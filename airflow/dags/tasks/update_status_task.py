import os
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def update_status(**context):
    ti = context["ti"]
    dag_run = context.get("dag_run")
    conf = dag_run.conf or {} if dag_run else {}

    document_id = conf.get("document_id")
    group_id = conf.get("group_id")
    validation = ti.xcom_pull(task_ids="validation_task")

    final_status = validation["status"]      # conforme / non_conforme
    anomalies = validation.get("anomalies", [])
    doc_type = validation.get("document_type")

    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    now = datetime.now(timezone.utc)

    # Mise à jour du DocumentFile
    if document_id and ObjectId.is_valid(document_id):
        db.documents.update_one(
            {"_id": ObjectId(document_id)},
            {"$set": {
                "analysis_status": "analyzed",
                "document_type": doc_type,
                "anomalies": anomalies,
                "needs_manual_review": len(anomalies) > 0,
                "updated_at": now,
            }}
        )

    # Mise à jour du DocumentGroup seulement si tous les fichiers sont analysés
    if group_id and ObjectId.is_valid(group_id):
        group_oid = ObjectId(group_id)
        total = db.documents.count_documents({"group": group_oid})
        terminal = db.documents.count_documents({
            "group": group_oid,
            "analysis_status": {"$in": ["analyzed", "failed"]}
        })

        if total > 0 and terminal >= total:
            # Récupère toutes les anomalies + types de tous les fichiers du groupe
            all_anomalies = []
            present_types = set()
            docs_data = list(db.documents.find(
                {"group": group_oid},
                {"anomalies": 1, "document_type": 1, "analysis_status": 1, "extracted_data": 1}
            ))
            for doc in docs_data:
                if doc.get("analysis_status") == "failed":
                    all_anomalies.append(f"erreur technique lors du traitement ({doc.get('document_type', 'document inconnu')})")
                else:
                    all_anomalies.extend(doc.get("anomalies", []))
                if doc.get("document_type"):
                    present_types.add(doc["document_type"])

            # Vérification complétude du dossier (3 types requis)
            required_types = {"invoice", "urssaf_certificate", "bank_details"}
            missing_types = required_types - present_types
            for t in missing_types:
                all_anomalies.append(f"dossier incomplet : document manquant ({t})")

            group_state = "compliant" if not all_anomalies else "non_compliant"

            # Résumé consolidé pour le CRM / outil conformité
            extracted_summary = {}
            for doc in docs_data:
                data = doc.get("extracted_data") or {}
                dtype = doc.get("document_type")
                if dtype == "invoice":
                    extracted_summary["supplier_name"] = data.get("tva", [None])[0]
                    extracted_summary["siret"]         = data.get("siret", [None])[0]
                    extracted_summary["tva"]           = data.get("tva", [None])[0]
                    extracted_summary["montant_ht"]    = data.get("montant_ht")
                    extracted_summary["montant_ttc"]   = data.get("montant_ttc")
                    extracted_summary["date_emission"] = data.get("dates", [None])[0]
                elif dtype == "bank_details":
                    extracted_summary["iban"] = data.get("iban", [None])[0]
                    extracted_summary["bic"]  = data.get("bic", [None])[0]
                elif dtype == "urssaf_certificate":
                    extracted_summary["urssaf_valid_until"] = data.get("dates", [None])[0]

            db.document_groups.update_one(
                {"_id": group_oid},
                {"$set": {
                    "status":            "completed",
                    "state":             group_state,
                    "validation_result": "valid" if not all_anomalies else "invalid",
                    "anomalies":         all_anomalies,
                    "extracted_summary": extracted_summary,
                    "pipeline_step":     "done",
                    "processed_at":      now,
                    "updated_at":        now,
                }}
            )
            print(f"[update_status] groupe {group_id} finalisé → {group_state} (manquants: {missing_types or 'aucun'})")
        else:
            print(f"[update_status] groupe {group_id} : {terminal}/{total} fichiers traités, en attente")

    client.close()

    print(f"[update_status] document={document_id} group={group_id} → {final_status}")
