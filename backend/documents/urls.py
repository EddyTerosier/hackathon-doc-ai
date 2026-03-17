from django.urls import path

from .views import (
    DocumentDetailView,
    DocumentGroupDetailView,
    DocumentGroupListCreateView,
    GroupDocumentListCreateView,
)


urlpatterns = [
    path(
        "document-groups/",
        DocumentGroupListCreateView.as_view(),
        name="document-group-list-create",
    ),
    path(
        "document-groups/<str:group_id>/",
        DocumentGroupDetailView.as_view(),
        name="document-group-detail",
    ),
    path(
        "document-groups/<str:group_id>/documents/",
        GroupDocumentListCreateView.as_view(),
        name="group-document-list-create",
    ),
    path("documents/<str:document_id>/", DocumentDetailView.as_view(), name="document-detail"),
]
