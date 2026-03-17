from django.urls import path

from .views import CompanyDetailView, CompanyListCreateView


urlpatterns = [
    path("", CompanyListCreateView.as_view(), name="company-list-create"),
    path("<str:company_id>/", CompanyDetailView.as_view(), name="company-detail"),
]
