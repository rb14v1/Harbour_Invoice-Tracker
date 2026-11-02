"""
DEMO DATA SEED (data migration).

Populates a fresh database with one sample login (demo@example.com /
demo12345) plus a handful of clients, invoices covering every status
(draft, sent-unpaid, paid, overdue-unpaid, overdue-partially-paid) with
realistic line items, and payments (a full payment on the paid invoice, a
partial payment on one of the overdue invoices) - so the app is
immediately explorable right after `migrate`, with no manual data entry.

Idempotent by design: every row is looked up with get_or_create (clients,
invoices) or an explicit existence check (line items/payments, which have
no natural unique key) before being created, so running `migrate` more
than once - or reapplying this migration - never produces duplicate rows.
"""
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.db import migrations

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "demo12345"


def seed_demo_data(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Client = apps.get_model("clients", "Client")
    Invoice = apps.get_model("invoices", "Invoice")
    InvoiceLineItem = apps.get_model("invoices", "InvoiceLineItem")
    Payment = apps.get_model("invoices", "Payment")

    today = date.today()

    # Historical models (from `apps.get_model`) only have the fields/methods
    # captured in migration state - no set_password()/custom manager
    # methods from the real User class - so the password is hashed by hand.
    user, created = User.objects.get_or_create(
        email=DEMO_EMAIL,
        defaults={
            "first_name": "Demo", "last_name": "User", "is_active": True,
            "password": make_password(DEMO_PASSWORD),
        },
    )

    def get_or_create_client(name, email, phone="", notes=""):
        client, _ = Client.objects.get_or_create(
            user=user, name=name,
            defaults={"email": email, "phone": phone, "notes": notes},
        )
        return client

    acme = get_or_create_client("Acme Corp", "billing@acme.example.com", "555-0100")
    globex = get_or_create_client("Globex LLC", "ap@globex.example.com", "555-0101")
    initech = get_or_create_client("Initech", "finance@initech.example.com", "555-0102")
    umbrella = get_or_create_client(
        "Umbrella Industries", "payables@umbrella.example.com", "555-0103",
        notes="Prefers invoices itemised by task.",
    )

    def get_or_create_invoice(number, client, issue_date, due_date, inv_status, notes=""):
        invoice, _ = Invoice.objects.get_or_create(
            user=user, invoice_number=number,
            defaults={
                "client": client, "issue_date": issue_date, "due_date": due_date,
                "status": inv_status, "notes": notes,
            },
        )
        return invoice

    def ensure_line_items(invoice, items):
        """items: list of (description, quantity, unit_price) as strings."""
        if invoice.line_items.exists():
            return
        for description, quantity, unit_price in items:
            InvoiceLineItem.objects.create(
                invoice=invoice, description=description,
                quantity=Decimal(quantity), unit_price=Decimal(unit_price),
            )

    def ensure_payment(invoice, amount, paid_date, method):
        amount = Decimal(amount)
        if not invoice.payments.filter(amount=amount, paid_date=paid_date).exists():
            Payment.objects.create(invoice=invoice, amount=amount, paid_date=paid_date, method=method)

    # 1. Draft - never sent, so it can never be overdue regardless of dates.
    draft_invoice = get_or_create_invoice(
        "INV-1001", acme, today - timedelta(days=2), today + timedelta(days=28), "draft",
        notes="Draft - pending internal review before sending.",
    )
    ensure_line_items(draft_invoice, [
        ("Website redesign - discovery phase", "10.00", "95.00"),
        ("Stakeholder workshops", "4.00", "120.00"),
    ])

    # 2. Sent, unpaid, due date still in the future.
    sent_invoice = get_or_create_invoice(
        "INV-1002", globex, today - timedelta(days=5), today + timedelta(days=25), "sent",
    )
    ensure_line_items(sent_invoice, [
        ("Monthly retainer - support & maintenance", "1.00", "750.00"),
        ("Extra hours", "3.50", "85.00"),
    ])

    # 3. Sent and fully paid.
    paid_invoice = get_or_create_invoice(
        "INV-1003", initech, today - timedelta(days=40), today - timedelta(days=10), "sent",
    )
    ensure_line_items(paid_invoice, [
        ("API integration project", "1.00", "2400.00"),
    ])
    ensure_payment(paid_invoice, "2400.00", today - timedelta(days=12), "bank transfer")

    # 4. Sent, overdue, completely unpaid.
    overdue_invoice = get_or_create_invoice(
        "INV-1004", umbrella, today - timedelta(days=60), today - timedelta(days=20), "sent",
    )
    ensure_line_items(overdue_invoice, [
        ("Annual compliance audit", "1.00", "1800.00"),
        ("Report preparation", "6.00", "60.00"),
    ])

    # 5. Sent, overdue, with a partial payment (amount_due > 0, still overdue).
    partial_invoice = get_or_create_invoice(
        "INV-1005", acme, today - timedelta(days=50), today - timedelta(days=5), "sent",
        notes="Client requested a payment plan.",
    )
    ensure_line_items(partial_invoice, [
        ("Brand guidelines", "1.00", "1200.00"),
    ])
    ensure_payment(partial_invoice, "500.00", today - timedelta(days=15), "credit card")


def unseed_demo_data(apps, schema_editor):
    """Reverse migration: deleting the demo user cascades to every client,
    invoice, line item and payment created for them (all CASCADE FKs)."""
    User = apps.get_model("accounts", "User")
    User.objects.filter(email=DEMO_EMAIL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("clients", "0001_initial"),
        ("invoices", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_demo_data, unseed_demo_data),
    ]
