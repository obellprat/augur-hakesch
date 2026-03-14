import os
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from fastapi_keycloak_middleware import CheckPermissions
from pydantic import BaseModel, Field

from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User

# Role required to view and manage support tickets (Keycloak realm role)
SUPPORT_ADMIN_ROLE = os.getenv("SUPPORT_ADMIN_ROLE", "support_admin")

from calculations.support_notifications import send_support_notification

ALLOWED_STATUSES = {"open", "in_progress", "resolved", "closed"}

router = APIRouter(
    prefix="/support",
    tags=["support"],
)


class CreateTicketBody(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    message: str = Field(min_length=10, max_length=5000)
    requesterEmail: str = Field(min_length=3, max_length=254)
    requesterName: str | None = Field(default=None, max_length=120)
    priority: Literal["low", "normal", "high"] = "normal"
    source: str = Field(default="public_form", max_length=60)


class AddCommentBody(BaseModel):
    body: str = Field(min_length=2, max_length=5000)
    isInternal: bool = True


class UpdateTicketBody(BaseModel):
    status: Literal["open", "in_progress", "resolved", "closed"]


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _recipient_emails() -> list[str]:
    raw_recipients = os.getenv("SUPPORT_EMAIL_RECIPIENTS", "")
    return [email.strip().lower() for email in raw_recipients.split(",") if email.strip()]


def _get_authenticated_user_from_scope(request: Request) -> User | None:
    if "user" not in request.scope or request.scope["user"] is None:
        return None
    return prisma.user.find_first(
        where={
            "email": request.scope["user"].email,
        }
    )


def _serialize_comment(comment) -> dict:
    item = comment.model_dump(mode="json")
    item["author"] = {
        "userId": item.get("authorUserId"),
        "email": item.get("authorEmail"),
        "name": item.get("authorName"),
    }
    return item


def _serialize_ticket(ticket) -> dict:
    item = ticket.model_dump(mode="json")
    item["comments"] = [_serialize_comment(comment) for comment in ticket.comments] if ticket.comments else []
    item["recipients"] = [recipient.email for recipient in ticket.recipients] if ticket.recipients else []
    return item


@router.post("/tickets")
def create_ticket(payload: CreateTicketBody, request: Request):
    auth_user = _get_authenticated_user_from_scope(request)
    requester_email = _normalize_email(payload.requesterEmail)

    if "@" not in requester_email:
        raise HTTPException(status_code=400, detail="Invalid requesterEmail")

    if auth_user is not None:
        requester_email = auth_user.email

    ticket = prisma.supportticket.create(
        data={
            "subject": payload.subject.strip(),
            "message": payload.message.strip(),
            "status": "open",
            "priority": payload.priority,
            "requesterEmail": requester_email,
            "requesterName": (auth_user.name if auth_user is not None else payload.requesterName),
            "source": payload.source.strip() or "public_form",
            "createdByUserId": auth_user.id if auth_user is not None else None,
        }
    )

    recipients = _recipient_emails()
    if len(recipients) > 0:
        prisma.supportrecipient.create_many(
            data=[{"ticketId": ticket.id, "email": email} for email in recipients],
            skip_duplicates=True,
        )

    prisma.supportcomment.create(
        data={
            "ticketId": ticket.id,
            "authorUserId": auth_user.id if auth_user is not None else None,
            "authorEmail": requester_email,
            "authorName": auth_user.name if auth_user is not None else payload.requesterName,
            "body": payload.message.strip(),
            "isInternal": False,
        }
    )

    full_ticket = prisma.supportticket.find_unique(
        where={"id": ticket.id},
        include={"comments": True, "recipients": True},
    )

    send_support_notification.delay(
        event_type="ticket_created",
        ticket_id=ticket.id,
        actor_email=requester_email,
        actor_name=auth_user.name if auth_user is not None else payload.requesterName,
    )

    return JSONResponse(_serialize_ticket(full_ticket), status_code=201)


@router.get(
    "/tickets",
    dependencies=[Depends(CheckPermissions(SUPPORT_ADMIN_ROLE))],
)
def list_tickets(status: str | None = Query(default=None), _: User = Depends(get_user)):
    where = {}
    if status is not None:
        if status not in ALLOWED_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status")
        where["status"] = status

    tickets = prisma.supportticket.find_many(
        where=where,
        include={"comments": True, "recipients": True},
    )
    serialized_tickets = [_serialize_ticket(ticket) for ticket in tickets]
    serialized_tickets.sort(key=lambda ticket: ticket["createdAt"], reverse=True)
    return JSONResponse(serialized_tickets)


@router.get(
    "/tickets/{ticket_id}",
    dependencies=[Depends(CheckPermissions(SUPPORT_ADMIN_ROLE))],
)
def get_ticket(ticket_id: int, _: User = Depends(get_user)):
    ticket = prisma.supportticket.find_unique(
        where={"id": ticket_id},
        include={"comments": True, "recipients": True},
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return JSONResponse(_serialize_ticket(ticket))


@router.post(
    "/tickets/{ticket_id}/comments",
    dependencies=[Depends(CheckPermissions(SUPPORT_ADMIN_ROLE))],
)
def create_ticket_comment(ticket_id: int, payload: AddCommentBody, user: User = Depends(get_user)):
    ticket = prisma.supportticket.find_unique(where={"id": ticket_id}, include={"recipients": True})
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    comment = prisma.supportcomment.create(
        data={
            "ticketId": ticket_id,
            "authorUserId": user.id,
            "authorEmail": user.email,
            "authorName": user.name,
            "body": payload.body.strip(),
            "isInternal": payload.isInternal,
        }
    )

    send_support_notification.delay(
        event_type="comment_added",
        ticket_id=ticket.id,
        actor_email=user.email,
        actor_name=user.name,
    )

    return JSONResponse(_serialize_comment(comment), status_code=201)


@router.patch(
    "/tickets/{ticket_id}",
    dependencies=[Depends(CheckPermissions(SUPPORT_ADMIN_ROLE))],
)
def update_ticket(ticket_id: int, payload: UpdateTicketBody, user: User = Depends(get_user)):
    if payload.status not in ALLOWED_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")

    ticket = prisma.supportticket.find_unique(where={"id": ticket_id})
    if ticket is None:
        raise HTTPException(status_code=404, detail="Ticket not found")

    updated_ticket = prisma.supportticket.update(
        where={"id": ticket_id},
        data={"status": payload.status},
        include={"comments": True, "recipients": True},
    )

    if payload.status in {"resolved", "closed"}:
        send_support_notification.delay(
            event_type="status_changed",
            ticket_id=ticket.id,
            actor_email=user.email,
            actor_name=user.name,
            new_status=payload.status,
        )

    return JSONResponse(_serialize_ticket(updated_ticket))
