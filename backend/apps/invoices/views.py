from datetime import date

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.invoices.models import Invoice, InvoiceLineItem, Payment
from apps.invoices.serializers import (
    InvoiceLineItemSerializer,
    InvoiceSerializer,
    PaymentSerializer,
)


def get_user_invoice_or_404(user, invoice_pk):
    """Looks up an invoice scoped to `user`. Mirrors the 404-not-403 pattern
    used across this app for cross-user isolation: another user's invoice
    ID looks identical to one that doesn't exist at all."""
    return get_object_or_404(Invoice, pk=invoice_pk, user=user)


class InvoiceViewSet(viewsets.ModelViewSet):
    serializer_class = InvoiceSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = []  # manual filtering below - computed_status isn't a DB column

    def get_queryset(self):
        qs = Invoice.objects.filter(user=self.request.user).select_related("client").prefetch_related(
            "line_items", "payments"
        )
        client_param = self.request.query_params.get("client")
        if client_param:
            qs = qs.filter(client_id=client_param)

        status_param = self.request.query_params.get("status")
        if status_param:
            # computed_status isn't a DB column, so filter in Python. Small
            # demo dataset per user - fine to materialize here.
            qs = [invoice for invoice in qs if invoice.computed_status == status_param]
        return qs

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"], url_path="mark-sent")
    def mark_sent(self, request, pk=None):
        invoice = get_user_invoice_or_404(request.user, pk)
        if invoice.status != Invoice.Status.DRAFT:
            return Response(
                {"detail": "Only a draft invoice can be marked as sent."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        invoice.status = Invoice.Status.SENT
        invoice.save(update_fields=["status"])
        return Response(InvoiceSerializer(invoice).data)


class InvoiceLineItemListCreateView(generics.ListCreateAPIView):
    serializer_class = InvoiceLineItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_invoice(self):
        return get_user_invoice_or_404(self.request.user, self.kwargs["invoice_pk"])

    def get_queryset(self):
        return InvoiceLineItem.objects.filter(invoice=self.get_invoice())

    def perform_create(self, serializer):
        serializer.save(invoice=self.get_invoice())


class InvoiceLineItemDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = InvoiceLineItemSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        invoice = get_user_invoice_or_404(self.request.user, self.kwargs["invoice_pk"])
        return InvoiceLineItem.objects.filter(invoice=invoice)


class InvoicePaymentListCreateView(generics.ListCreateAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_invoice(self):
        return get_user_invoice_or_404(self.request.user, self.kwargs["invoice_pk"])

    def get_queryset(self):
        return Payment.objects.filter(invoice=self.get_invoice())

    def perform_create(self, serializer):
        serializer.save(invoice=self.get_invoice())


class InvoicePaymentDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        invoice = get_user_invoice_or_404(self.request.user, self.kwargs["invoice_pk"])
        return Payment.objects.filter(invoice=invoice)
