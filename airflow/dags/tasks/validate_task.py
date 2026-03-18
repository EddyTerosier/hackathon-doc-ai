import os
from datetime import date
from bson import ObjectId
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def run_validation(**context):
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}

    group_id = conf.get("group_id")
    analysis = ti.xcom_pull(task_ids="classify_extract_task")
    champs = analysis.get("champs", {})
    doc_type = analysis.get("document_type")
    anomalies = []

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    # Récupération du fournisseur via le DocumentGroup
    supplier = None
    if group_id and ObjectId.is_valid(group_id):
        group = db.document_groups.find_one({"_id": ObjectId(group_id)})
        if group and group.get("supplier"):
            supplier = db.suppliers.find_one({"_id": group["supplier"]})

    # Règles métier (project_scope.md)
    if doc_type == "facture":
        montants = champs.get("montants", [])
        if len(montants) < 2:
            anomalies.append("montants HT/TTC manquants")
        if not champs.get("tva"):
            anomalies.append("numéro TVA manquant")
        if supplier and champs.get("siret"):
            if supplier.get("siret") != champs["siret"][0]:
                anomalies.append("SIRET facture incohérent avec le fournisseur du dossier")

    elif doc_type == "attestation_urssaf":
        if supplier and supplier.get("urssaf_expiration_date"):
            exp = supplier["urssaf_expiration_date"]
            if isinstance(exp, date) and exp < date.today():
                anomalies.append("attestation URSSAF expirée")
        elif not champs.get("dates"):
            anomalies.append("date d'expiration URSSAF manquante")

    elif doc_type == "rib":
        if not champs.get("iban"):
            anomalies.append("IBAN manquant")
        if not champs.get("bic"):
            anomalies.append("BIC manquant")
        if supplier and champs.get("iban") and supplier.get("iban"):
            extracted_iban = champs["iban"][0].replace(" ", "")
            known_iban = supplier["iban"].replace(" ", "")
            if extracted_iban != known_iban:
                anomalies.append("IBAN ne correspond pas au fournisseur du dossier")

    client.close()

    final_status = "non_conforme" if anomalies else "conforme"

    return {
        "status": final_status,
        "document_type": doc_type,
        "anomalies": anomalies,
    }
