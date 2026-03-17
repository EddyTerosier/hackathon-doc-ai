import os
import traceback
from datetime import datetime, timezone
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def on_task_failure(context):
    """Callback déclenché automatiquement par Airflow quand une tâche échoue.
    Enregistre l'erreur technique en MongoDB pour monitoring.
    """
    task_id = context.get("task_instance").task_id
    dag_id = context.get("dag").dag_id
    run_id = context.get("run_id", "unknown")
    exception = context.get("exception")

    error_doc = {
        "type": "technical",
        "dag_id": dag_id,
        "run_id": run_id,
        "pipeline_step": task_id,
        "status": "error",
        "error": str(exception) if exception else "unknown error",
        "traceback": traceback.format_exc(),
        "occurred_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        client = MongoClient(MONGO_URI)
        client[DB_NAME].pipeline_errors.insert_one(error_doc)
        client.close()
    except Exception as e:
        print(f"[callback] Impossible d'écrire l'erreur en MongoDB : {e}")
