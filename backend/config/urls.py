from django.urls import include, path


urlpatterns = [
    path("api/auth/", include("users.urls")),
    path("api/companies/", include("companies.urls")),
    path("api/", include("documents.urls")),
    path("api/suppliers/", include("suppliers.urls")),
]
