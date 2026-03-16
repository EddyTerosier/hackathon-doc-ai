from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
RAW_IMAGES_DIR = BASE_DIR / "raw_images"

TARGET_DIRS = [
    RAW_IMAGES_DIR / "facture",
    RAW_IMAGES_DIR / "urssaf",
    RAW_IMAGES_DIR / "rib",
    RAW_IMAGES_DIR / "degraded",
]


def delete_images() -> None:
    deleted_count = 0

    for folder in TARGET_DIRS:
        if not folder.exists():
            continue

        for pattern in ("*.png", "*.jpg", "*.jpeg"):
            for image_file in folder.glob(pattern):
                image_file.unlink()
                deleted_count += 1

    print(f"{deleted_count} image(s) supprimée(s).")


if __name__ == "__main__":
    delete_images()