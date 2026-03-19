import datetime

from mongoengine import (
    CASCADE,
    BooleanField,
    NULLIFY,
    DateTimeField,
    DictField,
    Document,
    FloatField,
    ListField,
    ReferenceField,
    StringField,
)

from companies.models import Company
from suppliers.models import Supplier
from users.models import User


class TimeStampedDocument(Document):
    created_at = DateTimeField(default=datetime.datetime.utcnow)
    updated_at = DateTimeField(default=datetime.datetime.utcnow)

    meta = {"abstract": True}

    def save(self, *args, **kwargs):
        self.updated_at = datetime.datetime.utcnow()
        return super().save(*args, **kwargs)


class DocumentGroup(TimeStampedDocument):
    STATUS_PENDING = "pending"
    STATUS_PROCESSING = "processing"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = (
        STATUS_PENDING,
        STATUS_PROCESSING,
        STATUS_COMPLETED,
        STATUS_FAILED,
    )

    VALIDATION_PENDING = "pending"
    VALIDATION_VALID = "valid"
    VALIDATION_INVALID = "invalid"
    VALIDATION_REVIEW = "review"
    VALIDATION_RESULT_CHOICES = (
        VALIDATION_PENDING,
        VALIDATION_VALID,
        VALIDATION_INVALID,
        VALIDATION_REVIEW,
    )

    STATE_PENDING = "pending"
    STATE_COMPLETE = "complete"
    STATE_PROCESSING = "processing"
    STATE_NON_COMPLIANT = "non_compliant"
    STATE_COMPLIANT = "compliant"
    STATE_CHOICES = (
        STATE_PENDING,
        STATE_COMPLETE,
        STATE_PROCESSING,
        STATE_NON_COMPLIANT,
        STATE_COMPLIANT,
    )

    name = StringField(required=True, max_length=255)
    description = StringField()
    status = StringField(
        required=True,
        choices=STATUS_CHOICES,
        default=STATUS_PROCESSING,
    )
    pipeline_step = StringField(required=True, max_length=100, default="ocr")
    error = StringField(null=True)
    validation_result = StringField(
        required=True,
        choices=VALIDATION_RESULT_CHOICES,
        default=VALIDATION_PENDING,
    )
    fraud_flags = ListField(StringField(max_length=100), default=list)
    state = StringField(required=True, choices=STATE_CHOICES, default=STATE_PENDING)
    company = ReferenceField(Company, null=True, reverse_delete_rule=NULLIFY)
    supplier = ReferenceField(Supplier, null=True, reverse_delete_rule=NULLIFY)
    created_by = ReferenceField(User, null=True, reverse_delete_rule=NULLIFY)
    extracted_summary = DictField(default=dict)
    anomalies = ListField(StringField(max_length=255), default=list)
    compliance_notes = StringField()
    non_compliance_reason = StringField()
    processing_started_at = DateTimeField()
    processed_at = DateTimeField()

    meta = {
        "collection": "document_groups",
        "indexes": [
            "status",
            "pipeline_step",
            "validation_result",
            "state",
            "company",
            "supplier",
        ],
    }


class DocumentFile(TimeStampedDocument):
    DOCUMENT_TYPE_UNKNOWN = "unknown"
    DOCUMENT_TYPE_INVOICE = "invoice"
    DOCUMENT_TYPE_URSSAF_CERTIFICATE = "urssaf_certificate"
    DOCUMENT_TYPE_BANK_DETAILS = "bank_details"
    DOCUMENT_TYPE_CHOICES = (
        DOCUMENT_TYPE_UNKNOWN,
        DOCUMENT_TYPE_INVOICE,
        DOCUMENT_TYPE_URSSAF_CERTIFICATE,
        DOCUMENT_TYPE_BANK_DETAILS,
    )

    ANALYSIS_PENDING = "pending"
    ANALYSIS_PROCESSING = "processing"
    ANALYSIS_ANALYZED = "analyzed"
    ANALYSIS_FAILED = "failed"
    ANALYSIS_STATUS_CHOICES = (
        ANALYSIS_PENDING,
        ANALYSIS_PROCESSING,
        ANALYSIS_ANALYZED,
        ANALYSIS_FAILED,
    )

    TYPE_PDF = "pdf"
    TYPE_PNG = "png"
    TYPE_JPG = "jpg"
    TYPE_JPEG = "jpeg"
    TYPE_CHOICES = (TYPE_PDF, TYPE_PNG, TYPE_JPG, TYPE_JPEG)

    group = ReferenceField(DocumentGroup, required=True, reverse_delete_rule=CASCADE)
    original_name = StringField(required=True, max_length=255)
    stored_name = StringField(required=True, max_length=255)
    file_path = StringField(required=True)
    file_type = StringField(required=True, choices=TYPE_CHOICES)
    mime_type = StringField(required=True, max_length=100)
    document_type = StringField(
        required=True,
        choices=DOCUMENT_TYPE_CHOICES,
        default=DOCUMENT_TYPE_UNKNOWN,
    )
    analysis_status = StringField(
        required=True,
        choices=ANALYSIS_STATUS_CHOICES,
        default=ANALYSIS_PENDING,
    )
    ocr_text = StringField()
    extracted_data = DictField(default=dict)
    anomalies = ListField(StringField(max_length=255), default=list)
    confidence_score = FloatField()
    needs_manual_review = BooleanField(default=False)

    meta = {
        "collection": "documents",
        "indexes": ["group", "file_type", "document_type", "analysis_status"],
    }


class PipelineEvent(TimeStampedDocument):
    TYPE_TECHNICAL = "technical"
    TYPE_BUSINESS = "business"
    TYPE_CHOICES = (
        TYPE_TECHNICAL,
        TYPE_BUSINESS,
    )

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_ERROR = "error"
    STATUS_CHOICES = (
        STATUS_PENDING,
        STATUS_RUNNING,
        STATUS_SUCCESS,
        STATUS_ERROR,
    )

    type = StringField(required=True, choices=TYPE_CHOICES, default=TYPE_TECHNICAL)
    dag_id = StringField(required=True, max_length=255)
    run_id = StringField(required=True, max_length=255)
    pipeline_step = StringField(required=True, max_length=100)
    document_id = StringField(required=True, max_length=24)
    group_id = StringField(required=True, max_length=24)
    status = StringField(required=True, choices=STATUS_CHOICES, default=STATUS_PENDING)
    error = StringField()
    traceback = StringField()
    occurred_at = DateTimeField(required=True, default=datetime.datetime.utcnow)

    meta = {
        "collection": "pipeline_errors",
        "indexes": [
            "type",
            "dag_id",
            "run_id",
            "pipeline_step",
            "document_id",
            "group_id",
            "status",
            "occurred_at",
        ],
    }
