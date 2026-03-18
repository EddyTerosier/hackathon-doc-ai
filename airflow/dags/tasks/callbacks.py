import os
import traceback
from datetime import datetime, timezone
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def on_task_failure(context):
    """Callback déclenché automatiquement par Airflow quand une tâche échoue.
    Enregistre l'erreur technique en MongoDB et met à jour le DocumentFile.
    """
    task_instance = context.get("task_instance")
    task_id = task_instance.task_id
    dag_id = context.get("dag").dag_id
    run_id = context.get("run_id", "unknown")
    exception = context.get("exception")
    error_msg = str(exception) if exception else "unknown error"

    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}
    document_id = conf.get("document_id")
    group_id = conf.get("group_id")

    now = datetime.now(timezone.utc)

    error_doc = {
        "type": "technical",
        "dag_id": dag_id,
        "run_id": run_id,
        "pipeline_step": task_id,
        "document_id": document_id,
        "group_id": group_id,
        "status": "error",
        "error": error_msg,
        "traceback": traceback.format_exc(),
        "occurred_at": now.isoformat(),
    }

    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]

        db.pipeline_errors.insert_one(error_doc)

        # Met à jour le DocumentFile pour que le frontend et update_status_task sachent
        if document_id:
            from bson import ObjectId
            if ObjectId.is_valid(document_id):
                db.documents.update_one(
                    {"_id": ObjectId(document_id)},
                    {"$set": {
                        "analysis_status": "failed",
                        "pipeline_step": task_id,
                        "error": error_msg,
                        "updated_at": now,
                    }}
                )

        client.close()
    except Exception as e:
        print(f"[callback] Impossible d'écrire l'erreur en MongoDB : {e}")
