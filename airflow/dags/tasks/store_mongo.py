import os
from pymongo import MongoClient
from datetime import datetime, timezone

""" Lit la variable d'env MONGO_URI injectée par Docker. Local : localhost"""
MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"

""" Construction du document MongoDB """
""" Puis ecriture dans MongoDB """
def store_results(**context):

    ti = context["ti"]

    ocr_result = ti.xcom_pull(task_ids="ocr_task")
    analysis_result = ti.xcom_pull(task_ids="classify_extract_task")

    document = {
        "stored_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "ocr_text": ocr_result,
        "document_type": analysis_result["document_type"],
        "extracted_data": analysis_result["champs"],
        "status": "processing",
        "pipeline_step": "store_db",
        "error": None,
    }

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    result = db.documents.insert_one(document)

    client.close()

    document["_id"] = str(result.inserted_id)
    document["stored_at"] = document["stored_at"].isoformat()

    return document
