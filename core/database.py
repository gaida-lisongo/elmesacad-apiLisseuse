from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, Request
from motor.motor_asyncio import AsyncIOMotorDatabase


async def get_db(request: Request) -> AsyncGenerator[AsyncIOMotorDatabase, None]:
    db: AsyncIOMotorDatabase = request.app.state.db
    yield db


DbDep = Annotated[AsyncIOMotorDatabase, Depends(get_db)]
