from datetime import timedelta
from decimal import Decimal

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.clients.models import Client
from apps.invoices.models import Invoice, InvoiceLineItem, Payment
from common.test_utils import auth_client, create_user

TODAY = timezone.localdate()


class DashboardAggregationTests(APITestCase):
    def setUp(self):
        self.user = create_user(email="dash@example.com")
        self.other_user = create_user(email="dash-other@example.com")
        self.client_obj = Client.objects.create(user=self.user, name="Acme", email="acme@example.com")

        # Draft invoice - excluded from outstanding entirely.
        draft = Invoice.objects.create(
            user=self.user, client=self.client_obj, invoice_number="DRAFT-1",
            issue_date=TODAY, due_date=TODAY + timedelta(days=30), status=Invoice.Status.DRAFT,
        )
        InvoiceLineItem.objects.create(invoice=draft, description="Work", quantity=1, unit_price=Decimal("999.00"))

        # Sent, unpaid, not yet due - contributes full total to outstanding.
        self.sent_unpaid = Invoice.objects.create(
            user=self.user, client=self.client_obj, invoice_number="SENT-1",
            issue_date=TODAY, due_date=TODAY + timedelta(days=10), status=Invoice.Status.SENT,
        )
        InvoiceLineItem.objects.create(invoice=self.sent_unpaid, description="Work", quantity=1, unit_price=Decimal("200.00"))

        # Sent, fully paid - excluded from outstanding, counts toward paid-this-month.
        paid = Invoice.objects.create(
            user=self.user, client=self.client_obj, invoice_number="PAID-1",
            issue_date=TODAY, due_date=TODAY + timedelta(days=10), status=Invoice.Status.SENT,
        )
        InvoiceLineItem.objects.create(invoice=paid, description="Work", quantity=1, unit_price=Decimal("300.00"))
        Payment.objects.create(invoice=paid, amount=Decimal("300.00"), paid_date=TODAY)

        # Sent, overdue, partially paid - amount_due (not total) counts toward outstanding.
        self.overdue = Invoice.objects.create(
            user=self.user, client=self.client_obj, invoice_number="OVERDUE-1",
            issue_date=TODAY - timedelta(days=60), due_date=TODAY - timedelta(days=15), status=Invoice.Status.SENT,
        )
        InvoiceLineItem.objects.create(invoice=self.overdue, description="Work", quantity=1, unit_price=Decimal("500.00"))
        # paid_date=TODAY (not an offset) so this reliably falls within the
        # current calendar month regardless of what day-of-month tests run on.
        Payment.objects.create(invoice=self.overdue, amount=Decimal("100.00"), paid_date=TODAY)

        # A payment made last month must not count toward this month's total.
        last_month_payment_date = (TODAY.replace(day=1) - timedelta(days=1))
        old_paid = Invoice.objects.create(
            user=self.user, client=self.client_obj, invoice_number="PAID-OLD",
            issue_date=last_month_payment_date, due_date=last_month_payment_date + timedelta(days=5),
            status=Invoice.Status.SENT,
        )
        InvoiceLineItem.objects.create(invoice=old_paid, description="Work", quantity=1, unit_price=Decimal("50.00"))
        Payment.objects.create(invoice=old_paid, amount=Decimal("50.00"), paid_date=last_month_payment_date)

        # Another user's data must never leak in.
        other_client = Client.objects.create(user=self.other_user, name="Other", email="other@example.com")
        other_invoice = Invoice.objects.create(
            user=self.other_user, client=other_client, invoice_number="OTHER-1",
            issue_date=TODAY - timedelta(days=60), due_date=TODAY - timedelta(days=15), status=Invoice.Status.SENT,
        )
        InvoiceLineItem.objects.create(invoice=other_invoice, description="Work", quantity=1, unit_price=Decimal("5000.00"))

    def test_total_outstanding_excludes_draft_and_paid(self):
        api = auth_client(self.user)
        response = api.get(reverse("dashboard"))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # sent_unpaid: 200.00 due + overdue: 500 - 100 = 400.00 due = 600.00
        self.assertEqual(Decimal(response.data["total_outstanding"]), Decimal("600.00"))

    def test_total_paid_this_month_excludes_other_months_and_other_users(self):
        api = auth_client(self.user)
        response = api.get(reverse("dashboard"))
        # paid (300.00) + overdue's partial payment (100.00) = 400.00.
        # old_paid's 50.00 was paid last month and must be excluded.
        self.assertEqual(Decimal(response.data["total_paid_this_month"]), Decimal("400.00"))

    def test_overdue_invoices_list_contains_only_overdue_invoice(self):
        api = auth_client(self.user)
        response = api.get(reverse("dashboard"))
        overdue_ids = [row["id"] for row in response.data["overdue_invoices"]]
        self.assertEqual(overdue_ids, [self.overdue.id])
        row = response.data["overdue_invoices"][0]
        self.assertEqual(row["client_name"], "Acme")
        self.assertEqual(Decimal(row["total"]), Decimal("500.00"))
        self.assertEqual(Decimal(row["amount_due"]), Decimal("400.00"))
        self.assertEqual(row["days_overdue"], 15)

    def test_other_users_data_never_appears(self):
        api = auth_client(self.user)
        response = api.get(reverse("dashboard"))
        overdue_ids = [row["id"] for row in response.data["overdue_invoices"]]
        self.assertNotIn("other_invoice", str(response.data))
        self.assertTrue(all(Decimal(row["total"]) != Decimal("5000.00") for row in response.data["overdue_invoices"]))
