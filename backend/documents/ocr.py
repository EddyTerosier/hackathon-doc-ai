import os
import shutil
import subprocess
import tempfile
from typing import List

from ..extraction.classifier import DocumentType, extract
from .models import DocumentFile


TESSERACT_LANG = "fra+eng"


def _run_tesseract(input_path: str, lang: str = TESSERACT_LANG) -> str:
    """Exécute Tesseract sur un fichier image et retourne le texte reconnu."""

    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract n'est pas disponible dans le PATH")

    cmd = ["tesseract", input_path, "stdout", "-l", lang]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"Tesseract a échoué (code {proc.returncode}): {proc.stderr.strip()}"
        )
    return proc.stdout or ""


def _pdf_to_image_paths(pdf_path: str, output_dir: str, dpi: int = 300) -> List[str]:
    """Convertit un PDF en images PNG (une image par page) en utilisant pdftoppm."""

    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm (poppler-utils) n'est pas disponible dans le PATH")

    base = os.path.join(output_dir, "page")
    cmd = ["pdftoppm", "-png", "-r", str(dpi), pdf_path, base]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"pdftoppm a échoué (code {proc.returncode}): {proc.stderr.strip()}"
        )

    png_files = sorted(
        f for f in os.listdir(output_dir) if f.lower().startswith("page") and f.lower().endswith(".png")
    )
    return [os.path.join(output_dir, p) for p in png_files]


def extract_text_from_file(file_path: str) -> str:
    """Retourne le texte OCR d'un PDF ou d'une image."""

    ext = os.path.splitext(file_path)[1].lower()

    if ext == ".pdf":
        with tempfile.TemporaryDirectory() as tmpdir:
            images = _pdf_to_image_paths(file_path, tmpdir)
            texts = [_run_tesseract(img) for img in images]
            return "\n".join(texts)

    # Image (png/jpg/jpeg)
    return _run_tesseract(file_path)


def process_document_file(document: DocumentFile) -> DocumentFile:
    """Effectue l'OCR + extraction sur un document et met à jour le modèle."""

    document.analysis_status = DocumentFile.ANALYSIS_PROCESSING
    document.save()

    try:
        ocr_text = extract_text_from_file(document.file_path)
        extraction_result = extract(ocr_text)

        document.ocr_text = ocr_text
        document.extracted_data = extraction_result.to_dict()
        document.confidence_score = extraction_result.confidence
        document.needs_manual_review = extraction_result.confidence < 0.5

        type_map = {
            DocumentType.FACTURE: DocumentFile.DOCUMENT_TYPE_INVOICE,
            DocumentType.ATTESTATION_URSSAF: DocumentFile.DOCUMENT_TYPE_URSSAF_CERTIFICATE,
            DocumentType.RIB: DocumentFile.DOCUMENT_TYPE_BANK_DETAILS,
            DocumentType.INCONNU: DocumentFile.DOCUMENT_TYPE_UNKNOWN,
        }
        document.document_type = type_map.get(extraction_result.document_type, DocumentFile.DOCUMENT_TYPE_UNKNOWN)
        document.analysis_status = DocumentFile.ANALYSIS_ANALYZED

    except Exception as exc:
        document.analysis_status = DocumentFile.ANALYSIS_FAILED
        document.needs_manual_review = True
        document.anomalies = list(document.anomalies or [])
        document.anomalies.append(str(exc)[:255])

    document.save()
    return document


def process_document_file_async(document: DocumentFile) -> None:
    """Lance le traitement OCR en background (thread)."""

    import threading

    thread = threading.Thread(target=process_document_file, args=(document,), daemon=True)
    thread.start()
