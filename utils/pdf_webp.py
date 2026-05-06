import io

import fitz
from PIL import Image


class PdfProcessingError(Exception):
    pass


def _pixmap_to_webp(pix: fitz.Pixmap) -> bytes:
    """
    PyMuPDF n’embarque pas toujours l’encodeur WebP (surtout en conteneur).
    Ordre : tobytes('webp') → pil_tobytes → PNG + Pillow.
    """

    try:
        return pix.tobytes("webp")
    except Exception:
        pass

    pil_tobytes = getattr(pix, "pil_tobytes", None)
    if callable(pil_tobytes):
        try:
            return pil_tobytes(format="WEBP", optimize=True)
        except Exception:
            pass

    try:
        png_bytes = pix.tobytes("png")
    except Exception as exc:
        raise PdfProcessingError(
            "Export image impossible pour cette page (PNG / PyMuPDF)."
        ) from exc

    img = Image.open(io.BytesIO(png_bytes))
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    try:
        img.save(buf, format="WEBP", quality=85, method=6)
    except Exception as exc:
        raise PdfProcessingError(
            "Conversion WebP impossible (bibliothèque système libwebp ou Pillow)."
        ) from exc
    return buf.getvalue()


def pdf_pages_as_webp(pdf_bytes: bytes) -> list[bytes]:
    """Convertit chaque page PDF en image WebP (bytes)."""

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise PdfProcessingError("Fichier PDF illisible ou corrompu.") from exc

    try:
        if doc.page_count == 0:
            raise PdfProcessingError("Le PDF ne contient aucune page.")

        images: list[bytes] = []
        matrix = fitz.Matrix(2.0, 2.0)
        for i in range(doc.page_count):
            page = doc.load_page(i)
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            try:
                images.append(_pixmap_to_webp(pix))
            except PdfProcessingError:
                raise
            except Exception as exc:
                raise PdfProcessingError(
                    f"Échec conversion page {i + 1}."
                ) from exc
        return images
    finally:
        doc.close()


def sniff_pdf(header: bytes) -> None:
    if not header.startswith(b"%PDF"):
        raise PdfProcessingError("Le fichier ne semble pas être un PDF valide.")
