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

    documents_raw = await db.documents.find({"userId": user_id}).sort(
        "updatedAt",
        -1,
    ).to_list(length=10_000)

    documents = [stringify_ids(d) for d in documents_raw]

    category_refs: list[str] = []
    seen: set[str] = set()
    for d in documents_raw:
        ref = d.get("categorie")
        if isinstance(ref, str) and ref and ref not in seen:
            seen.add(ref)
            category_refs.append(ref)

    categories_out: list[dict] = []
    if category_refs:
        categories_raw = await db.categories.find(
            {"reference": {"$in": category_refs}},
        ).to_list(length=500)
        by_ref = {c["reference"]: stringify_ids(c) for c in categories_raw}
        categories_out = [by_ref[r] for r in category_refs if r in by_ref]

    return {
        "user": user_out,
        "documents": documents,
        "categories": categories_out,
    }
