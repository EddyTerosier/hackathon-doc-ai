import datetime
import os

from bson import ObjectId
from rest_framework import serializers

from companies.models import Company
from suppliers.models import Supplier

from .models import DocumentFile, DocumentGroup, PipelineEvent


class DocumentFileSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    group_id = serializers.CharField(source="group.id", read_only=True)
    original_name = serializers.CharField(read_only=True)
    stored_name = serializers.CharField(read_only=True)
    file_path = serializers.CharField(read_only=True)
    file_type = serializers.CharField(read_only=True)
    mime_type = serializers.CharField(read_only=True)
    document_type = serializers.CharField(read_only=True)
    analysis_status = serializers.CharField(read_only=True)
    ocr_text = serializers.CharField(read_only=True)
    extracted_data = serializers.DictField(read_only=True)
    anomalies = serializers.ListField(child=serializers.CharField(), read_only=True)
    confidence_score = serializers.FloatField(read_only=True)
    needs_manual_review = serializers.BooleanField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "group_id": str(instance.group.id),
            "original_name": instance.original_name,
            "stored_name": instance.stored_name,
            "file_path": instance.file_path,
            "file_type": instance.file_type,
            "mime_type": instance.mime_type,
            "document_type": instance.document_type,
            "analysis_status": instance.analysis_status,
            "ocr_text": instance.ocr_text or "",
            "extracted_data": instance.extracted_data or {},
            "anomalies": instance.anomalies or [],
            "confidence_score": instance.confidence_score,
            "needs_manual_review": instance.needs_manual_review,
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }


class DocumentUploadSerializer(serializers.Serializer):
    file = serializers.FileField()

    def validate_file(self, value):
        extension = os.path.splitext(value.name)[1].lower().lstrip(".")
        allowed_types = set(DocumentFile.TYPE_CHOICES)
        if extension not in allowed_types:
            raise serializers.ValidationError(
                "Only pdf, png, jpg and jpeg files are allowed."
            )
        return value


class DocumentGroupSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=DocumentGroup.STATUS_CHOICES,
        required=False,
        default=DocumentGroup.STATUS_PROCESSING,
    )
    pipeline_step = serializers.CharField(
        required=False,
        allow_blank=True,
        default="ocr",
    )
    error = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    validation_result = serializers.ChoiceField(
        choices=DocumentGroup.VALIDATION_RESULT_CHOICES,
        required=False,
        default=DocumentGroup.VALIDATION_PENDING,
    )
    fraud_flags = serializers.ListField(
        child=serializers.CharField(),
        required=False,
    )
    state = serializers.ChoiceField(
        choices=DocumentGroup.STATE_CHOICES, required=False, default=DocumentGroup.STATE_PENDING
    )
    company_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    supplier_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    created_by_id = serializers.CharField(read_only=True)
    extracted_summary = serializers.DictField(required=False)
    anomalies = serializers.ListField(
        child=serializers.CharField(), required=False
    )
    compliance_notes = serializers.CharField(required=False, allow_blank=True)
    non_compliance_reason = serializers.CharField(required=False, allow_blank=True)
    processing_started_at = serializers.DateTimeField(required=False, allow_null=True)
    processed_at = serializers.DateTimeField(required=False, allow_null=True)
    documents = serializers.SerializerMethodField(read_only=True)

    def get_documents(self, instance):
        documents = DocumentFile.objects(group=instance).order_by("-created_at")
        return DocumentFileSerializer(documents, many=True).data

    def _get_optional_reference(self, model_class, value, field_name):
        if value in (None, ""):
            return None
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError({field_name: "Invalid id."})
        instance = model_class.objects(id=ObjectId(value)).first()
        if not instance:
            raise serializers.ValidationError({field_name: "Object not found."})
        return instance

    def validate(self, attrs):
        if "company_id" in self.initial_data:
            attrs["company"] = self._get_optional_reference(
                Company, attrs.pop("company_id", None), "company_id"
            )
        if "supplier_id" in self.initial_data:
            attrs["supplier"] = self._get_optional_reference(
                Supplier, attrs.pop("supplier_id", None), "supplier_id"
            )

        state = attrs.get("state", getattr(self.instance, "state", None))
        non_compliance_reason = attrs.get(
            "non_compliance_reason",
            getattr(self.instance, "non_compliance_reason", ""),
        )
        if state == DocumentGroup.STATE_NON_COMPLIANT and not non_compliance_reason:
            raise serializers.ValidationError(
                {
                    "non_compliance_reason": (
                        "This field is required when state is non_compliant."
                    )
                }
            )
        return attrs

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "name": instance.name,
            "description": instance.description or "",
            "status": instance.status,
            "pipeline_step": instance.pipeline_step,
            "error": instance.error,
            "validation_result": instance.validation_result,
            "fraud_flags": instance.fraud_flags or [],
            "state": instance.state,
            "company_id": str(instance.company.id) if instance.company else None,
            "supplier_id": str(instance.supplier.id) if instance.supplier else None,
            "created_by_id": str(instance.created_by.id) if instance.created_by else None,
            "extracted_summary": instance.extracted_summary or {},
            "anomalies": instance.anomalies or [],
            "compliance_notes": instance.compliance_notes or "",
            "non_compliance_reason": instance.non_compliance_reason or "",
            "processing_started_at": (
                instance.processing_started_at.isoformat()
                if instance.processing_started_at
                else None
            ),
            "processed_at": (
                instance.processed_at.isoformat() if instance.processed_at else None
            ),
            "documents": self.get_documents(instance),
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }

    def create(self, validated_data):
        group = DocumentGroup(**validated_data)
        group.save()
        return group

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance


class PipelineEventSerializer(serializers.Serializer):
    id = serializers.CharField(read_only=True)
    type = serializers.ChoiceField(choices=PipelineEvent.TYPE_CHOICES, required=False)
    dag_id = serializers.CharField(max_length=255)
    run_id = serializers.CharField(max_length=255)
    pipeline_step = serializers.CharField(max_length=100)
    document_id = serializers.CharField(max_length=24)
    group_id = serializers.CharField(max_length=24)
    status = serializers.ChoiceField(choices=PipelineEvent.STATUS_CHOICES, required=False)
    error = serializers.CharField(required=False, allow_blank=True)
    traceback = serializers.CharField(required=False, allow_blank=True)
    occurred_at = serializers.DateTimeField(required=False)

    def validate_document_id(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError("Invalid id.")
        return value

    def validate_group_id(self, value):
        if not ObjectId.is_valid(value):
            raise serializers.ValidationError("Invalid id.")
        return value

    def validate(self, attrs):
        status_value = attrs.get("status", getattr(self.instance, "status", PipelineEvent.STATUS_PENDING))
        error = attrs.get("error", getattr(self.instance, "error", ""))
        if status_value == PipelineEvent.STATUS_ERROR and not error:
            raise serializers.ValidationError(
                {"error": "This field is required when status is error."}
            )
        return attrs

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "type": instance.type,
            "dag_id": instance.dag_id,
            "run_id": instance.run_id,
            "pipeline_step": instance.pipeline_step,
            "document_id": instance.document_id,
            "group_id": instance.group_id,
            "status": instance.status,
            "error": instance.error or "",
            "traceback": instance.traceback or "",
            "occurred_at": instance.occurred_at.isoformat(),
            "created_at": instance.created_at.isoformat(),
            "updated_at": instance.updated_at.isoformat(),
        }

    def create(self, validated_data):
        event = PipelineEvent(
            type=validated_data.get("type", PipelineEvent.TYPE_TECHNICAL),
            status=validated_data.get("status", PipelineEvent.STATUS_PENDING),
            occurred_at=validated_data.get("occurred_at"),
            **{
                key: value
                for key, value in validated_data.items()
                if key not in {"type", "status", "occurred_at"}
            },
        )
        if event.occurred_at is None:
            event.occurred_at = datetime.datetime.utcnow()
        event.save()
        return event

    def update(self, instance, validated_data):
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        return instance
