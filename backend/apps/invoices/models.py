from datetime import date
from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.clients.models import Client


class Invoice(models.Model):
    """An invoice billed by the logged-in user to one of their clients.

    Status model
    ------------
    Only two states are ever *persisted* on `status`: ``draft`` and
    ``sent``. An invoice starts as `draft` and is moved to `sent` exactly
    once, via the explicit `mark-sent` action (``POST
    /api/invoices/{id}/mark-sent/``) - it never happens implicitly on save.

    The user/API-visible status (draft/sent/paid/overdue) is *computed* on
    read by `computed_status`, layered on top of the persisted `status`:

    1. `draft`  - persisted status is still `draft`.
    2. `paid`   - persisted status is `sent` AND sum(payments) >= total.
       Paid always wins once reached: a paid invoice whose due_date has
       since passed is NOT overdue.
    3. `overdue`- persisted status is `sent`, not fully paid, and
       `due_date` is in the past.
    4. `sent`   - persisted status is `sent`, not fully paid, due_date not
       yet passed.

    `total`, `amount_paid` and `amount_due` are likewise never stored -
    they are always derived from the related line items / payments (see
    the properties below and InvoiceSerializer).
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="invoices")
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="invoices")
    invoice_number = models.CharField(max_length=50)
    issue_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-issue_date", "-id"]
        constraints = [
            models.UniqueConstraint(fields=["user", "invoice_number"], name="unique_invoice_number_per_user"),
        ]

    def __str__(self):
        return f"{self.invoice_number} ({self.client.name})"

    @property
    def total(self) -> Decimal:
        """Sum of quantity * unit_price across line items. Computed, not
        stored - relies on `line_items` having been prefetched by the
        caller for efficiency, but works either way."""
        return sum(
            (item.quantity * item.unit_price for item in self.line_items.all()),
            Decimal("0.00"),
        )

    @property
    def amount_paid(self) -> Decimal:
        return sum((p.amount for p in self.payments.all()), Decimal("0.00"))

    @property
    def amount_due(self) -> Decimal:
        return self.total - self.amount_paid

    @property
    def is_fully_paid(self) -> bool:
        total = self.total
        return total > 0 and self.amount_paid >= total

    @property
    def computed_status(self) -> str:
        if self.status == self.Status.DRAFT:
            return self.Status.DRAFT
        # status == SENT from here on.
        if self.is_fully_paid:
            return "paid"
        if self.due_date < date.today():
            return "overdue"
        return self.Status.SENT

    @property
    def days_overdue(self) -> int:
        if self.computed_status != "overdue":
            return 0
        return (date.today() - self.due_date).days


class InvoiceLineItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="line_items")
    description = models.CharField(max_length=255)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1.00"))
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return self.description

    @property
    def line_total(self) -> Decimal:
        return self.quantity * self.unit_price


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    paid_date = models.DateField()
    method = models.CharField(max_length=100, blank=True, default="")

    class Meta:
        ordering = ["paid_date", "id"]

    def __str__(self):
        return f"{self.amount} on {self.paid_date}"
