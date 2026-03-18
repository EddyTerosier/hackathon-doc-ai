"""
Script de test du pipeline Airflow avec 3 fichiers réels (SUP001 - conforme).

Prérequis :
    docker-compose up airflow mongo -d

Usage :
    python scripts/test_pipeline.py
"""

import os
import subprocess 
import time
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient
import requests

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI       = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
DB_NAME         = "hackathon_db"
AIRFLOW_URL     = "http://localhost:8080"
AIRFLOW_USER    = "admin"

def _get_airflow_password():
    if pw := os.getenv("AIRFLOW_PASSWORD"):
        return pw
    try:
        import json
        result = subprocess.run(
            ["docker", "exec", AIRFLOW_CONTAINER,
             "cat", "/opt/airflow/simple_auth_manager_passwords.json.generated"],
            capture_output=True, text=True
        )
        data = json.loads(result.stdout.strip())
        # format : {"admin": "MOT_DE_PASSE"}
        return list(data.values())[0]
    except Exception as e:
        print(f"  [warning] lecture password échouée : {e}")
        return "admin"

AIRFLOW_PASSWORD = _get_airflow_password()
print(f"[debug] password utilisé : '{AIRFLOW_PASSWORD}'")
AIRFLOW_CONTAINER = "hackathon-airflow"

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATASET_DIR = os.path.join(PROJECT_DIR, "dataset", "raw")

FILES = {
    "facture":          os.path.join(DATASET_DIR, "facture", "FAC_SUP001_conforme.pdf"),
    "attestation_urssaf": os.path.join(DATASET_DIR, "urssaf", "URS_SUP001_conforme.pdf"),
    "rib":              os.path.join(DATASET_DIR, "rib",     "RIB_SUP001_conforme.pdf"),
}

# ── MongoDB ───────────────────────────────────────────────────────────────────
client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def setup_test_data():
    print("\n[1/3] Création du fournisseur SUP001 en MongoDB...")
    db.suppliers.delete_many({"siret": "12345678901234"})
    supplier = db.suppliers.insert_one({
        "name": "Alpha Conseil",
        "siret": "12345678901234",
        "vat_number": "FR12123456789",
        "iban": "FR7612345678901234567890123",
        "bic": "AGRIFRPP",
        "urssaf_expiration_date": datetime(2026, 6, 30),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    supplier_oid = supplier.inserted_id
    print(f"   → supplier_id = {supplier_oid}")

    print("\n[2/3] Création du DocumentGroup...")
    db.document_groups.delete_many({"name": "Test SUP001"})
    group = db.document_groups.insert_one({
        "name": "Test SUP001",
        "status": "processing",
        "pipeline_step": "ocr",
        "state": "pending",
        "validation_result": "pending",
        "supplier": supplier_oid,
        "fraud_flags": [],
        "anomalies": [],
        "extracted_summary": {},
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    group_oid = group.inserted_id
    print(f"   → group_id = {group_oid}")

    return group_oid

def create_document_file(group_oid, doc_type, file_path):
    filename = os.path.basename(file_path)
    stored_name = filename
    container_path = f"/data/raw/{group_oid}/{stored_name}"

    doc = db.documents.insert_one({
        "group": group_oid,
        "original_name": filename,
        "stored_name": stored_name,
        "file_path": container_path,
        "file_type": "pdf",
        "mime_type": "application/pdf",
        "document_type": "unknown",
        "analysis_status": "pending",
        "ocr_text": None,
        "extracted_data": {},
        "anomalies": [],
        "confidence_score": None,
        "needs_manual_review": False,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    return doc.inserted_id, container_path

def copy_file_to_container(group_oid, file_path):
    """Copie le fichier dans le volume Docker via docker cp."""
    filename = os.path.basename(file_path)
    container_dir = f"/data/raw/{group_oid}"

    subprocess.run(
        ["docker", "exec", AIRFLOW_CONTAINER, "mkdir", "-p", container_dir],
        check=True
    )
    subprocess.run(
        ["docker", "cp", file_path, f"{AIRFLOW_CONTAINER}:{container_dir}/{filename}"],
        check=True
    )
    print(f"   → copié dans {container_dir}/{filename}")

def get_airflow_token():
    """Obtient un token JWT depuis l'API Airflow 3.x."""
    response = requests.post(
        f"{AIRFLOW_URL}/auth/token",
        json={"username": AIRFLOW_USER, "password": AIRFLOW_PASSWORD},
        timeout=10,
    )
    if response.status_code in (200, 201):
        return response.json().get("access_token")
    raise Exception(f"Impossible d'obtenir le token Airflow : {response.status_code} {response.text}")


def trigger_dag(file_path, document_id, group_id):
    token = get_airflow_token()
    response = requests.post(
        f"{AIRFLOW_URL}/api/v2/dags/document_pipeline/dagRuns",
        json={
            "logical_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "conf": {
                "file_path": file_path,
                "document_id": str(document_id),
                "group_id": str(group_id),
            }
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if response.status_code in (200, 201):
        run_id = response.json().get("dag_run_id")
        print(f"   → DAG déclenché : {run_id}")
    else:
        print(f"   ✗ Erreur {response.status_code} : {response.text}")

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("  TEST PIPELINE AIRFLOW — SUP001 (conforme)")
    print("=" * 60)
    print(f"  [debug] Airflow password utilisé : '{AIRFLOW_PASSWORD}'")

    group_oid = setup_test_data()

    print("\n[3/3] Déclenchement des 3 runs du pipeline...")
    for doc_type, file_path in FILES.items():
        print(f"\n  ▶ {doc_type.upper()} — {os.path.basename(file_path)}")
        copy_file_to_container(group_oid, file_path)
        doc_id, container_path = create_document_file(group_oid, doc_type, file_path)
        trigger_dag(container_path, doc_id, group_oid)
        time.sleep(2)  # Évite les conflits de dagRun

    client.close()

    print("\n" + "=" * 60)
    print(f"  group_id : {group_oid}")
    print(f"  Airflow  : {AIRFLOW_URL}")
    print(f"  Mongo    : http://localhost:8081 (mongo-express)")
    print("=" * 60)
    print("  Suivi dans l'UI Airflow → DAG 'document_pipeline'")
