def update_status(**context):
    ti = context["ti"]

    validation = ti.xcom_pull(task_ids="validation_task")

    # TODO: mettre à jour le statut en base (Personne 5)
    print(f"Statut final : {validation['status']} — type : {validation['document_type']}")
