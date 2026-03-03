from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from helpers.prisma import prisma
from helpers.user import get_user
from prisma.models import User

router = APIRouter(
    prefix="/news",
    tags=["news"],
)


@router.get("/")
def get_news(request: Request):
    current_user = None
    if "user" in request.scope and request.scope["user"] is not None:
        current_user = prisma.user.find_first(
            where={
                "email": request.scope["user"].email,
            }
        )

    if current_user is not None:
        news_items = prisma.news.find_many(
            where={
                "isActive": True,
            },
            include={
                "NewsRead": {
                    "where": {
                        "userId": current_user.id,
                    }
                }
            },
        )
    else:
        news_items = prisma.news.find_many(
            where={
                "isActive": True,
            }
        )

    serialized_news = []
    for item in news_items:
        item_dict = item.model_dump(mode="json")
        item_dict["isRead"] = len(item_dict.get("NewsRead", [])) > 0 if current_user is not None else False
        item_dict.pop("NewsRead", None)
        serialized_news.append(item_dict)

    serialized_news.sort(key=lambda entry: entry["createdAt"], reverse=True)
    return JSONResponse(serialized_news)


@router.get("/important/unread")
def get_unread_important_news(user: User = Depends(get_user)):
    important_news = prisma.news.find_many(
        where={
            "isActive": True,
            "isImportant": True,
        },
        include={
            "NewsRead": {
                "where": {
                    "userId": user.id,
                }
            }
        },
    )

    unread_news = next((item for item in important_news if len(item.NewsRead) == 0), None)
    if unread_news is None:
        return JSONResponse(None)

    return JSONResponse(unread_news.model_dump(mode="json"))


@router.post("/{news_id}/read")
def mark_news_as_read(news_id: int, user: User = Depends(get_user)):
    news_item = prisma.news.find_unique(
        where={
            "id": news_id,
        }
    )

    if news_item is None:
        raise HTTPException(status_code=404, detail="News item not found")

    existing_read = prisma.newsread.find_first(
        where={
            "userId": user.id,
            "newsId": news_id,
        }
    )

    if existing_read is None:
        prisma.newsread.create(
            data={
                "userId": user.id,
                "newsId": news_id,
            }
        )
    else:
        prisma.newsread.update(
            where={
                "id": existing_read.id,
            },
            data={
                "readAt": datetime.now(timezone.utc),
            },
        )

    return JSONResponse({"success": True})
