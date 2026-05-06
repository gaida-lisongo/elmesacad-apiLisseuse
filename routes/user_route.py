from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, HTTPException, status

from core.database import DbDep
from models.schemas import UserRechargeBody
from utils.ids import parse_object_id

router = APIRouter(prefix="/user", tags=["user"])


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.put("/recharge", status_code=status.HTTP_200_OK)
async def user_recharge(db: DbDep, body: UserRechargeBody) -> dict:
    if body.user_id is None and body.matricule is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Fournissez userId ou matricule.",
        )

    filt: dict
    if body.user_id is not None:
        filt = {"_id": parse_object_id(body.user_id, "userId")}
    else:
        filt = {"matricule": body.matricule.strip()}

    user = await db.users.find_one(filt)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable.")

    now = _utcnow()
    recharge_doc = {
        "_id": ObjectId(),
        "status": body.recharge.status,
        "credits": body.recharge.credits,
        "orderNumber": body.recharge.order_number,
        "ceatedAt": now,
        "updatedAt": now,
    }

    credits_delta = int(body.recharge.credits)
    if credits_delta < 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Le nombre de crédits de la recharge doit être positif.",
        )

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$push": {"recharges": recharge_doc},
            "$inc": {"credits": float(credits_delta)},
            "$set": {"updatedAt": now},
        },
    )

    saved = await db.users.find_one({"_id": user["_id"]})
    assert saved is not None
    out = dict(saved)
    out["_id"] = str(out["_id"])
    for r in out.get("recharges", []):
        if isinstance(r.get("_id"), ObjectId):
            r["_id"] = str(r["_id"])
    return out
