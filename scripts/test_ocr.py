"""
Test unitaire de l'OCR sur les images du dataset.
Teste extract_text_from_file() sur PNG et PDF.

Usage (depuis hackathon-doc-ai/) :
    python scripts/test_ocr.py
"""

import os
import sys

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATASET_DIR = os.path.join(PROJECT_DIR, "dataset")

# Ajoute le dossier airflow/dags/tasks au path pour importer ocr_engine
sys.path.insert(0, os.path.join(PROJECT_DIR, "airflow", "dags", "tasks"))

from ocr_engine import extract_text_from_file  # noqa: E402

TESTS = [
    ("PNG facture conforme",    os.path.join(DATASET_DIR, "raw_images", "facture", "FAC_SUP001_conforme.png")),
    ("PNG RIB conforme",        os.path.join(DATASET_DIR, "raw_images", "rib",     "RIB_SUP001_conforme.png")),
    ("PNG URSSAF conforme",     os.path.join(DATASET_DIR, "raw_images", "urssaf",  "URS_SUP001_conforme.png")),
    ("PNG facture dégradée",    os.path.join(DATASET_DIR, "raw_images", "degraded","FAC_SUP004_invoice_degraded_blur.png")),
    ("PDF facture conforme",    os.path.join(DATASET_DIR, "raw",        "facture", "FAC_SUP001_conforme.pdf")),
]

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST OCR — extract_text_from_file()")
    print("=" * 60)

    for label, path in TESTS:
        print(f"\n▶ {label}")
        print(f"  Fichier : {os.path.basename(path)}")
        if not os.path.exists(path):
            print(f"  ✗ Fichier introuvable")
            continue
        try:
            text = extract_text_from_file(path)
            preview = text.strip()[:200].replace("\n", " ")
            print(f"  ✓ {len(text)} caractères extraits")
            print(f"  Aperçu : {preview}...")
        except Exception as e:
            print(f"  ✗ Erreur : {e}")

    print("\n" + "=" * 60)
