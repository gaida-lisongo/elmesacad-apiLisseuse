import io
from typing import Any

import cloudinary
import cloudinary.uploader

from core.config import Settings


def configure_cloudinary(settings: Settings) -> None:
    cloudinary.config(
        cloud_name=settings.cloudinary_cloud_name,
        api_key=settings.cloudinary_api_key,
        api_secret=settings.cloudinary_secret_key,
        secure=True,
    )


def webp_public_delivery_url(
    cloud_name: str,
    reference: str,
    page_index_1_based: int,
    folder: str | None,
) -> str:
    base_id = f"{reference}-{page_index_1_based}"
    public_path = f"{folder}/{base_id}" if folder else base_id
    return f"https://res.cloudinary.com/{cloud_name}/image/upload/{public_path}.webp"


def upload_webp_page(
    settings: Settings,
    reference: str,
    page_index_1_based: int,
    webp_bytes: bytes,
) -> dict[str, Any]:
    public_id = f"{reference}-{page_index_1_based}"
    opts: dict[str, Any] = {
        "resource_type": "image",
        "format": "webp",
        "overwrite": True,
        "invalidate": True,
    }
    if settings.cloudinary_folder:
        opts["folder"] = settings.cloudinary_folder

    return cloudinary.uploader.upload(
        io.BytesIO(webp_bytes),
        public_id=public_id,
        **opts,
    )
