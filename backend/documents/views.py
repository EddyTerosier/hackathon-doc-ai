import os
import uuid
from datetime import datetime, timezone

import requests as http_requests
from bson import ObjectId
from django.conf import settings
from rest_framework import permissions, status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import DocumentFile, DocumentGroup
from .serializers import (
    DocumentFileSerializer,
    DocumentGroupSerializer,
    DocumentUploadSerializer,
)


AIRFLOW_URL = os.getenv("AIRFLOW_URL", "http://airflow:8080")
AIRFLOW_USER = os.getenv("AIRFLOW_USER", "admin")
AIRFLOW_PASSWORD = os.getenv("AIRFLOW_PASSWORD", "admin")


def _get_airflow_token():
    response = http_requests.post(
        f"{AIRFLOW_URL}/auth/token",
        json={"username": AIRFLOW_USER, "password": AIRFLOW_PASSWORD},
        timeout=10,
    )
    return response.json().get("access_token")


def _trigger_airflow_dag(document_id, group_id, file_path):
    try:
        token = _get_airflow_token()
        http_requests.post(
            f"{AIRFLOW_URL}/api/v2/dags/document_pipeline/dagRuns",
            json={
                "logical_date": datetime.now(timezone.utc).isoformat(),
                "conf": {
                    "file_path": file_path,
                    "document_id": document_id,
                    "group_id": group_id,
                },
            },
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except Exception as e:
        print(f"[airflow] Impossible de déclencher le DAG : {e}")


def _get_object_or_404(model_class, object_id):
    if not ObjectId.is_valid(object_id):
        return None
    return model_class.objects(id=ObjectId(object_id)).first()


class DocumentGroupListCreateView(APIView):
    def get(self, request):
        groups = DocumentGroup.objects.order_by("-created_at")
        return Response(DocumentGroupSerializer(groups, many=True).data)

    def post(self, request):
        serializer = DocumentGroupSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        group = serializer.save(created_by=request.user)
        return Response(DocumentGroupSerializer(group).data, status=status.HTTP_201_CREATED)


class DocumentGroupDetailView(APIView):
    def get_object(self, group_id):
        return _get_object_or_404(DocumentGroup, group_id)

    def get(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return Response(
                {"detail": "Document group not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(DocumentGroupSerializer(group).data)

    def patch(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return Response(
                {"detail": "Document group not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DocumentGroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, group_id):
        group = self.get_object(group_id)
        if not group:
            return Response(
                {"detail": "Document group not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class GroupDocumentListCreateView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def get_group(self, group_id):
        return _get_object_or_404(DocumentGroup, group_id)

    def get(self, request, group_id):
        group = self.get_group(group_id)
        if not group:
            return Response(
                {"detail": "Document group not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        documents = DocumentFile.objects(group=group).order_by("-created_at")
        return Response(DocumentFileSerializer(documents, many=True).data)

    def post(self, request, group_id):
        group = self.get_group(group_id)
        if not group:
            return Response(
                {"detail": "Document group not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = DocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        uploaded_file = serializer.validated_data["file"]
        file_extension = os.path.splitext(uploaded_file.name)[1].lower().lstrip(".")
        stored_name = f"{uuid.uuid4()}.{file_extension}"
        group_directory = os.path.join(settings.MEDIA_ROOT, "raw", str(group.id))
        os.makedirs(group_directory, exist_ok=True)
        destination = os.path.join(group_directory, stored_name)

        with open(destination, "wb+") as output_file:
            for chunk in uploaded_file.chunks():
                output_file.write(chunk)

        document = DocumentFile(
            group=group,
            original_name=uploaded_file.name,
            stored_name=stored_name,
            file_path=destination,
            file_type=file_extension,
            mime_type=uploaded_file.content_type or f"application/{file_extension}",
        )
        document.save()

        # Déclenche le DAG Airflow
        _trigger_airflow_dag(str(document.id), str(group.id), destination)

        return Response(
            DocumentFileSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(APIView):
    def get_object(self, document_id):
        return _get_object_or_404(DocumentFile, document_id)

    def get(self, request, document_id):
        document = self.get_object(document_id)
        if not document:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)
        return Response(DocumentFileSerializer(document).data)

    def delete(self, request, document_id):
        document = self.get_object(document_id)
        if not document:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
