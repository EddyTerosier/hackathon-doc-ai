def run_classify_and_extract(**context):
    ti = context["ti"]

    text = ti.xcom_pull(task_ids="ocr_task")

    # TODO: remplacer par la vraie classification + extraction (Personne 3)
    return {
        "document_type": "facture",
        "champs": {
            "supplier_name": "Mock Supplier",
            "siret": "12345678901234",
            "tva": "FR12345678901",
            "date_emission": "2024-01-01",
            "montant_ht": 100.0,
            "montant_ttc": 120.0,
        }
    }
