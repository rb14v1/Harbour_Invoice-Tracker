from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.invoices.views import (
    InvoiceLineItemDetailView,
    InvoiceLineItemListCreateView,
    InvoicePaymentDetailView,
    InvoicePaymentListCreateView,
    InvoiceViewSet,
)

router = DefaultRouter()
router.register(r"", InvoiceViewSet, basename="invoice")

urlpatterns = [
    path("<int:invoice_pk>/line-items/", InvoiceLineItemListCreateView.as_view(), name="invoice-line-items-list"),
    path("<int:invoice_pk>/line-items/<int:pk>/", InvoiceLineItemDetailView.as_view(), name="invoice-line-items-detail"),
    path("<int:invoice_pk>/payments/", InvoicePaymentListCreateView.as_view(), name="invoice-payments-list"),
    path("<int:invoice_pk>/payments/<int:pk>/", InvoicePaymentDetailView.as_view(), name="invoice-payments-detail"),
] + router.urls
