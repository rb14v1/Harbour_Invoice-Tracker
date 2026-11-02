from datetime import date
from decimal import Decimal

from django.db.models import Sum
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.invoices.models import Invoice, Payment


class DashboardView(APIView):
    """Single-screen summary for the logged-in user:

    - total_outstanding: sum of amount_due across every invoice that is
      currently `sent` or `overdue` (i.e. billed but not yet fully paid).
      Draft invoices are excluded - they haven't been billed yet.
    - total_paid_this_month: sum of payment amounts recorded against any of
      the user's invoices, where the payment's `paid_date` falls in the
      current calendar month.
    - overdue_invoices: every invoice whose computed status is `overdue`.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        today = date.today()

        invoices = Invoice.objects.filter(user=user).select_related("client").prefetch_related(
            "line_items", "payments"
        )

        total_outstanding = Decimal("0.00")
        overdue_invoices = []
        for invoice in invoices:
            computed = invoice.computed_status
            if computed in ("sent", "overdue"):
                total_outstanding += invoice.amount_due
            if computed == "overdue":
                overdue_invoices.append({
                    "id": invoice.id,
                    "client_name": invoice.client.name,
                    "total": invoice.total,
                    "amount_due": invoice.amount_due,
                    "days_overdue": invoice.days_overdue,
                })

        overdue_invoices.sort(key=lambda row: row["days_overdue"], reverse=True)

        total_paid_this_month = Payment.objects.filter(
            invoice__user=user,
            paid_date__year=today.year,
            paid_date__month=today.month,
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return Response({
            "total_outstanding": total_outstanding,
            "total_paid_this_month": total_paid_this_month,
            "overdue_invoices": overdue_invoices,
        })
