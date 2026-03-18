import io
import os
import shutil

from django.conf import settings
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from companies.models import Company
from suppliers.models import Supplier
from users.models import User
from users.mongo import reconnect_mongo_for_tests

from .models import DocumentFile, DocumentGroup


DATASET_DIR = os.path.abspath(
    os.path.join(settings.BASE_DIR, "..", "dataset")
)


class DocumentDomainTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        reconnect_mongo_for_tests()

    def setUp(self):
        reconnect_mongo_for_tests()
        User.drop_collection()
        Company.drop_collection()
        Supplier.drop_collection()
        DocumentGroup.drop_collection()
        DocumentFile.drop_collection()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

        self.client = APIClient()
        self.user = User(
            last_name="Admin",
            first_name="Alice",
            role=User.ROLE_ACCOUNTANT,
            email="admin@example.com",
        )
        self.user.set_password("Admin12345!")
        self.user.save()

        login_response = self.client.post(
            "/api/auth/login/",
            {"email": "admin@example.com", "password": "Admin12345!"},
            format="json",
        )
        self.access_token = login_response.data["tokens"]["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.access_token}")

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_create_company(self):
        response = self.client.post(
            "/api/companies/",
            {
                "name": "Acme Corp",
                "registration_number": "123456789",
                "siret": "12345678901234",
                "vat_number": "FR12123456789",
                "email": "contact@acme.test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Acme Corp")
        self.assertEqual(response.data["siret"], "12345678901234")
        self.assertEqual(Company.objects.count(), 1)

    def test_create_supplier(self):
        response = self.client.post(
            "/api/suppliers/",
            {
                "name": "Alpha Supply",
                "registration_number": "SUP-001",
                "siret": "12345678901234",
                "vat_number": "FR12123456789",
                "iban": "FR7612345678901234567890123",
                "bic": "AGRIFRPP",
                "urssaf_expiration_date": "2026-06-30",
                "email": "hello@alpha.test",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["name"], "Alpha Supply")
        self.assertEqual(response.data["iban"], "FR7612345678901234567890123")
        self.assertEqual(Supplier.objects.count(), 1)

    def test_create_document_group_without_links(self):
        response = self.client.post(
            "/api/document-groups/",
            {
                "name": "Unlinked group",
                "description": "No company and no supplier",
                "state": "pending",
                "anomalies": ["Potential OCR quality issue"],
                "extracted_summary": {"document_count": 0},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["company_id"])
        self.assertIsNone(response.data["supplier_id"])
        self.assertEqual(response.data["status"], "processing")
        self.assertEqual(response.data["pipeline_step"], "ocr")
        self.assertIsNone(response.data["error"])
        self.assertEqual(response.data["validation_result"], "pending")
        self.assertEqual(response.data["fraud_flags"], [])
        self.assertEqual(response.data["state"], "pending")
        self.assertEqual(response.data["anomalies"], ["Potential OCR quality issue"])
        self.assertEqual(DocumentGroup.objects.count(), 1)

    def test_create_document_group_with_company_and_supplier(self):
        company = Company(name="Acme Corp", registration_number="123").save()
        supplier = Supplier(name="Alpha Supply", registration_number="SUP-001").save()

        response = self.client.post(
            "/api/document-groups/",
            {
                "name": "Supplier onboarding",
                "status": "processing",
                "pipeline_step": "ocr",
                "state": "processing",
                "company_id": str(company.id),
                "supplier_id": str(supplier.id),
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["company_id"], str(company.id))
        self.assertEqual(response.data["supplier_id"], str(supplier.id))
        self.assertEqual(response.data["status"], "processing")
        self.assertEqual(response.data["pipeline_step"], "ocr")
        self.assertEqual(response.data["validation_result"], "pending")
        self.assertEqual(response.data["fraud_flags"], [])

    def test_patch_document_group_monitoring_fields(self):
        group = DocumentGroup(name="Invoices", created_by=self.user).save()

        response = self.client.patch(
            f"/api/document-groups/{group.id}/",
            {
                "status": "failed",
                "pipeline_step": "business_rules",
                "error": "Missing mandatory supplier VAT number.",
                "validation_result": "invalid",
                "fraud_flags": ["siret_mismatch", "date_expired"],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["status"], "failed")
        self.assertEqual(response.data["pipeline_step"], "business_rules")
        self.assertEqual(response.data["error"], "Missing mandatory supplier VAT number.")
        self.assertEqual(response.data["validation_result"], "invalid")
        self.assertEqual(response.data["fraud_flags"], ["siret_mismatch", "date_expired"])

    def test_non_compliant_group_requires_reason(self):
        response = self.client.post(
            "/api/document-groups/",
            {
                "name": "Invalid supplier file",
                "state": "non_compliant",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("non_compliance_reason", response.data)

    def test_non_compliant_group_accepts_reason(self):
        response = self.client.post(
            "/api/document-groups/",
            {
                "name": "Invalid supplier file",
                "state": "non_compliant",
                "non_compliance_reason": "SIRET mismatch between invoice and URSSAF certificate.",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(
            response.data["non_compliance_reason"],
            "SIRET mismatch between invoice and URSSAF certificate.",
        )

    def test_upload_pdf_document_to_group(self):
        group = DocumentGroup(name="Invoices", created_by=self.user).save()
        file = SimpleUploadedFile(
            "invoice.pdf",
            b"%PDF-1.4 fake pdf content",
            content_type="application/pdf",
        )

        response = self.client.post(
            f"/api/document-groups/{group.id}/documents/",
            {"file": file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["file_type"], "pdf")
        self.assertEqual(response.data["document_type"], "unknown")
        # L'OCR est déclenché immédiatement après l'upload.
        # Selon l'environnement, Tesseract/Poppler peut être absent, ce qui donne le statut "failed".
        self.assertIn(response.data["analysis_status"], ["pending", "failed", "analyzed"])
        self.assertTrue(os.path.exists(response.data["file_path"]))
        self.assertEqual(DocumentFile.objects.count(), 1)

    def test_upload_png_document_to_group(self):
        group = DocumentGroup(name="Receipts", created_by=self.user).save()
        file = SimpleUploadedFile(
            "receipt.png",
            b"\x89PNG\r\n\x1a\nfake png content",
            content_type="image/png",
        )

        response = self.client.post(
            f"/api/document-groups/{group.id}/documents/",
            {"file": file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["file_type"], "png")

    def test_reject_unsupported_file_type(self):
        group = DocumentGroup(name="Invalid", created_by=self.user).save()
        file = SimpleUploadedFile(
            "notes.txt",
            b"plain text is not allowed",
            content_type="text/plain",
        )

        response = self.client.post(
            f"/api/document-groups/{group.id}/documents/",
            {"file": file},
            format="multipart",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("file", response.data)


class SeedBusinessDataCommandTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        reconnect_mongo_for_tests()

    def setUp(self):
        reconnect_mongo_for_tests()
        User.drop_collection()
        Company.drop_collection()
        Supplier.drop_collection()
        DocumentGroup.drop_collection()
        DocumentFile.drop_collection()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def test_seed_business_data_creates_domain_objects(self):
        owner = User(
            last_name="Martin",
            first_name="Alice",
            role=User.ROLE_ACCOUNTANT,
            email="admin1@hackathon.local",
        )
        owner.set_password("Admin12345!")
        owner.save()

        call_command("seed_business_data", stdout=io.StringIO())

        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(Supplier.objects.count(), 2)
        self.assertEqual(DocumentGroup.objects.count(), 2)
        self.assertEqual(DocumentFile.objects.count(), 5)
        non_compliant_group = DocumentGroup.objects(
            name="Gamma Services non compliant batch"
        ).first()
        self.assertEqual(non_compliant_group.status, "failed")
        self.assertEqual(non_compliant_group.pipeline_step, "compliance_checks")
        self.assertEqual(
            non_compliant_group.error,
            "Business validation failed: SIRET mismatch between invoice and URSSAF certificate.",
        )
        self.assertEqual(non_compliant_group.validation_result, "invalid")
        self.assertEqual(
            non_compliant_group.fraud_flags,
            ["siret_mismatch", "date_expired"],
        )
        self.assertEqual(
            non_compliant_group.non_compliance_reason,
            "SIRET mismatch between invoice and URSSAF certificate.",
        )
        seeded_invoice = DocumentFile.objects(
            original_name="FAC_SUP001_conforme.pdf"
        ).first()
        dataset_invoice = os.path.join(
            DATASET_DIR, "raw", "facture", "FAC_SUP001_conforme.pdf"
        )
        with open(seeded_invoice.file_path, "rb") as seeded_file:
            seeded_bytes = seeded_file.read()
        with open(dataset_invoice, "rb") as dataset_file:
            dataset_bytes = dataset_file.read()
        self.assertEqual(seeded_bytes, dataset_bytes)

    def test_seed_business_data_is_idempotent(self):
        owner = User(
            last_name="Martin",
            first_name="Alice",
            role=User.ROLE_ACCOUNTANT,
            email="admin1@hackathon.local",
        )
        owner.set_password("Admin12345!")
        owner.save()

        call_command("seed_business_data", stdout=io.StringIO())
        call_command("seed_business_data", stdout=io.StringIO())

        self.assertEqual(Company.objects.count(), 2)
        self.assertEqual(Supplier.objects.count(), 2)
        self.assertEqual(DocumentGroup.objects.count(), 2)
        self.assertEqual(DocumentFile.objects.count(), 5)
