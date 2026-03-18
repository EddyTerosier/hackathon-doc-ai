"""
Test du callback d'erreur Airflow.

Déclenche le pipeline avec un fichier inexistant pour vérifier que :
  1. pipeline_errors contient une entrée avec task_id='ocr_task'
  2. documents[].analysis_status = 'failed'
  3. document_groups.state = 'non_compliant' (après finalisation)

Prérequis :
    docker-compose up airflow mongo -d

Usage :
    python scripts/test_callback.py
"""

import os
import json
import subprocess
import time
from datetime import datetime, timezone
from bson import ObjectId
from pymongo import MongoClient
import requests

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI         = "mongodb://admin:admin123@localhost:27017/?authSource=admin"
DB_NAME           = "hackathon_db"
AIRFLOW_URL       = "http://localhost:8080"
AIRFLOW_USER      = "admin"
AIRFLOW_CONTAINER = "hackathon-airflow"

FAKE_FILE_PATH = "/data/raw/fake_callback_test/inexistant.pdf"

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_airflow_password():
    if pw := os.getenv("AIRFLOW_PASSWORD"):
        return pw
    try:
        result = subprocess.run(
            ["docker", "exec", AIRFLOW_CONTAINER,
             "cat", "/opt/airflow/simple_auth_manager_passwords.json.generated"],
            capture_output=True, text=True,
        )
        data = json.loads(result.stdout.strip())
        return list(data.values())[0]
    except Exception as e:
        print(f"  [warning] lecture password échouée : {e}")
        return "admin"


def get_airflow_token(password):
    resp = requests.post(
        f"{AIRFLOW_URL}/auth/token",
        json={"username": AIRFLOW_USER, "password": password},
        timeout=10,
    )
    if resp.status_code in (200, 201):
        return resp.json().get("access_token")
    raise Exception(f"Token Airflow impossible : {resp.status_code} {resp.text}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  TEST CALLBACK — Fichier inexistant → on_failure_callback")
    print("=" * 60)

    password = _get_airflow_password()
    token    = get_airflow_token(password)

    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]

    # ── Création des documents de test en MongoDB ─────────────────────────────
    print("\n[1/3] Création DocumentGroup + DocumentFile en MongoDB...")

    group_oid = db.document_groups.insert_one({
        "name":              "Test Callback Error",
        "status":            "processing",
        "pipeline_step":     "ocr",
        "state":             "pending",
        "validation_result": "pending",
        "supplier":          None,
        "fraud_flags":       [],
        "anomalies":         [],
        "extracted_summary": {},
        "created_at":        datetime.now(timezone.utc),
        "updated_at":        datetime.now(timezone.utc),
    }).inserted_id

    doc_oid = db.documents.insert_one({
        "group":               group_oid,
        "original_name":       "inexistant.pdf",
        "stored_name":         "inexistant.pdf",
        "file_path":           FAKE_FILE_PATH,
        "file_type":           "pdf",
        "mime_type":           "application/pdf",
        "document_type":       "unknown",
        "analysis_status":     "pending",
        "ocr_text":            None,
        "extracted_data":      {},
        "anomalies":           [],
        "confidence_score":    None,
        "needs_manual_review": False,
        "created_at":          datetime.now(timezone.utc),
        "updated_at":          datetime.now(timezone.utc),
    }).inserted_id

    print(f"  group_id    = {group_oid}")
    print(f"  document_id = {doc_oid}")
    print(f"  file_path   = {FAKE_FILE_PATH}  ← n'existe pas dans le container")

    # ── Déclenchement du DAG avec le fichier fictif ───────────────────────────
    print("\n[2/3] Déclenchement du DAG avec le fichier inexistant...")
    resp = requests.post(
        f"{AIRFLOW_URL}/api/v2/dags/document_pipeline/dagRuns",
        json={
            "logical_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "conf": {
                "file_path":   FAKE_FILE_PATH,
                "document_id": str(doc_oid),
                "group_id":    str(group_oid),
            },
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )

    if resp.status_code in (200, 201):
        run_id = resp.json().get("dag_run_id")
        print(f"  DAG déclenché : {run_id}")
    else:
        print(f"  ✗ Erreur trigger : {resp.status_code} {resp.text}")
        client.close()
        raise SystemExit(1)

    # ── Attente que le callback s'exécute ─────────────────────────────────────
    print("\n[3/3] Attente du callback (max 90s)...")
    start = time.time()
    pipeline_error = None
    doc_final      = None

    while time.time() - start < 90:
        pipeline_error = db.pipeline_errors.find_one(
            {"document_id": str(doc_oid)},
            sort=[("timestamp", -1)],
        )
        doc_final = db.documents.find_one({"_id": doc_oid})
        elapsed   = int(time.time() - start)

        if pipeline_error or (doc_final and doc_final.get("analysis_status") == "failed"):
            print(f"  Callback détecté après {elapsed}s")
            break

        print(f"  ... en attente ({elapsed}s)", end="\r")
        time.sleep(3)
    else:
        print(f"\n  [timeout] aucune réponse après 90s")

    # ── Vérification ─────────────────────────────────────────────────────────
    print("\n  Résultats :")
    all_ok = True

    def check(label, condition):
        global all_ok
        mark = "✓" if condition else "✗"
        if not condition:
            all_ok = False
        print(f"  {mark} {label}")

    # Check 1 : pipeline_errors alimenté
    if pipeline_error:
        check(
            f"pipeline_errors : task_id='{pipeline_error.get('task_id')}' | "
            f"error='{str(pipeline_error.get('error', ''))[:80]}'",
            True,
        )
    else:
        check("pipeline_errors contient une entrée pour ce document", False)

    # Check 2 : document.analysis_status = "failed"
    doc_status = doc_final.get("analysis_status") if doc_final else "N/A"
    check(
        f"document.analysis_status = 'failed' — trouvé: '{doc_status}'",
        doc_status == "failed",
    )

    # Check 3 : group finalisé (update_status_task doit avoir tourné sur les autres docs aussi,
    #           ici 1 seul doc donc le groupe doit être finalisé)
    group = db.document_groups.find_one({"_id": group_oid})
    group_status = group.get("status") if group else "N/A"
    check(
        f"group.status = 'completed' — trouvé: '{group_status}'",
        group_status == "completed",
    )

    # Check 4 : group.state non_compliant (doc failed → anomalie technique)
    group_state = group.get("state") if group else "N/A"
    check(
        f"group.state = 'non_compliant' — trouvé: '{group_state}'",
        group_state == "non_compliant",
    )

    client.close()

    status_label = "PASS ✓" if all_ok else "FAIL ✗"
    print(f"\n  {status_label} — callback on_failure")
    print("\n" + "=" * 60)
    print(f"  Airflow UI : {AIRFLOW_URL}")
    print(f"  Mongo UI   : http://localhost:8081  → pipeline_errors")
    print("=" * 60)
