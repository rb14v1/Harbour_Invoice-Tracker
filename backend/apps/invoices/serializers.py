from rest_framework import serializers

from apps.invoices.models import Invoice, InvoiceLineItem, Payment


class InvoiceLineItemSerializer(serializers.ModelSerializer):
    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = InvoiceLineItem
        fields = ["id", "invoice", "description", "quantity", "unit_price", "line_total"]
        read_only_fields = ["id", "invoice", "line_total"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than zero.")
        return value

    def validate_unit_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Unit price cannot be negative.")
        return value


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "invoice", "amount", "paid_date", "method"]
        read_only_fields = ["id", "invoice"]

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")
        return value


class InvoiceSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source="client.name", read_only=True)
    status = serializers.CharField(source="computed_status", read_only=True)
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    amount_paid = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    amount_due = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    days_overdue = serializers.IntegerField(read_only=True)
    line_items = InvoiceLineItemSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Invoice
        fields = [
            "id", "client", "client_name", "invoice_number", "issue_date", "due_date",
            "status", "notes", "total", "amount_paid", "amount_due", "days_overdue",
            "line_items", "payments", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]

    def validate_client(self, value):
        request = self.context["request"]
        if value.user_id != request.user.id:
            raise serializers.ValidationError("Client not found.")
        return value

    def validate_invoice_number(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Invoice number cannot be blank.")
        return value

    def validate(self, attrs):
        request = self.context["request"]
        invoice_number = attrs.get("invoice_number", getattr(self.instance, "invoice_number", None))
        if invoice_number and Invoice.objects.filter(
            user=request.user, invoice_number__iexact=invoice_number
        ).exclude(pk=getattr(self.instance, "pk", None)).exists():
            raise serializers.ValidationError({"invoice_number": "You already have an invoice with this number."})

        issue_date = attrs.get("issue_date", getattr(self.instance, "issue_date", None))
        due_date = attrs.get("due_date", getattr(self.instance, "due_date", None))
        if issue_date and due_date and due_date < issue_date:
            raise serializers.ValidationError({"due_date": "Due date cannot be before the issue date."})
        return attrs
