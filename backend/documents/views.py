import os
import uuid
from datetime import datetime

import requests
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

        # Déclenche le pipeline Airflow avec le fichier uploadé
        airflow_url = os.getenv("AIRFLOW_URL", "http://airflow:8080")
        airflow_user = os.getenv("AIRFLOW_USER", "admin")
        airflow_password = os.getenv("AIRFLOW_PASSWORD", "admin")
        try:
            requests.post(
                f"{airflow_url}/api/v2/dags/document_pipeline/dagRuns",
                json={
                    "logical_date": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "conf": {
                        "file_path": destination,
                        "document_id": str(document.id),
                        "group_id": str(group.id),
                        "user_id": str(request.user.id) if request.user else None,
                    }
                },
                auth=(airflow_user, airflow_password),
                timeout=5,
            )
        except requests.exceptions.RequestException:
            pass  # Ne pas bloquer l'upload si Airflow est indisponible

        return Response(
            DocumentFileSerializer(document).data,
            status=status.HTTP_201_CREATED,
        )


class DocumentDetailView(APIView):
    def get_object(self, document_id):
        return _get_object_or_404(DocumentFile, document_id)

    def delete(self, request, document_id):
        document = self.get_object(document_id)
        if not document:
            return Response({"detail": "Document not found."}, status=status.HTTP_404_NOT_FOUND)

        if os.path.exists(document.file_path):
            os.remove(document.file_path)
        document.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
