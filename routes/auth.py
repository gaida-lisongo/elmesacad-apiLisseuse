from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from core.database import DbDep
from models.schemas import MatriculeAuthBody
from utils.mongo_doc import stringify_ids

router = APIRouter(prefix="/auth", tags=["auth"])


def _serialize_user(doc: dict) -> dict:
    out = stringify_ids(doc)
    for r in out.get("recharges") or []:
        if isinstance(r.get("_id"), ObjectId):
            r["_id"] = str(r["_id"])
    return out


@router.post("/matricule", status_code=status.HTTP_200_OK)
async def auth_by_matricule(db: DbDep, body: MatriculeAuthBody) -> dict:
    matricule = body.matricule.strip()
    if not matricule:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Le matricule est obligatoire.",
        )

    user = await db.users.find_one({"matricule": matricule})
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Aucun utilisateur avec ce matricule.",
        )

    user_out = _serialize_user(user)
    user_id = user_out["_id"]

    categories_raw = await db.categories.aggregate([
        {
            "$lookup": {
                "from": "documents",
                "let": {"reference": "$reference"},
                "pipeline": [
                    {
                        "$match": {
                            "$expr": {
                                "$and": [
                                    {"$eq": ["$categorie", "$$reference"]},
                                    {"$eq": ["$userId", user_id]},
                                ]
                            }
                        }
                    },
                    {"$sort": {"updatedAt": -1}},
                ],
                "as": "documents",
            }
        },
        {"$match": {"documents": {"$ne": []}}},
        {
            "$project": {
                "_id": 1,
                "reference": 1,
                "designation": 1,
                "tags": 1,
                "documents": 1,
            }
        },
        {"$sort": {"documents.0.updatedAt": -1}},
    ]).to_list(length=500)

    categories_out: list[dict] = []
    if categories_raw:
        for category in categories_raw:
            serialized_category = stringify_ids(category)
            serialized_category["documents"] = [stringify_ids(d) for d in serialized_category.get("documents", [])]
            categories_out.append(serialized_category)

    return {
        "user": user_out,
        "categories": categories_out,
    }
