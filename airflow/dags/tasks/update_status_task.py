import os
import re
from datetime import datetime, timezone
from pymongo import MongoClient
from bson import ObjectId

MONGO_URI = os.getenv("MONGO_URI", "mongodb://admin:admin123@localhost:27017/?authSource=admin")
DB_NAME = "hackathon_db"


def _extract_labeled_value(text, labels):
    if not text:
        return None

    for label in labels:
        match = re.search(rf"{label}\s*[:\-]\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _infer_supplier_name(doc):
    return _extract_labeled_value(
        doc.get("ocr_text") or "",
        [
            r"Fournisseur",
            r"Entreprise",
            r"Titulaire du compte",
        ],
    )


def _first_or_none(value):
    if isinstance(value, list):
        return value[0] if value else None
    return value


def _upsert_supplier(db, summary, now):
    name = (summary.get("supplier_name") or "").strip() or None
    siret = (summary.get("siret") or "").strip() or None
    vat_number = (summary.get("tva") or "").strip() or None
    iban = (summary.get("iban") or "").strip() or None
    bic = (summary.get("bic") or "").strip() or None
    urssaf_valid_until = (summary.get("urssaf_valid_until") or "").strip() or None

    if not any([name, siret, vat_number, iban]):
        return None

    if not name:
        name = siret or vat_number or iban or "Extracted supplier"

    query = None
    for field, value in (
        ("siret", siret),
        ("vat_number", vat_number),
        ("iban", iban),
        ("name", name),
    ):
        if value:
            query = {field: value}
            break

    if query is None:
        return None

    update_fields = {"updated_at": now}
    if name:
        update_fields["name"] = name
    if siret:
        update_fields["siret"] = siret
    if vat_number:
        update_fields["vat_number"] = vat_number
    if iban:
        update_fields["iban"] = iban
    if bic:
        update_fields["bic"] = bic
    if urssaf_valid_until:
        try:
            update_fields["urssaf_expiration_date"] = datetime.fromisoformat(
                urssaf_valid_until.replace("Z", "+00:00")
            )
        except ValueError:
            pass

    try:
        existing = db.suppliers.find_one(query, {"_id": 1})
        if existing:
            db.suppliers.update_one({"_id": existing["_id"]}, {"$set": update_fields})
            return existing["_id"]

        update_fields["created_at"] = now
        return db.suppliers.insert_one(update_fields).inserted_id
    except Exception as exc:
        print(f"[update_status] supplier upsert skipped: {exc}")
        return None


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
                {
                    "anomalies": 1,
                    "document_type": 1,
                    "analysis_status": 1,
                    "extracted_data": 1,
                    "ocr_text": 1,
                }
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
                    extracted_summary["supplier_name"] = _infer_supplier_name(doc)
                    extracted_summary["siret"]         = _first_or_none(data.get("siret"))
                    extracted_summary["tva"]           = _first_or_none(data.get("tva"))
                    extracted_summary["montant_ht"]    = data.get("montant_ht")
                    extracted_summary["montant_ttc"]   = data.get("montant_ttc")
                    extracted_summary["date_emission"] = _first_or_none(data.get("dates"))
                elif dtype == "bank_details":
                    extracted_summary["supplier_name"] = (
                        extracted_summary.get("supplier_name") or _infer_supplier_name(doc)
                    )
                    extracted_summary["iban"] = _first_or_none(data.get("iban"))
                    extracted_summary["bic"]  = _first_or_none(data.get("bic"))
                elif dtype == "urssaf_certificate":
                    extracted_summary["supplier_name"] = (
                        extracted_summary.get("supplier_name") or _infer_supplier_name(doc)
                    )
                    extracted_summary["urssaf_valid_until"] = _first_or_none(data.get("dates"))

            supplier_id = None
            if group_state == "compliant":
                supplier_id = _upsert_supplier(db, extracted_summary, now)

            group_update = {
                "status":            "completed",
                "state":             group_state,
                "validation_result": "valid" if not all_anomalies else "invalid",
                "anomalies":         all_anomalies,
                "extracted_summary": extracted_summary,
                "pipeline_step":     "done",
                "processed_at":      now,
                "updated_at":        now,
            }
            if supplier_id:
                group_update["supplier"] = supplier_id

            db.document_groups.update_one(
                {"_id": group_oid},
                {"$set": group_update}
            )
            print(f"[update_status] groupe {group_id} finalisé → {group_state} (manquants: {missing_types or 'aucun'})")
        else:
            print(f"[update_status] groupe {group_id} : {terminal}/{total} fichiers traités, en attente")

    client.close()

    print(f"[update_status] document={document_id} group={group_id} → {final_status}")
