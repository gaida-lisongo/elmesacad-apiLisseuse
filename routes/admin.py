from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, status

from core.database import DbDep
from models.schemas import AdminCategoryUpsert, UserCreate
router = APIRouter(prefix="/admin", tags=["admin"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user(db: DbDep, payload: UserCreate) -> dict:
    matricule = payload.matricule.strip()
    mail = payload.mail.strip().lower()
    if not matricule or not mail:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Matricule et mail sont obligatoires.",
        )

    dup = await db.users.find_one(
        {"$or": [{"matricule": matricule}, {"mail": mail}]},
    )
    if dup:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Un utilisateur existe déjà avec ce matricule ou ce mail.",
        )

    doc = {
        "matricule": matricule,
        "mail": mail,
        "credits": float(payload.credits),
        "recharges": [],
        "metrics": {"categories": 0, "documents": 0, "pages": 0},
    }
    result = await db.users.insert_one(doc)
    saved = await db.users.find_one({"_id": result.inserted_id})
    assert saved is not None
    saved["_id"] = str(saved["_id"])
    return saved


@router.patch("/categories", status_code=status.HTTP_200_OK)
async def upsert_categories(
    db: DbDep,
    items: list[AdminCategoryUpsert],
) -> dict:
    if not items:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Liste de catégories vide.",
        )

    now = _utcnow()
    upserted = 0
    for item in items:
        ref = item.reference.strip()
        if not ref:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                detail="Chaque catégorie doit avoir une référence non vide.",
            )

        res = await db.categories.update_one(
            {"reference": ref},
            {
                "$set": {
                    "reference": ref,
                    "designation": item.designation,
                    "tags": item.tags,
                    "updatedAt": now,
                },
                "$setOnInsert": {"createdAt": now},
            },
            upsert=True,
        )
        if res.upserted_id is not None or res.modified_count > 0:
            upserted += 1

    return {"matched_or_modified": upserted, "received": len(items)}
