import os
import shutil

from django.conf import settings
from django.core.management.base import BaseCommand

from companies.models import Company
from suppliers.models import Supplier
from users.models import User

from documents.models import DocumentFile, DocumentGroup


DATASET_DIR = os.path.abspath(
    os.path.join(settings.BASE_DIR, "..", "dataset")
)


COMPANIES = [
    {
        "name": "Alpha Conseil",
        "registration_number": "ENT-001",
        "siret": "12345678901234",
        "vat_number": "FR12123456789",
        "email": "contact@alphaconseil.test",
    },
    {
        "name": "Beta Industrie",
        "registration_number": "ENT-002",
        "siret": "22345678901234",
        "vat_number": "FR98223456789",
        "email": "contact@betaindustrie.test",
    },
]

SUPPLIERS = [
    {
        "name": "Alpha Conseil",
        "registration_number": "SUP-001",
        "siret": "12345678901234",
        "vat_number": "FR12123456789",
        "iban": "FR7612345678901234567890123",
        "bic": "AGRIFRPP",
        "urssaf_expiration_date": "2026-06-30",
        "email": "support@alphaconseil.test",
    },
    {
        "name": "Gamma Services",
        "registration_number": "SUP-002",
        "siret": "99999999999999",
        "vat_number": "FR88999999999",
        "iban": "FR7611111111111111111111111",
        "bic": "PSSTFRPP",
        "urssaf_expiration_date": "2026-01-15",
        "email": "support@gammaservices.test",
    },
]

GROUPS = [
    {
        "name": "Alpha Conseil compliant batch",
        "description": "Supplier batch with invoice, URSSAF and bank details.",
        "state": DocumentGroup.STATE_COMPLIANT,
        "company_name": "Alpha Conseil",
        "supplier_name": "Alpha Conseil",
        "extracted_summary": {
            "supplier_name": "Alpha Conseil",
            "siret": "12345678901234",
            "vat_number": "FR12123456789",
            "iban": "FR7612345678901234567890123",
            "bic": "AGRIFRPP",
            "invoice_date": "2026-03-10",
            "amount_excl_tax": 1200.50,
            "amount_incl_tax": 1440.60,
            "urssaf_expiration_date": "2026-06-30",
        },
        "anomalies": [],
        "compliance_notes": "All extracted fields are consistent across the batch.",
        "non_compliance_reason": "",
        "documents": [
            {
                "original_name": "FAC_SUP001_conforme.pdf",
                "source_path": os.path.join("raw", "facture", "FAC_SUP001_conforme.pdf"),
                "file_type": "pdf",
                "mime_type": "application/pdf",
                "document_type": DocumentFile.DOCUMENT_TYPE_INVOICE,
                "analysis_status": DocumentFile.ANALYSIS_ANALYZED,
                "ocr_text": "Invoice Alpha Conseil 12345678901234 FR12123456789 1200.50 1440.60",
                "extracted_data": {
                    "supplier_name": "Alpha Conseil",
                    "siret": "12345678901234",
                    "vat_number": "FR12123456789",
                    "issue_date": "2026-03-10",
                    "amount_excl_tax": 1200.50,
                    "amount_incl_tax": 1440.60,
                },
                "anomalies": [],
                "confidence_score": 0.98,
                "needs_manual_review": False,
            },
            {
                "original_name": "URS_SUP001_conforme.pdf",
                "source_path": os.path.join("raw", "urssaf", "URS_SUP001_conforme.pdf"),
                "file_type": "pdf",
                "mime_type": "application/pdf",
                "document_type": DocumentFile.DOCUMENT_TYPE_URSSAF_CERTIFICATE,
                "analysis_status": DocumentFile.ANALYSIS_ANALYZED,
                "ocr_text": "URSSAF Alpha Conseil 12345678901234 valid until 2026-06-30",
                "extracted_data": {
                    "company_name": "Alpha Conseil",
                    "siret": "12345678901234",
                    "expiration_date": "2026-06-30",
                },
                "anomalies": [],
                "confidence_score": 0.97,
                "needs_manual_review": False,
            },
            {
                "original_name": "RIB_SUP001_conforme.pdf",
                "source_path": os.path.join("raw", "rib", "RIB_SUP001_conforme.pdf"),
                "file_type": "pdf",
                "mime_type": "application/pdf",
                "document_type": DocumentFile.DOCUMENT_TYPE_BANK_DETAILS,
                "analysis_status": DocumentFile.ANALYSIS_ANALYZED,
                "ocr_text": "IBAN FR7612345678901234567890123 BIC AGRIFRPP",
                "extracted_data": {
                    "account_holder": "Alpha Conseil",
                    "iban": "FR7612345678901234567890123",
                    "bic": "AGRIFRPP",
                },
                "anomalies": [],
                "confidence_score": 0.95,
                "needs_manual_review": False,
            },
        ],
    },
    {
        "name": "Gamma Services non compliant batch",
        "description": "Batch with an inconsistent SIRET and expired URSSAF certificate.",
        "state": DocumentGroup.STATE_NON_COMPLIANT,
        "company_name": "Beta Industrie",
        "supplier_name": "Gamma Services",
        "extracted_summary": {
            "supplier_name": "Gamma Services",
            "invoice_siret": "23456789012345",
            "urssaf_siret": "99999999999999",
            "urssaf_expiration_date": "2026-01-15",
        },
        "anomalies": [
            "SIRET mismatch between invoice and URSSAF certificate.",
            "URSSAF certificate is expired.",
        ],
        "compliance_notes": "Manual correction required before onboarding.",
        "non_compliance_reason": "SIRET mismatch between invoice and URSSAF certificate.",
        "documents": [
            {
                "original_name": "FAC_SUP002_siret_incoherent.pdf",
                "source_path": os.path.join("raw", "facture", "FAC_SUP002_siret_incoherent.pdf"),
                "file_type": "pdf",
                "mime_type": "application/pdf",
                "document_type": DocumentFile.DOCUMENT_TYPE_INVOICE,
                "analysis_status": DocumentFile.ANALYSIS_ANALYZED,
                "ocr_text": "Invoice Gamma Services 23456789012345",
                "extracted_data": {
                    "supplier_name": "Gamma Services",
                    "siret": "23456789012345",
                },
                "anomalies": ["Invoice SIRET differs from URSSAF certificate."],
                "confidence_score": 0.91,
                "needs_manual_review": True,
            },
            {
                "original_name": "URS_SUP003_attestation_expired.pdf",
                "source_path": os.path.join("raw", "urssaf", "URS_SUP003_attestation_expired.pdf"),
                "file_type": "pdf",
                "mime_type": "application/pdf",
                "document_type": DocumentFile.DOCUMENT_TYPE_URSSAF_CERTIFICATE,
                "analysis_status": DocumentFile.ANALYSIS_ANALYZED,
                "ocr_text": "URSSAF Gamma Services 99999999999999 expired 2026-01-15",
                "extracted_data": {
                    "company_name": "Gamma Services",
                    "siret": "99999999999999",
                    "expiration_date": "2026-01-15",
                },
                "anomalies": ["URSSAF certificate expired."],
                "confidence_score": 0.93,
                "needs_manual_review": True,
            },
        ],
    },
]


class Command(BaseCommand):
    help = (
        "Insert demo companies, suppliers, document groups and document files "
        "into MongoDB without creating duplicates."
    )

    def handle(self, *args, **options):
        companies = self._seed_companies()
        suppliers = self._seed_suppliers()
        created_by = self._get_seed_owner()
        self._seed_groups(companies, suppliers, created_by)
        self.stdout.write(self.style.SUCCESS("Business seed completed successfully."))

    def _seed_companies(self):
        companies = {}
        for data in COMPANIES:
            company = Company.objects(name=data["name"]).first()
            if company is None:
                company = Company(**data)
                company.save()
                self.stdout.write(self.style.SUCCESS(f"Company created: {company.name}"))
            else:
                for field, value in data.items():
                    setattr(company, field, value)
                company.save()
                self.stdout.write(self.style.WARNING(f"Company updated: {company.name}"))
            companies[company.name] = company
        return companies

    def _seed_suppliers(self):
        suppliers = {}
        for data in SUPPLIERS:
            supplier = Supplier.objects(name=data["name"]).first()
            if supplier is None:
                supplier = Supplier(**data)
                supplier.save()
                self.stdout.write(self.style.SUCCESS(f"Supplier created: {supplier.name}"))
            else:
                for field, value in data.items():
                    setattr(supplier, field, value)
                supplier.save()
                self.stdout.write(self.style.WARNING(f"Supplier updated: {supplier.name}"))
            suppliers[supplier.name] = supplier
        return suppliers

    def _get_seed_owner(self):
        return (
            User.objects(email="admin1@hackathon.local").first()
            or User.objects(role=User.ROLE_ACCOUNTANT).first()
        )

    def _seed_groups(self, companies, suppliers, created_by):
        for data in GROUPS:
            group = DocumentGroup.objects(name=data["name"]).first()
            group_fields = {
                "name": data["name"],
                "description": data["description"],
                "state": data["state"],
                "company": companies.get(data["company_name"]),
                "supplier": suppliers.get(data["supplier_name"]),
                "created_by": created_by,
                "extracted_summary": data["extracted_summary"],
                "anomalies": data["anomalies"],
                "compliance_notes": data["compliance_notes"],
                "non_compliance_reason": data["non_compliance_reason"],
            }

            if group is None:
                group = DocumentGroup(**group_fields)
                group.save()
                self.stdout.write(self.style.SUCCESS(f"Document group created: {group.name}"))
            else:
                for field, value in group_fields.items():
                    setattr(group, field, value)
                group.save()
                self.stdout.write(self.style.WARNING(f"Document group updated: {group.name}"))

            self._seed_documents_for_group(group, data["documents"])

    def _seed_documents_for_group(self, group, documents):
        group_directory = os.path.join(settings.MEDIA_ROOT, "documents", str(group.id))
        os.makedirs(group_directory, exist_ok=True)
        expected_original_names = {document["original_name"] for document in documents}

        for stale_document in DocumentFile.objects(group=group):
            if stale_document.original_name not in expected_original_names:
                if os.path.exists(stale_document.file_path):
                    os.remove(stale_document.file_path)
                stale_name = stale_document.original_name
                stale_document.delete()
                self.stdout.write(
                    self.style.WARNING(
                        f"Document removed: {group.name} / {stale_name}"
                    )
                )

        for document_data in documents:
            stored_name = document_data["original_name"]
            file_path = os.path.join(group_directory, stored_name)
            source_path = os.path.join(DATASET_DIR, document_data["source_path"])

            if not os.path.exists(source_path):
                raise FileNotFoundError(
                    f"Dataset file not found for seed: {source_path}"
                )

            shutil.copy2(source_path, file_path)

            document = DocumentFile.objects(
                group=group, original_name=document_data["original_name"]
            ).first()

            payload = {
                "group": group,
                "original_name": document_data["original_name"],
                "stored_name": stored_name,
                "file_path": file_path,
                "file_type": document_data["file_type"],
                "mime_type": document_data["mime_type"],
                "document_type": document_data["document_type"],
                "analysis_status": document_data["analysis_status"],
                "ocr_text": document_data["ocr_text"],
                "extracted_data": document_data["extracted_data"],
                "anomalies": document_data["anomalies"],
                "confidence_score": document_data["confidence_score"],
                "needs_manual_review": document_data["needs_manual_review"],
            }

            if document is None:
                document = DocumentFile(**payload)
                document.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Document created: {group.name} / {document.original_name}"
                    )
                )
            else:
                for field, value in payload.items():
                    setattr(document, field, value)
                document.save()
                self.stdout.write(
                    self.style.WARNING(
                        f"Document updated: {group.name} / {document.original_name}"
                )
                )
