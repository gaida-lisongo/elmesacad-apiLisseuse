from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status

from core.config import Settings, get_settings
from core.database import DbDep
from models.schemas import ReaderProgressBody
from utils.ids import parse_object_id

router = APIRouter(prefix="/reader", tags=["reader"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.patch("/update-progress", status_code=status.HTTP_200_OK)
async def update_progress(
    request: Request,
    settings: SettingsDep,
    db: DbDep,
    body: ReaderProgressBody,
) -> dict:
    cost = float(settings.credits_per_progress_update)

    doc_oid = parse_object_id(body.document_id, "documentId")
    user_oid = parse_object_id(body.user_id, "userId")

    client = request.app.state.mongo_client
    now = datetime.now(timezone.utc)

    async with await client.start_session() as session:
        async with session.start_transaction():
            doc = await db.documents.find_one(
                {"_id": doc_oid, "userId": body.user_id},
                session=session,
            )
            if not doc:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND,
                    detail="Document introuvable ou non associé à cet utilisateur.",
                )

            pages = list(doc.get("pages") or [])
            for p in pages:
                if p.get("index", 0) <= body.new_page:
                    p["isRead"] = True

            await db.documents.update_one(
                {"_id": doc_oid},
                {"$set": {"pages": pages, "updatedAt": now}},
                session=session,
            )

            user_res = await db.users.update_one(
                {"_id": user_oid, "credits": {"$gte": cost}},
                {"$inc": {"credits": -cost}},
                session=session,
            )
            if user_res.modified_count == 0:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    detail="Crédits insuffisants ou utilisateur introuvable.",
                )

    saved_doc = await db.documents.find_one({"_id": doc_oid})
    saved_user = await db.users.find_one({"_id": user_oid})
    assert saved_doc is not None and saved_user is not None

    return {
        "documentId": str(saved_doc["_id"]),
        "userId": body.user_id,
        "credits_remaining": float(saved_user["credits"]),
        "pages": saved_doc["pages"],
    }
