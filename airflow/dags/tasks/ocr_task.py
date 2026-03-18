import os
import re


DATA_ROOT = os.getenv("DATA_ROOT", "/data")


def run_ocr(**context):
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}
    file_path = conf.get("file_path")

    if not file_path or not os.path.exists(file_path):
        # Fallback mock pour les tests sans fichier réel
        return "FACTURE N° FAC-2024-00123\nSIRET : 123 456 789 00012\nTotal TTC : 1 800,00 €"

    # TODO: remplacer par le vrai OCR Tesseract (Personne 2)
    # import pytesseract
    # from PIL import Image
    # text = pytesseract.image_to_string(Image.open(file_path), lang="fra")

    with open(file_path, "r", errors="ignore") as f:
        text = f.read()

    # Nettoyage basique du texte (clean)
    text = re.sub(r"\s+", " ", text).strip()

    # Sauvegarde dans clean/
    group_id = conf.get("group_id", "unknown")
    document_id = conf.get("document_id", "unknown")
    clean_dir = os.path.join(DATA_ROOT, "clean", group_id)
    os.makedirs(clean_dir, exist_ok=True)
    clean_path = os.path.join(clean_dir, f"{document_id}.txt")
    with open(clean_path, "w") as f:
        f.write(text)

    return text

"""
def run_ocr(**_):
    # TODO: remplacer par le vrai OCR Tesseract sur un PDF (Personne 2)
    return 
    FACTURE
    Fournisseur : Mock Supplier
    SIRET : 12345678901234
    TVA : FR12345678901
    Date : 01/01/2024
    Montant HT : 100.00 EUR
    Montant TTC : 120.00 EUR
"""