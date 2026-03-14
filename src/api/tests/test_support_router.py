import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from routers import support


class FakeRecord(dict):
    def __getattr__(self, key):
        return self.get(key)

    def model_dump(self, mode="json"):
        return dict(self)


class FakeTask:
    def __init__(self):
        self.calls = []

    def delay(self, **kwargs):
        self.calls.append(kwargs)


class FakePrisma:
    def __init__(self):
        self.users = {}
        self.tickets = {}
        self.comments = []
        self.recipients = []
        self.ticket_id = 1
        self.comment_id = 1

        self.user = SimpleNamespace(find_first=self.user_find_first)
        self.supportticket = SimpleNamespace(
            create=self.ticket_create,
            find_unique=self.ticket_find_unique,
            find_many=self.ticket_find_many,
            update=self.ticket_update,
        )
        self.supportcomment = SimpleNamespace(create=self.comment_create)
        self.supportrecipient = SimpleNamespace(
            create_many=self.recipient_create_many,
            find_many=self.recipient_find_many,
        )

    def user_find_first(self, where):
        email = where.get("email")
        user = self.users.get(email)
        return FakeRecord(user) if user else None

    def ticket_create(self, data):
        ticket = {
            "id": self.ticket_id,
            "subject": data["subject"],
            "message": data["message"],
            "status": data.get("status", "open"),
            "priority": data.get("priority", "normal"),
            "requesterEmail": data["requesterEmail"],
            "requesterName": data.get("requesterName"),
            "source": data.get("source", "public_form"),
            "createdByUserId": data.get("createdByUserId"),
            "createdAt": "2026-03-11T00:00:00Z",
            "updatedAt": "2026-03-11T00:00:00Z",
        }
        self.tickets[self.ticket_id] = ticket
        self.ticket_id += 1
        return FakeRecord(ticket)

    def _ticket_with_relations(self, ticket):
        ticket_id = ticket["id"]
        ticket_comments = [FakeRecord(c) for c in self.comments if c["ticketId"] == ticket_id]
        ticket_recipients = [FakeRecord(r) for r in self.recipients if r["ticketId"] == ticket_id]
        full = FakeRecord(ticket)
        full["comments"] = ticket_comments
        full["recipients"] = ticket_recipients
        return full

    def ticket_find_unique(self, where, include=None):
        ticket = self.tickets.get(where.get("id"))
        if ticket is None:
            return None
        if include:
            return self._ticket_with_relations(ticket)
        return FakeRecord(ticket)

    def ticket_find_many(self, where=None, include=None):
        where = where or {}
        results = []
        for ticket in self.tickets.values():
            if where.get("status") and where["status"] != ticket["status"]:
                continue
            results.append(self._ticket_with_relations(ticket) if include else FakeRecord(ticket))
        return results

    def ticket_update(self, where, data, include=None):
        ticket = self.tickets.get(where["id"])
        if ticket is None:
            return None
        ticket.update(data)
        if include:
            return self._ticket_with_relations(ticket)
        return FakeRecord(ticket)

    def comment_create(self, data):
        comment = {
            "id": self.comment_id,
            "ticketId": data["ticketId"],
            "authorUserId": data.get("authorUserId"),
            "authorEmail": data.get("authorEmail"),
            "authorName": data.get("authorName"),
            "body": data["body"],
            "isInternal": data.get("isInternal", True),
            "createdAt": "2026-03-11T00:00:00Z",
        }
        self.comments.append(comment)
        self.comment_id += 1
        return FakeRecord(comment)

    def recipient_create_many(self, data, skip_duplicates=True):
        seen = {(r["ticketId"], r["email"]) for r in self.recipients}
        for row in data:
            key = (row["ticketId"], row["email"])
            if skip_duplicates and key in seen:
                continue
            self.recipients.append(
                {
                    "id": len(self.recipients) + 1,
                    "ticketId": row["ticketId"],
                    "email": row["email"],
                    "createdAt": "2026-03-11T00:00:00Z",
                }
            )
            seen.add(key)

    def recipient_find_many(self, where):
        return [FakeRecord(r) for r in self.recipients if r["ticketId"] == where["ticketId"]]


def test_create_ticket_public_sets_recipients_and_initial_comment(monkeypatch):
    fake_prisma = FakePrisma()
    fake_task = FakeTask()
    monkeypatch.setattr(support, "prisma", fake_prisma)
    monkeypatch.setattr(support, "send_support_notification", fake_task)
    monkeypatch.setenv("SUPPORT_EMAIL_RECIPIENTS", "ops@example.org,dev@example.org")

    payload = support.CreateTicketBody(
        subject="Test ticket",
        message="This is a support message from public form.",
        requesterEmail="person@example.org",
        requesterName="Person",
    )
    request = SimpleNamespace(scope={})

    response = support.create_ticket(payload, request)
    body = json.loads(response.body.decode("utf-8"))

    assert response.status_code == 201
    assert body["requesterEmail"] == "person@example.org"
    assert len(body["recipients"]) == 2
    assert len(body["comments"]) == 1
    assert fake_task.calls[0]["event_type"] == "ticket_created"


def test_list_tickets_rejects_invalid_status(monkeypatch):
    fake_prisma = FakePrisma()
    monkeypatch.setattr(support, "prisma", fake_prisma)

    with pytest.raises(HTTPException) as exc:
        support.list_tickets(status="unknown_status", _=FakeRecord({"id": 1, "email": "a@b.c"}))

    assert exc.value.status_code == 400


def test_update_ticket_resolved_sends_notification(monkeypatch):
    fake_prisma = FakePrisma()
    fake_task = FakeTask()
    monkeypatch.setattr(support, "prisma", fake_prisma)
    monkeypatch.setattr(support, "send_support_notification", fake_task)

    created = fake_prisma.ticket_create(
        {
            "subject": "Ticket",
            "message": "Initial message",
            "requesterEmail": "x@y.z",
            "status": "open",
            "priority": "normal",
            "source": "public_form",
        }
    )
    payload = support.UpdateTicketBody(status="resolved")
    user = FakeRecord({"id": 10, "email": "dev@example.org", "name": "Dev User"})
    response = support.update_ticket(created.id, payload, user)

    assert response.status_code == 200
    assert fake_task.calls[0]["event_type"] == "status_changed"
