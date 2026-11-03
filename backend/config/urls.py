from django.contrib import admin
from django.urls import include, path
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def healthz(request):
    """Unauthenticated liveness probe for orchestrators and load balancers."""
    return Response({"status": "ok"})


urlpatterns = [
    path("healthz", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("api/auth/", include("apps.accounts.auth_urls")),
    path("api/", include("apps.accounts.urls")),
    path("api/clients/", include("apps.clients.urls")),
    path("api/invoices/", include("apps.invoices.urls")),
    path("api/dashboard/", include("apps.dashboard.urls")),
]
