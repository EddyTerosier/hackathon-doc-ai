import sys
import os

# Fonctionne en local et en Docker (/opt/airflow = racine du projet)
_project_root = os.environ.get(
    "PROJECT_ROOT",
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import json
import os

from backend.extraction.classifier import extract

DATA_ROOT = os.getenv("DATA_ROOT", "/data")


def run_classify_and_extract(**context):
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}

    text = ti.xcom_pull(task_ids="ocr_task")

    result = extract(text)
    result_dict = result.to_dict()

    # Sauvegarde dans curated/
    group_id = conf.get("group_id", "unknown")
    document_id = conf.get("document_id", "unknown")
    curated_dir = os.path.join(DATA_ROOT, "curated", group_id)
    os.makedirs(curated_dir, exist_ok=True)
    curated_path = os.path.join(curated_dir, f"{document_id}.json")
    with open(curated_path, "w") as f:
        json.dump(result_dict, f, ensure_ascii=False, indent=2)

    return result_dict


"""
def run_classify_and_extract(**context):
    ti = context["ti"]

    text = ti.xcom_pull(task_ids="ocr_task")

    # TODO: remplacer par la vraie classification + extraction (Personne 3)
    return {
        "document_type": "facture",
        "champs": {
            "supplier_name": "Mock Supplier",
            "siret": "12345678901234",
            "tva": "FR12345678901",
            "date_emission": "2024-01-01",
            "montant_ht": 100.0,
            "montant_ttc": 120.0,
        }
    }
"""