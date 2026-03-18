import os
import sys
from datetime import date
from bson import ObjectId
from pymongo import MongoClient

sys.path.insert(0, "/opt/airflow")
from backend.extraction.classifier import luhn_siret, parse_amount  # noqa: E402

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def run_validation(**context):
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}

    group_id = conf.get("group_id")
    analysis = ti.xcom_pull(task_ids="classify_extract_task")
    champs = analysis.get("champs", {})

    # Mapping classifier → valeurs du modèle DocumentFile
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

    # Récupération du fournisseur via le DocumentGroup
    supplier = None
    if group_id and ObjectId.is_valid(group_id):
        group = db.document_groups.find_one({"_id": ObjectId(group_id)})
        if group and group.get("supplier"):
            supplier = db.suppliers.find_one({"_id": group["supplier"]})

    # Règles métier
    if doc_type == "invoice":
        montants = champs.get("montants", [])
        montant_ht = parse_amount(champs.get("montant_ht"))
        montant_ttc = parse_amount(champs.get("montant_ttc"))

        if len(montants) < 2:
            anomalies.append("montants HT/TTC manquants")
        if not champs.get("tva"):
            anomalies.append("numéro TVA manquant")

        # TTC doit être >= HT
        if montant_ht is not None and montant_ttc is not None:
            if montant_ttc < montant_ht:
                anomalies.append("montant TTC inférieur au montant HT")
                fraud_flags.append("ttc_lt_ht")

        # Validation SIRET via algorithme de Luhn
        if champs.get("siret"):
            siret = champs["siret"][0]
            if not luhn_siret(siret):
                anomalies.append(f"SIRET invalide (échec contrôle Luhn) : {siret}")
                fraud_flags.append("siret_invalid")
            elif supplier and supplier.get("siret") != siret:
                anomalies.append("SIRET facture incohérent avec le fournisseur du dossier")
                fraud_flags.append("siret_mismatch")

    elif doc_type == "urssaf_certificate":
        # Validation SIRET URSSAF via Luhn
        if champs.get("siret"):
            siret = champs["siret"][0]
            if not luhn_siret(siret):
                anomalies.append(f"SIRET URSSAF invalide (échec contrôle Luhn) : {siret}")
                fraud_flags.append("siret_invalid")

        if supplier and supplier.get("urssaf_expiration_date"):
            exp = supplier["urssaf_expiration_date"]
            if hasattr(exp, "date"):
                exp = exp.date()
            if isinstance(exp, date) and exp < date.today():
                anomalies.append("attestation URSSAF expirée")
                fraud_flags.append("date_expired")
        elif not champs.get("dates"):
            anomalies.append("date d'expiration URSSAF manquante")

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

    # Mise à jour des fraud_flags sur le DocumentGroup
    if fraud_flags and group_id and ObjectId.is_valid(group_id):
        db.document_groups.update_one(
            {"_id": ObjectId(group_id)},
            {"$addToSet": {"fraud_flags": {"$each": fraud_flags}}}
        )

    client.close()

    final_status = "non_conforme" if anomalies else "conforme"

    return {
        "status": final_status,
        "document_type": doc_type,
        "anomalies": anomalies,
        "fraud_flags": fraud_flags,
    }
