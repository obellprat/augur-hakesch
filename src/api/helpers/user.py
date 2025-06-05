from fastapi import Request
from prisma.models import User
from helpers.prisma import prisma


async def map_user(userinfo: dict[str, any]) -> User:
    user = prisma.user.find_first(
        where={
            "email": userinfo["email"],
        }
    )
    return user


async def get_user(request: Request) -> User:
    """
    Custom dependency to retrieve the user object from the request.
    """

    if "user" in request.scope:
        # Do whatever you need to get the user object from the database
        user = prisma.user.find_first(
            where={
                "email": request.scope["user"].email,
            })
        if user:
            return user
    # Handle missing user scenario
    raise HTTPException(
        status_code=401,
        detail="Unable to retrieve user from request",
    )