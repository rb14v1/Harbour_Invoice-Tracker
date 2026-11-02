from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.test import APITestCase

from apps.clients.models import Client
from apps.invoices.models import Invoice, InvoiceLineItem, Payment
from common.test_utils import auth_client, create_user

TODAY = timezone.localdate()
YESTERDAY = TODAY - timedelta(days=1)
TOMORROW = TODAY + timedelta(days=1)


def make_invoice(user, client, **kwargs):
    defaults = {
        "invoice_number": "INV-TEST",
        "issue_date": TODAY - timedelta(days=10),
        "due_date": TOMORROW,
    }
    defaults.update(kwargs)
    return Invoice.objects.create(user=user, client=client, **defaults)


class InvoiceStatusTransitionTests(TestCase):
    """Covers every branch of Invoice.computed_status."""

    def setUp(self):
        self.user = create_user(email="status@example.com")
        self.client_obj = Client.objects.create(user=self.user, name="Acme", email="acme@example.com")

    def _add_line_item(self, invoice, quantity="2.00", unit_price="50.00"):
        return InvoiceLineItem.objects.create(
            invoice=invoice, description="Work", quantity=Decimal(quantity), unit_price=Decimal(unit_price)
        )

    def test_draft_until_explicitly_marked_sent(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.DRAFT, due_date=YESTERDAY)
        self._add_line_item(invoice)
        # Even with a past due date, a draft invoice is never overdue/sent/paid.
        self.assertEqual(invoice.computed_status, "draft")

    def test_sent_and_unpaid_before_due_date_is_sent(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.SENT, due_date=TOMORROW)
        self._add_line_item(invoice)
        self.assertEqual(invoice.computed_status, "sent")

    def test_sent_becomes_paid_when_payments_cover_total(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.SENT, due_date=TOMORROW)
        self._add_line_item(invoice, quantity="2.00", unit_price="50.00")  # total = 100.00
        Payment.objects.create(invoice=invoice, amount=Decimal("100.00"), paid_date=TODAY)
        self.assertEqual(invoice.computed_status, "paid")

    def test_sent_becomes_paid_with_multiple_partial_payments_summing_to_total(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.SENT, due_date=TOMORROW)
        self._add_line_item(invoice, quantity="2.00", unit_price="50.00")  # total = 100.00
        Payment.objects.create(invoice=invoice, amount=Decimal("40.00"), paid_date=TODAY)
        Payment.objects.create(invoice=invoice, amount=Decimal("60.00"), paid_date=TODAY)
        self.assertEqual(invoice.computed_status, "paid")

    def test_sent_past_due_and_unpaid_is_overdue(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.SENT, due_date=YESTERDAY)
        self._add_line_item(invoice)
        self.assertEqual(invoice.computed_status, "overdue")

    def test_sent_past_due_with_partial_payment_is_overdue_not_paid(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.SENT, due_date=YESTERDAY)
        self._add_line_item(invoice, quantity="2.00", unit_price="50.00")  # total = 100.00
        Payment.objects.create(invoice=invoice, amount=Decimal("30.00"), paid_date=TODAY)
        self.assertEqual(invoice.computed_status, "overdue")

    def test_paid_always_wins_even_when_due_date_has_passed(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.SENT, due_date=YESTERDAY)
        self._add_line_item(invoice, quantity="2.00", unit_price="50.00")  # total = 100.00
        Payment.objects.create(invoice=invoice, amount=Decimal("100.00"), paid_date=TODAY)
        self.assertEqual(invoice.computed_status, "paid")
        self.assertEqual(invoice.days_overdue, 0)

    def test_total_amount_paid_and_amount_due_are_computed_correctly(self):
        invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.SENT, due_date=TOMORROW)
        self._add_line_item(invoice, quantity="3.00", unit_price="10.00")  # 30.00
        self._add_line_item(invoice, quantity="1.00", unit_price="20.00")  # 20.00
        Payment.objects.create(invoice=invoice, amount=Decimal("15.00"), paid_date=TODAY)
        self.assertEqual(invoice.total, Decimal("50.00"))
        self.assertEqual(invoice.amount_paid, Decimal("15.00"))
        self.assertEqual(invoice.amount_due, Decimal("35.00"))

    def test_days_overdue_counts_days_since_due_date(self):
        invoice = make_invoice(
            self.user, self.client_obj, status=Invoice.Status.SENT, due_date=TODAY - timedelta(days=5)
        )
        self._add_line_item(invoice)
        self.assertEqual(invoice.computed_status, "overdue")
        self.assertEqual(invoice.days_overdue, 5)


class MarkSentApiTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="marksent@example.com")
        self.client_obj = Client.objects.create(user=self.user, name="Acme", email="acme@example.com")
        self.invoice = make_invoice(self.user, self.client_obj, status=Invoice.Status.DRAFT)

    def test_mark_sent_transitions_draft_to_sent(self):
        api = auth_client(self.user)
        response = api.post(reverse("invoice-mark-sent", args=[self.invoice.id]))
        self.assertEqual(response.status_code, http_status.HTTP_200_OK, response.data)
        self.invoice.refresh_from_db()
        self.assertEqual(self.invoice.status, Invoice.Status.SENT)
        self.assertEqual(response.data["status"], "sent")

    def test_mark_sent_twice_is_rejected(self):
        api = auth_client(self.user)
        api.post(reverse("invoice-mark-sent", args=[self.invoice.id]))
        response = api.post(reverse("invoice-mark-sent", args=[self.invoice.id]))
        self.assertEqual(response.status_code, http_status.HTTP_400_BAD_REQUEST)
