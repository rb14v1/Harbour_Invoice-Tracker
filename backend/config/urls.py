from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.auth_urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/clients/", include("apps.clients.urls")),
    path("api/invoices/", include("apps.invoices.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
]
