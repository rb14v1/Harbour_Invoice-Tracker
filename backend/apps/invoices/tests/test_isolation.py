from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from apps.clients.models import Client
from apps.invoices.models import Invoice, InvoiceLineItem, Payment
from common.test_utils import auth_client, create_user

TODAY = timezone.localdate()


class CrossUserIsolationTests(TestCase):
    """User B must never be able to see or modify User A's data by ID -
    every lookup across clients, invoices, line items and payments must
    behave as if the object doesn't exist (404), not 403."""

    def setUp(self):
        self.user_a = create_user(email="iso-a@example.com")
        self.user_b = create_user(email="iso-b@example.com")

        self.client_a = Client.objects.create(user=self.user_a, name="A's Client", email="client-a@example.com")
        self.invoice_a = Invoice.objects.create(
            user=self.user_a, client=self.client_a, invoice_number="A-001",
            issue_date=TODAY, due_date=TODAY + timedelta(days=30),
        )
        self.line_item_a = InvoiceLineItem.objects.create(
            invoice=self.invoice_a, description="Consulting", quantity=Decimal("1.00"), unit_price=Decimal("500.00")
        )
        self.payment_a = Payment.objects.create(invoice=self.invoice_a, amount=Decimal("100.00"), paid_date=TODAY)

        self.api_b = auth_client(self.user_b)

    # --- Clients ---

    def test_user_b_cannot_see_user_a_client_in_list(self):
        response = self.api_b.get(reverse("client-list"))
        ids = [row["id"] for row in response.data["results"]]
        self.assertNotIn(self.client_a.id, ids)

    def test_user_b_cannot_retrieve_user_a_client(self):
        response = self.api_b.get(reverse("client-detail", args=[self.client_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_client(self):
        response = self.api_b.patch(reverse("client-detail", args=[self.client_a.id]), {"name": "Hijacked"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.client_a.refresh_from_db()
        self.assertEqual(self.client_a.name, "A's Client")

    def test_user_b_cannot_delete_user_a_client(self):
        response = self.api_b.delete(reverse("client-detail", args=[self.client_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Client.objects.filter(pk=self.client_a.id).exists())

    # --- Invoices ---

    def test_user_b_cannot_see_user_a_invoice_in_list(self):
        response = self.api_b.get(reverse("invoice-list"))
        ids = [row["id"] for row in response.data["results"]]
        self.assertNotIn(self.invoice_a.id, ids)

    def test_user_b_cannot_retrieve_user_a_invoice(self):
        response = self.api_b.get(reverse("invoice-detail", args=[self.invoice_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_invoice(self):
        response = self.api_b.patch(reverse("invoice-detail", args=[self.invoice_a.id]), {"notes": "hijacked"})
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_delete_user_a_invoice(self):
        response = self.api_b.delete(reverse("invoice-detail", args=[self.invoice_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Invoice.objects.filter(pk=self.invoice_a.id).exists())

    def test_user_b_cannot_mark_user_a_invoice_sent(self):
        response = self.api_b.post(reverse("invoice-mark-sent", args=[self.invoice_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_create_invoice_against_user_a_client(self):
        response = self.api_b.post(reverse("invoice-list"), {
            "client": self.client_a.id,
            "invoice_number": "B-999",
            "issue_date": str(TODAY),
            "due_date": str(TODAY + timedelta(days=30)),
        })
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    # --- Line items (nested under invoices) ---

    def test_user_b_cannot_list_line_items_of_user_a_invoice(self):
        response = self.api_b.get(reverse("invoice-line-items-list", args=[self.invoice_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_create_line_item_on_user_a_invoice(self):
        response = self.api_b.post(reverse("invoice-line-items-list", args=[self.invoice_a.id]), {
            "description": "Sneaky", "quantity": "1.00", "unit_price": "1.00",
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_retrieve_user_a_line_item(self):
        response = self.api_b.get(
            reverse("invoice-line-items-detail", args=[self.invoice_a.id, self.line_item_a.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_update_user_a_line_item(self):
        response = self.api_b.patch(
            reverse("invoice-line-items-detail", args=[self.invoice_a.id, self.line_item_a.id]),
            {"description": "hijacked"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_delete_user_a_line_item(self):
        response = self.api_b.delete(
            reverse("invoice-line-items-detail", args=[self.invoice_a.id, self.line_item_a.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(InvoiceLineItem.objects.filter(pk=self.line_item_a.id).exists())

    # --- Payments (nested under invoices) ---

    def test_user_b_cannot_list_payments_of_user_a_invoice(self):
        response = self.api_b.get(reverse("invoice-payments-list", args=[self.invoice_a.id]))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_create_payment_on_user_a_invoice(self):
        response = self.api_b.post(reverse("invoice-payments-list", args=[self.invoice_a.id]), {
            "amount": "1.00", "paid_date": str(TODAY),
        })
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_retrieve_user_a_payment(self):
        response = self.api_b.get(
            reverse("invoice-payments-detail", args=[self.invoice_a.id, self.payment_a.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_user_b_cannot_delete_user_a_payment(self):
        response = self.api_b.delete(
            reverse("invoice-payments-detail", args=[self.invoice_a.id, self.payment_a.id])
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Payment.objects.filter(pk=self.payment_a.id).exists())

    # --- Sanity check: user A can access all of their own data ---

    def test_user_a_can_access_their_own_data(self):
        api_a = auth_client(self.user_a)
        self.assertEqual(api_a.get(reverse("client-detail", args=[self.client_a.id])).status_code, status.HTTP_200_OK)
        self.assertEqual(api_a.get(reverse("invoice-detail", args=[self.invoice_a.id])).status_code, status.HTTP_200_OK)
        self.assertEqual(
            api_a.get(reverse("invoice-line-items-detail", args=[self.invoice_a.id, self.line_item_a.id])).status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(
            api_a.get(reverse("invoice-payments-detail", args=[self.invoice_a.id, self.payment_a.id])).status_code,
            status.HTTP_200_OK,
        )
