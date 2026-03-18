import os

from tasks.ocr_engine import extract_text_from_file

DATA_ROOT = os.getenv("DATA_ROOT", "/data")


def run_ocr(**context):
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}
    file_path = conf.get("file_path")
    group_id = conf.get("group_id", "unknown")
    document_id = conf.get("document_id", "unknown")

    if not file_path:
        raise ValueError("file_path manquant dans dag_run.conf")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Fichier introuvable : {file_path}")

    text = extract_text_from_file(file_path)

    clean_dir = os.path.join(DATA_ROOT, "clean", group_id)
    os.makedirs(clean_dir, exist_ok=True)
    clean_path = os.path.join(clean_dir, f"{document_id}.txt")
    with open(clean_path, "w") as f:
        f.write(text)

    return text