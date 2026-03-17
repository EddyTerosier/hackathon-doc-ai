from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RAW_DIR = BASE_DIR / "raw"

TARGET_DIRS = [
    RAW_DIR / "facture",
    RAW_DIR / "urssaf",
    RAW_DIR / "rib",
    RAW_DIR / "degraded",
]


def delete_pdfs() -> None:
    deleted_count = 0

    for folder in TARGET_DIRS:
        if not folder.exists():
            continue

        for pdf_file in folder.glob("*.pdf"):
            pdf_file.unlink()
            deleted_count += 1

    print(f"{deleted_count} fichier(s) PDF supprimé(s).")


if __name__ == "__main__":
    delete_pdfs()