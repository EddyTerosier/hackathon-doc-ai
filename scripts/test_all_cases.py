"""
Test de tous les scénarios du dataset contre le pipeline Airflow.

Scénarios testés :
  SUP001 conforme            → group.state: non_compliant (SIRET fictifs → Luhn échoue)
  SUP002 siret_incoherent    → fraud_flags: siret_invalid (URSSAF SIRET = 99999999999999)
  SUP003 attestation_expired → fraud_flags: date_expired (expiration 2026-01-15 < today)
  SUP004 invoice_degraded    → analysé normalement, OCR potentiellement dégradé
  SUP005 rib_missing_bic     → anomalies: BIC manquant
  SUP006 ttc_lower_than_ht   → fraud_flags: ttc_lt_ht

Note : tous les SIRETs du dataset sont fictifs et échouent la validation Luhn →
       siret_invalid sera présent dans fraud_flags pour tous les cas (invoice + urssaf).

Prérequis :
    docker-compose up airflow mongo -d

Usage :
    python scripts/test_all_cases.py               # tous les cas
    python scripts/test_all_cases.py SUP001 SUP006 # cas sélectionnés
    python scripts/test_all_cases.py --no-wait     # déclenche sans attendre ni vérifier
"""

import os
import sys
import json
import time
import subprocess
import argparse
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

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATASET_DIR = os.path.join(PROJECT_DIR, "dataset", "raw")

# ── Définition des scénarios ──────────────────────────────────────────────────
SCENARIOS = {
    "SUP001": {
        "label": "SUP001 — conforme",
        "note": "SIRET fictifs → siret_invalid systématique, pas de fraude métier",
        "supplier": {
            "name": "Alpha Conseil",
            "siret": "12345678901234",
            "vat_number": "FR12123456789",
            "iban": "FR7612345678901234567890123",
            "bic": "AGRIFRPP",
            "urssaf_expiration_date": datetime(2026, 6, 30),
        },
        "files": {
            "facture": os.path.join(DATASET_DIR, "facture", "FAC_SUP001_conforme.pdf"),
            "urssaf":  os.path.join(DATASET_DIR, "urssaf",  "URS_SUP001_conforme.pdf"),
            "rib":     os.path.join(DATASET_DIR, "rib",     "RIB_SUP001_conforme.pdf"),
        },
        "expect_flags_include":    [],        # aucun flag métier spécifique au scénario
        "expect_anomaly_keywords": [],
        "expect_group_state":      "non_compliant",  # siret_invalid → non_compliant
    },
    "SUP002": {
        "label": "SUP002 — siret_incoherent",
        "note": "URS_SUP002 contient SIRET 99999999999999 (différent du fournisseur)",
        "supplier": {
            "name": "Beta Services",
            "siret": "23456789012345",
            "vat_number": "FR23234567890",
            "iban": "FR7630001007941234567890185",
            "bic": "BNPAFRPP",
            "urssaf_expiration_date": datetime(2026, 7, 15),
        },
        "files": {
            "facture": os.path.join(DATASET_DIR, "facture", "FAC_SUP002_siret_incoherent.pdf"),
            "urssaf":  os.path.join(DATASET_DIR, "urssaf",  "URS_SUP002_siret_incoherent.pdf"),
            "rib":     os.path.join(DATASET_DIR, "rib",     "RIB_SUP002_siret_incoherent.pdf"),
        },
        "expect_flags_include":    ["siret_invalid"],
        "expect_anomaly_keywords": ["SIRET"],
        "expect_group_state":      "non_compliant",
    },
    "SUP003": {
        "label": "SUP003 — attestation_expired",
        "note": "urssaf_expiration_date = 2026-01-15, expirée → date_expired",
        "supplier": {
            "name": "Gamma Batiment",
            "siret": "34567890123456",
            "vat_number": "FR34345678901",
            "iban": "FR7610278000101234567890126",
            "bic": "CMCIFR2A",
            "urssaf_expiration_date": datetime(2026, 1, 15),  # intentionnellement expirée
        },
        "files": {
            "facture": os.path.join(DATASET_DIR, "facture", "FAC_SUP003_attestation_expired.pdf"),
            "urssaf":  os.path.join(DATASET_DIR, "urssaf",  "URS_SUP003_attestation_expired.pdf"),
            "rib":     os.path.join(DATASET_DIR, "rib",     "RIB_SUP003_attestation_expired.pdf"),
        },
        "expect_flags_include":    ["date_expired"],
        "expect_anomaly_keywords": ["expir"],
        "expect_group_state":      "non_compliant",
    },
    "SUP004": {
        "label": "SUP004 — invoice_degraded",
        "note": "Facture dégradée (blur) → OCR potentiellement incomplet, champs manquants possibles",
        "supplier": {
            "name": "Delta Logistique",
            "siret": "45678901234567",
            "vat_number": "FR45456789012",
            "iban": "FR7630011000011234567890153",
            "bic": "SOGEFRPP",
            "urssaf_expiration_date": datetime(2026, 8, 20),
        },
        "files": {
            "facture": os.path.join(PROJECT_DIR, "dataset", "raw", "degraded", "FAC_SUP004_invoice_degraded_blur.pdf"),
            "urssaf":  os.path.join(DATASET_DIR, "urssaf",  "URS_SUP004_invoice_degraded.pdf"),
            "rib":     os.path.join(DATASET_DIR, "rib",     "RIB_SUP004_invoice_degraded.pdf"),
        },
        "expect_flags_include":    [],
        "expect_anomaly_keywords": [],
        "expect_group_state":      "non_compliant",
    },
    "SUP005": {
        "label": "SUP005 — rib_missing_bic",
        "note": "RIB sans BIC → anomalie 'BIC manquant'",
        "supplier": {
            "name": "Epsilon Tech",
            "siret": "56789012345678",
            "vat_number": "FR56567890123",
            "iban": "FR7614508000401234567890128",
            "bic": "",
            "urssaf_expiration_date": datetime(2026, 9, 10),
        },
        "files": {
            "facture": os.path.join(DATASET_DIR, "facture", "FAC_SUP005_rib_missing_bic.pdf"),
            "urssaf":  os.path.join(DATASET_DIR, "urssaf",  "URS_SUP005_rib_missing_bic.pdf"),
            "rib":     os.path.join(DATASET_DIR, "rib",     "RIB_SUP005_rib_missing_bic.pdf"),
        },
        "expect_flags_include":    [],
        "expect_anomaly_keywords": ["BIC"],
        "expect_group_state":      "non_compliant",
    },
    "SUP006": {
        "label": "SUP006 — ttc_lower_than_ht",
        "note": "montant_ttc (1400) < montant_ht (1500) → fraud_flag ttc_lt_ht",
        "supplier": {
            "name": "Zeta Formation",
            "siret": "67890123456789",
            "vat_number": "FR67678901234",
            "iban": "FR7630004000031234567890143",
            "bic": "BNPAFRPPXXX",
            "urssaf_expiration_date": datetime(2026, 10, 5),
        },
        "files": {
            "facture": os.path.join(DATASET_DIR, "facture", "FAC_SUP006_ttc_lower_than_ht.pdf"),
            "urssaf":  os.path.join(DATASET_DIR, "urssaf",  "URS_SUP006_ttc_lower_than_ht.pdf"),
            "rib":     os.path.join(DATASET_DIR, "rib",     "RIB_SUP006_ttc_lower_than_ht.pdf"),
        },
        "expect_flags_include":    ["ttc_lt_ht"],
        "expect_anomaly_keywords": ["TTC"],
        "expect_group_state":      "non_compliant",
    },
}

# ── Airflow ───────────────────────────────────────────────────────────────────

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


def trigger_dag(token, file_path, document_id, group_id):
    resp = requests.post(
        f"{AIRFLOW_URL}/api/v2/dags/document_pipeline/dagRuns",
        json={
            "logical_date": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "conf": {
                "file_path":    file_path,
                "document_id":  str(document_id),
                "group_id":     str(group_id),
            },
        },
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    if resp.status_code in (200, 201):
        return resp.json().get("dag_run_id")
    raise Exception(f"Trigger DAG échoué : {resp.status_code} {resp.text}")


# ── Docker ────────────────────────────────────────────────────────────────────

def copy_file_to_container(group_oid, file_path):
    filename = os.path.basename(file_path)
    container_dir = f"/data/raw/{group_oid}"
    subprocess.run(
        ["docker", "exec", AIRFLOW_CONTAINER, "mkdir", "-p", container_dir],
        check=True,
    )
    subprocess.run(
        ["docker", "cp", file_path, f"{AIRFLOW_CONTAINER}:{container_dir}/{filename}"],
        check=True,
    )
    return f"{container_dir}/{filename}"


# ── MongoDB ───────────────────────────────────────────────────────────────────

def setup_supplier(db, sup_data):
    db.suppliers.delete_many({"name": sup_data["name"]})
    doc = {**sup_data, "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)}
    return db.suppliers.insert_one(doc).inserted_id


def setup_group(db, name, supplier_oid):
    db.document_groups.delete_many({"name": name})
    return db.document_groups.insert_one({
        "name":              name,
        "status":            "processing",
        "pipeline_step":     "ocr",
        "state":             "pending",
        "validation_result": "pending",
        "supplier":          supplier_oid,
        "fraud_flags":       [],
        "anomalies":         [],
        "extracted_summary": {},
        "created_at":        datetime.now(timezone.utc),
        "updated_at":        datetime.now(timezone.utc),
    }).inserted_id


def create_document_file(db, group_oid, filename, container_path):
    ext = os.path.splitext(filename)[1].lstrip(".")
    return db.documents.insert_one({
        "group":               group_oid,
        "original_name":       filename,
        "stored_name":         filename,
        "file_path":           container_path,
        "file_type":           ext,
        "mime_type":           f"application/{ext}",
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


# ── Attente + vérification ────────────────────────────────────────────────────

def wait_for_group(db, group_oid, timeout=180):
    """Poll jusqu'à ce que tous les docs soient analyzed ou failed."""
    start = time.time()
    while time.time() - start < timeout:
        total    = db.documents.count_documents({"group": group_oid})
        terminal = db.documents.count_documents({
            "group": group_oid,
            "analysis_status": {"$in": ["analyzed", "failed"]},
        })
        elapsed = int(time.time() - start)
        print(f"  ... {terminal}/{total} docs terminés ({elapsed}s)", end="\r")
        if total > 0 and terminal >= total:
            print()
            return True
        time.sleep(5)
    print()
    return False


def verify_case(db, scenario, group_oid):
    """Compare les résultats MongoDB aux attentes du scénario. Retourne (ok, lignes)."""
    checks = []
    all_ok = True

    def check(label, condition):
        nonlocal all_ok
        mark = "✓" if condition else "✗"
        if not condition:
            all_ok = False
        checks.append(f"  {mark} {label}")

    group = db.document_groups.find_one({"_id": group_oid})
    docs  = list(db.documents.find({"group": group_oid}))

    # ── Checks communs ────────────────────────────────────────────────────────
    check("3 documents présents", len(docs) == 3)

    analyzed = [d for d in docs if d.get("analysis_status") == "analyzed"]
    check(f"tous analyzed ({len(analyzed)}/3)", len(analyzed) == 3)

    doc_types = {d.get("document_type") for d in docs}
    check(
        f"document_types = {{invoice, urssaf_certificate, bank_details}} — trouvé: {doc_types}",
        doc_types == {"invoice", "urssaf_certificate", "bank_details"},
    )

    docs_with_ocr = [d for d in docs if d.get("ocr_text")]
    check(
        f"ocr_text non vide ({len(docs_with_ocr)}/3 docs)",
        len(docs_with_ocr) == 3,
    )

    docs_with_data = [d for d in docs if d.get("extracted_data")]
    check(
        f"extracted_data non vide ({len(docs_with_data)}/3 docs)",
        len(docs_with_data) == 3,
    )

    docs_with_conf = [d for d in docs if d.get("confidence_score") is not None]
    check(
        f"confidence_score présent ({len(docs_with_conf)}/3 docs)",
        len(docs_with_conf) == 3,
    )

    check("group.status = 'completed'", group.get("status") == "completed")
    check(
        f"group.state = '{scenario['expect_group_state']}' — trouvé: '{group.get('state')}'",
        group.get("state") == scenario["expect_group_state"],
    )

    # ── Checks spécifiques au scénario ────────────────────────────────────────
    group_flags    = group.get("fraud_flags", [])
    group_anomalies = group.get("anomalies", [])

    for flag in scenario["expect_flags_include"]:
        check(f"fraud_flag '{flag}' présent — flags: {group_flags}", flag in group_flags)

    for keyword in scenario["expect_anomaly_keywords"]:
        found = any(keyword.lower() in a.lower() for a in group_anomalies)
        check(
            f"anomalie contenant '{keyword}' — anomalies: {group_anomalies[:2]}",
            found,
        )

    return all_ok, checks


# ── Exécution d'un scénario ───────────────────────────────────────────────────

def run_case(db, token, scenario_id, scenario, no_wait=False):
    print(f"\n{'─' * 60}")
    print(f"  ▶  {scenario['label']}")
    print(f"  ℹ  {scenario['note']}")
    print(f"{'─' * 60}")

    # Vérification des fichiers locaux
    missing = [p for p in scenario["files"].values() if not os.path.exists(p)]
    if missing:
        for p in missing:
            print(f"  ✗ Fichier manquant : {p}")
        return None

    # Préparation MongoDB
    supplier_oid = setup_supplier(db, scenario["supplier"])
    group_oid    = setup_group(db, f"Test {scenario_id}", supplier_oid)
    print(f"  supplier_id = {supplier_oid}")
    print(f"  group_id    = {group_oid}")

    # Copie + déclenchement DAG pour chaque fichier
    for label, file_path in scenario["files"].items():
        filename       = os.path.basename(file_path)
        container_path = copy_file_to_container(group_oid, file_path)
        doc_id         = create_document_file(db, group_oid, filename, container_path)
        run_id         = trigger_dag(token, container_path, doc_id, group_oid)
        print(f"  → {label:8s}: {run_id}")
        time.sleep(2)   # évite conflits de dagRun sur la même logical_date

    if no_wait:
        print(f"\n  [--no-wait] group_id: {group_oid}")
        return group_oid

    # Attente pipeline
    print(f"\n  ⏳ Attente pipeline (max 3 min)...")
    if not wait_for_group(db, group_oid):
        print(f"  ✗ Timeout — pipeline non terminé dans les délais")
        return group_oid

    # Vérification
    ok, result_lines = verify_case(db, scenario, group_oid)
    print()
    for line in result_lines:
        print(line)
    status_label = "PASS ✓" if ok else "FAIL ✗"
    print(f"\n  {status_label} — {scenario['label']}")

    return group_oid


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test pipeline Airflow — tous les scénarios dataset")
    parser.add_argument(
        "cases", nargs="*",
        help="Scénarios à tester : SUP001 SUP002 … (défaut : tous)",
    )
    parser.add_argument(
        "--no-wait", action="store_true",
        help="Déclenche les DAGs sans attendre ni vérifier les résultats",
    )
    args = parser.parse_args()

    cases_to_run = args.cases if args.cases else list(SCENARIOS.keys())
    unknown = [c for c in cases_to_run if c not in SCENARIOS]
    if unknown:
        print(f"Cas inconnus : {unknown}")
        print(f"Disponibles  : {list(SCENARIOS.keys())}")
        sys.exit(1)

    password = _get_airflow_password()
    token    = get_airflow_token(password)

    client = MongoClient(MONGO_URI)
    db     = client[DB_NAME]

    print("=" * 60)
    print(f"  TEST PIPELINE — {', '.join(cases_to_run)}")
    print("=" * 60)

    group_ids = {}
    for sid in cases_to_run:
        gid = run_case(db, token, sid, SCENARIOS[sid], no_wait=args.no_wait)
        group_ids[sid] = gid

    client.close()

    print("\n" + "=" * 60)
    print("  RÉSUMÉ DES group_id")
    print("=" * 60)
    for sid, gid in group_ids.items():
        print(f"  {sid}: {gid}")
    print(f"\n  Airflow UI : {AIRFLOW_URL}")
    print(f"  Mongo UI   : http://localhost:8081")
    print("=" * 60)
