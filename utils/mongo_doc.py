from typing import Any

from bson import ObjectId


def stringify_ids(doc: dict[str, Any]) -> dict[str, Any]:
    out = dict(doc)
    if "_id" in out and isinstance(out["_id"], ObjectId):
        out["_id"] = str(out["_id"])
    return out


def stringify_list(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [stringify_ids(x) for x in items]
