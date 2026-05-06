import io

import fitz


class PdfProcessingError(Exception):
    pass


def pdf_pages_as_webp(pdf_bytes: bytes) -> list[bytes]:
    """Convertit chaque page PDF en image WebP (bytes). Index = page_numéro (1-based)."""

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
                images.append(pix.tobytes("webp"))
            except Exception as exc:
                raise PdfProcessingError(
                    "Export WebP impossible pour cette page (PyMuPDF / pilote)."
                ) from exc
        return images
    finally:
        doc.close()


def sniff_pdf(header: bytes) -> None:
    if not header.startswith(b"%PDF"):
        raise PdfProcessingError("Le fichier ne semble pas être un PDF valide.")
