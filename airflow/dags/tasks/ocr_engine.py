# Extraction OCR isolée de Django.
# backend/documents/ocr.py contient la même logique mais importe des modèles Django
# (DocumentFile, classifier...), ce qui provoque une erreur d'import relatif quand
# Airflow charge le DAG sans contexte Django initialisé.
# Ce fichier contient uniquement la logique Tesseract/pdftoppm, sans aucune dépendance
# Django, pour pouvoir être importé directement dans les tâches Airflow.

import os
import shutil
import subprocess
import tempfile
from typing import List

TESSERACT_LANG = "fra+eng"


def _run_tesseract(input_path: str, lang: str = TESSERACT_LANG) -> str:
    if not shutil.which("tesseract"):
        raise RuntimeError("tesseract n'est pas disponible dans le PATH")
    proc = subprocess.run(
        ["tesseract", input_path, "stdout", "-l", lang],
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Tesseract a échoué (code {proc.returncode}): {proc.stderr.strip()}")
    return proc.stdout or ""


def _pdf_to_image_paths(pdf_path: str, output_dir: str, dpi: int = 300) -> List[str]:
    if not shutil.which("pdftoppm"):
        raise RuntimeError("pdftoppm (poppler-utils) n'est pas disponible dans le PATH")
    base = os.path.join(output_dir, "page")
    proc = subprocess.run(
        ["pdftoppm", "-png", "-r", str(dpi), pdf_path, base],
        capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pdftoppm a échoué (code {proc.returncode}): {proc.stderr.strip()}")
    png_files = sorted(
        f for f in os.listdir(output_dir)
        if f.lower().startswith("page") and f.lower().endswith(".png")
    )
    return [os.path.join(output_dir, p) for p in png_files]


def extract_text_from_file(file_path: str) -> str:
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        with tempfile.TemporaryDirectory() as tmpdir:
            images = _pdf_to_image_paths(file_path, tmpdir)
            return "\n".join(_run_tesseract(img) for img in images)
    return _run_tesseract(file_path)
