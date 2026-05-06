from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException, status


def parse_object_id(value: str, field: str = "id") -> ObjectId:
    try:
        return ObjectId(value)
    except InvalidId as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"{field} invalide : identifiant MongoDB incorrect.",
        ) from exc
