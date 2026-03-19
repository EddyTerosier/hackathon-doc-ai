import os
from bson import ObjectId
from pymongo import MongoClient
from datetime import datetime, timezone

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def store_results(**context):
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}

    document_id = conf.get("document_id")
    ocr_result = ti.xcom_pull(task_ids="ocr_task")
    analysis_result = ti.xcom_pull(task_ids="classify_extract_task")

    # Mapping classifier → valeurs du modèle DocumentFile
    DOC_TYPE_MAP = {
        "facture": "invoice",
        "attestation_urssaf": "urssaf_certificate",
        "rib": "bank_details",
        "inconnu": "unknown",
    }
    doc_type = DOC_TYPE_MAP.get(analysis_result["document_type"], "unknown")

    update_fields = {
        "ocr_text": ocr_result,
        "document_type": doc_type,
        "extracted_data": analysis_result["champs"],
        "confidence_score": analysis_result.get("confidence"),
        "analysis_status": "processing",
        "pipeline_step": "store_db",
        "error": None,
        "updated_at": datetime.now(timezone.utc),
    }

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    if document_id and ObjectId.is_valid(document_id):
        db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": update_fields}
        )
    else:
        # Fallback si pas de document_id (tests locaux sans dag_run.conf)
        update_fields["stored_at"] = datetime.now(timezone.utc).isoformat()
        update_fields["updated_at"] = update_fields["updated_at"].isoformat()
        db.documents.insert_one(update_fields)

    client.close()

    return {
        "document_id": document_id,
        "document_type": doc_type,
        "classifier_type": analysis_result["document_type"],
    }
