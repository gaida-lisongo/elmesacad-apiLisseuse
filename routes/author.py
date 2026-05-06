from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from pymongo.errors import DuplicateKeyError

from core.config import Settings, get_settings
from core.database import DbDep
from models.schemas import DocumentCreatePayload, PdfUploadResponse
from utils.cloudinary_media import upload_webp_page, webp_public_delivery_url
from utils.ids import parse_object_id
from utils.pdf_webp import PdfProcessingError, pdf_pages_as_webp, sniff_pdf

router = APIRouter(prefix="/author", tags=["author"])

SettingsDep = Annotated[Settings, Depends(get_settings)]


@router.post(
    "/upload-pdf",
    response_model=PdfUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_pdf(
    settings: SettingsDep,
    reference: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
) -> PdfUploadResponse:
    ref = reference.strip()
    if not ref:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Le champ « reference » est obligatoire.",
        )

    allowed_types = {"application/pdf", "application/octet-stream", "binary/octet-stream"}
    if file.content_type and file.content_type not in allowed_types:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Le fichier doit être un PDF (Content-Type inattendu).",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="Fichier vide.",
        )

    sniff_pdf(raw[:5])

    try:
        pages_webp = pdf_pages_as_webp(raw)
    except PdfProcessingError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    total = len(pages_webp)
    for idx, blob in enumerate(pages_webp, start=1):
        try:
            upload_webp_page(settings, ref, idx, blob)
        except Exception as exc:
            raise HTTPException(
                status.HTTP_502_BAD_GATEWAY,
                detail=f"Échec upload Cloudinary pour la page {idx}: {exc}",
            ) from exc

    return PdfUploadResponse(reference=ref, total_pages=total)


def _build_document_pages(
    settings: Settings,
    payload: DocumentCreatePayload,
) -> list[dict]:
    by_index = {p.index: p for p in payload.pages}
    built: list[dict] = []
    for i in range(1, payload.total_pages + 1):
        url = webp_public_delivery_url(
            settings.cloudinary_cloud_name,
            payload.reference,
            i,
            settings.cloudinary_folder,
        )
        prev = by_index.get(i)
        built.append(
            {
                "url": url,
                "comment": prev.comment if prev else "",
                "index": i,
                "isRead": prev.is_read if prev else False,
            }
        )
    return built


@router.put("/create-document", status_code=status.HTTP_201_CREATED)
async def create_document(
    settings: SettingsDep,
    db: DbDep,
    payload: DocumentCreatePayload,
) -> dict:
    if payload.total_pages < 1:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail="total_pages doit être >= 1.",
        )

    cat = await db.categories.find_one({"reference": payload.categorie})
    if not cat:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            detail=f"Aucune catégorie avec la référence « {payload.categorie} ».",
        )

    user_oid = parse_object_id(payload.user_id, "userId")
    user = await db.users.find_one({"_id": user_oid})
    if not user:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable.",
        )

    pages = _build_document_pages(settings, payload)

    doc_id = parse_object_id(payload.id, "_id") if payload.id else None
    insert_doc: dict = {
        "_id": doc_id,
        "reference": payload.reference,
        "categorie": payload.categorie,
        "author": {
            "name": payload.author.name,
            "photo": payload.author.photo,
            "email": payload.author.email,
            "descriontion": [b.model_dump() for b in payload.author.bio_sections],
        },
        "userId": payload.user_id,
        "total_pages": payload.total_pages,
        "title": payload.title,
        "description": [d.model_dump() for d in payload.description],
        "pages": pages,
        "createdAt": payload.created_at,
        "updatedAt": payload.updated_at,
    }

    if doc_id is None:
        del insert_doc["_id"]

    try:
        result = await db.documents.insert_one(insert_doc)
    except DuplicateKeyError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail="Un document avec cet identifiant existe déjà.",
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de l'enregistrement du document.",
        ) from exc

    saved = await db.documents.find_one({"_id": result.inserted_id})
    if not saved:
        oid = insert_doc.get("_id", result.inserted_id)
        saved = await db.documents.find_one({"_id": oid}) or insert_doc

    out = dict(saved)
    out["_id"] = str(out["_id"])
    return out
