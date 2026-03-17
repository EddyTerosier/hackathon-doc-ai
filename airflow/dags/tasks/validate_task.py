def run_validation(**context):
    ti = context["ti"]

    analysis = ti.xcom_pull(task_ids="classify_extract_task")

    # TODO: remplacer par les vraies règles métier (Personne 4)
    return {
        "status": "conforme",
        "document_type": analysis["document_type"],
        "anomalies": []
    }
