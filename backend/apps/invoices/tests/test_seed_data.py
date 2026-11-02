from django.test import TestCase

from apps.accounts.models import User
from apps.clients.models import Client
from apps.invoices.models import Invoice


class SeedDataMigrationTests(TestCase):
    """Verifies the 0002_seed_demo_data data migration (run automatically
    when the test database is created) produced the documented demo
    dataset. Scoped entirely to the demo user, so it can't collide with
    data created by other tests."""

    @classmethod
    def setUpTestData(cls):
        cls.demo_user = User.objects.get(email="demo@example.com")

    def test_demo_user_exists_with_expected_password(self):
        self.assertTrue(self.demo_user.check_password("demo12345"))
        self.assertTrue(self.demo_user.is_active)

    def test_demo_clients_created(self):
        clients = Client.objects.filter(user=self.demo_user)
        self.assertGreaterEqual(clients.count(), 3)
        self.assertLessEqual(clients.count(), 4)

    def test_demo_invoices_cover_every_status(self):
        invoices = Invoice.objects.filter(user=self.demo_user).prefetch_related("line_items", "payments")
        self.assertGreaterEqual(invoices.count(), 4)

        statuses = {invoice.computed_status for invoice in invoices}
        self.assertIn("draft", statuses)
        self.assertIn("sent", statuses)
        self.assertIn("paid", statuses)
        self.assertIn("overdue", statuses)

    def test_demo_invoices_have_realistic_line_items(self):
        invoices = Invoice.objects.filter(user=self.demo_user).prefetch_related("line_items")
        for invoice in invoices:
            self.assertGreater(invoice.line_items.count(), 0, f"{invoice.invoice_number} has no line items")
            self.assertGreater(invoice.total, 0)

    def test_paid_invoice_has_a_full_payment(self):
        invoices = Invoice.objects.filter(user=self.demo_user).prefetch_related("line_items", "payments")
        paid_invoices = [inv for inv in invoices if inv.computed_status == "paid"]
        self.assertGreaterEqual(len(paid_invoices), 1)
        for invoice in paid_invoices:
            self.assertGreaterEqual(invoice.amount_paid, invoice.total)
            self.assertTrue(invoice.payments.exists())

    def test_one_other_invoice_has_a_partial_payment(self):
        invoices = Invoice.objects.filter(user=self.demo_user).prefetch_related("line_items", "payments")
        partially_paid = [
            inv for inv in invoices
            if inv.payments.exists() and 0 < inv.amount_paid < inv.total
        ]
        self.assertGreaterEqual(len(partially_paid), 1)

    def test_seed_migration_is_idempotent_when_rerun_directly(self):
        """Simulates re-running `migrate` by invoking the migration's
        forward function a second time directly against the already-seeded
        test database - get_or_create / existence checks inside it must
        guard against duplicate rows."""
        import importlib

        from django.apps import apps as global_apps

        module = importlib.import_module("apps.invoices.migrations.0002_seed_demo_data")

        before_clients = Client.objects.filter(user=self.demo_user).count()
        before_invoices = Invoice.objects.filter(user=self.demo_user).count()
        before_line_items = sum(inv.line_items.count() for inv in Invoice.objects.filter(user=self.demo_user))
        before_payments = sum(inv.payments.count() for inv in Invoice.objects.filter(user=self.demo_user))

        module.seed_demo_data(global_apps, None)

        self.assertEqual(Client.objects.filter(user=self.demo_user).count(), before_clients)
        self.assertEqual(Invoice.objects.filter(user=self.demo_user).count(), before_invoices)
        self.assertEqual(
            sum(inv.line_items.count() for inv in Invoice.objects.filter(user=self.demo_user)), before_line_items
        )
        self.assertEqual(
            sum(inv.payments.count() for inv in Invoice.objects.filter(user=self.demo_user)), before_payments
        )
