import os
import sys
from datetime import date, datetime

from bson import ObjectId
from pymongo import MongoClient

sys.path.insert(0, "/opt/airflow")
from backend.extraction.classifier import parse_amount  # noqa: E402

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def _parse_extracted_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    value = str(value).strip()
    if not value:
        return None

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y/%m/%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue

    return None


def _latest_valid_date(values):
    parsed = [_parse_extracted_date(value) for value in (values or [])]
    parsed = [value for value in parsed if value is not None]
    return max(parsed) if parsed else None


def _first_or_none(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _group_sirets(db, group_id, current_doc_type):
    if not group_id or not ObjectId.is_valid(group_id):
        return []

    docs = db.documents.find(
        {"group": ObjectId(group_id), "document_type": {"$in": ["invoice", "urssaf_certificate"]}},
        {"document_type": 1, "extracted_data": 1},
    )

    pairs = []
    for doc in docs:
        doc_type = doc.get("document_type")
        siret = _first_or_none((doc.get("extracted_data") or {}).get("siret"))
        if siret:
            pairs.append((doc_type, str(siret).replace(" ", "")))
    return [pair for pair in pairs if pair[0] != current_doc_type]


def run_validation(**context):
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}

    group_id = conf.get("group_id")
    analysis = ti.xcom_pull(task_ids="classify_extract_task")
    champs = analysis.get("champs", {})

    DOC_TYPE_MAP = {
        "facture": "invoice",
        "attestation_urssaf": "urssaf_certificate",
        "rib": "bank_details",
        "inconnu": "unknown",
    }
    doc_type = DOC_TYPE_MAP.get(analysis.get("document_type", "inconnu"), "unknown")
    anomalies = []
    fraud_flags = []

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    supplier = None
    if group_id and ObjectId.is_valid(group_id):
        group = db.document_groups.find_one({"_id": ObjectId(group_id)})
        if group and group.get("supplier"):
            supplier = db.suppliers.find_one({"_id": group["supplier"]})

    if doc_type == "unknown":
        anomalies.append("document illisible ou type non reconnu (OCR insuffisant)")

    elif doc_type == "invoice":
        montants = champs.get("montants", [])
        montant_ht = parse_amount(champs.get("montant_ht"))
        montant_ttc = parse_amount(champs.get("montant_ttc"))
        current_siret = _first_or_none(champs.get("siret"))

        if len(montants) < 2:
            anomalies.append("montants HT/TTC manquants")
        if not champs.get("tva"):
            anomalies.append("numÃ©ro TVA manquant")

        if montant_ht is not None and montant_ttc is not None and montant_ttc < montant_ht:
            anomalies.append("montant TTC infÃ©rieur au montant HT")
            fraud_flags.append("ttc_lt_ht")

        # Validation SIRET via algorithme de Luhn
        # if champs.get("siret"):
        #     siret = champs["siret"][0]
        #     if not luhn_siret(siret):
        #         anomalies.append(f"SIRET invalide (Ã©chec contrÃ´le Luhn) : {siret}")
        #         fraud_flags.append("siret_invalid")
        #     elif supplier and supplier.get("siret") != siret:
        #         anomalies.append("SIRET facture incohÃ©rent avec le fournisseur du dossier")
        #         fraud_flags.append("siret_mismatch")

        if current_siret:
            current_siret = str(current_siret).replace(" ", "")
            other_sirets = _group_sirets(db, group_id, "invoice")
            if any(other_siret != current_siret for _, other_siret in other_sirets):
                anomalies.append("SIRET facture incohÃ©rent avec les autres documents du dossier")
                fraud_flags.append("siret_mismatch")

    elif doc_type == "urssaf_certificate":
        current_siret = _first_or_none(champs.get("siret"))
        expiration_date = _latest_valid_date(champs.get("dates"))

        # Validation SIRET URSSAF via Luhn
        # if champs.get("siret"):
        #     siret = champs["siret"][0]
        #     if not luhn_siret(siret):
        #         anomalies.append(f"SIRET URSSAF invalide (Ã©chec contrÃ´le Luhn) : {siret}")
        #         fraud_flags.append("siret_invalid")

        if expiration_date is None and supplier and supplier.get("urssaf_expiration_date"):
            exp = supplier["urssaf_expiration_date"]
            if hasattr(exp, "date"):
                exp = exp.date()
            if isinstance(exp, date):
                expiration_date = exp

        if expiration_date and expiration_date < date.today():
            anomalies.append("attestation URSSAF expirÃ©e")
            fraud_flags.append("date_expired")
        elif expiration_date is None:
            anomalies.append("date d'expiration URSSAF manquante")

        if current_siret:
            current_siret = str(current_siret).replace(" ", "")
            other_sirets = _group_sirets(db, group_id, "urssaf_certificate")
            if any(other_siret != current_siret for _, other_siret in other_sirets):
                anomalies.append("SIRET URSSAF incohÃ©rent avec les autres documents du dossier")
                fraud_flags.append("siret_mismatch")

    elif doc_type == "bank_details":
        if not champs.get("iban"):
            anomalies.append("IBAN manquant")
        if not champs.get("bic"):
            anomalies.append("BIC manquant")
        if supplier and champs.get("iban") and supplier.get("iban"):
            extracted_iban = champs["iban"][0].replace(" ", "")
            known_iban = supplier["iban"].replace(" ", "")
            if extracted_iban != known_iban:
                anomalies.append("IBAN ne correspond pas au fournisseur du dossier")
                fraud_flags.append("iban_mismatch")

    if fraud_flags and group_id and ObjectId.is_valid(group_id):
        db.document_groups.update_one(
            {"_id": ObjectId(group_id)},
            {"$addToSet": {"fraud_flags": {"$each": fraud_flags}}},
        )

    client.close()

    final_status = "non_conforme" if anomalies else "conforme"

    return {
        "status": final_status,
        "document_type": doc_type,
        "anomalies": anomalies,
        "fraud_flags": fraud_flags,
    }
