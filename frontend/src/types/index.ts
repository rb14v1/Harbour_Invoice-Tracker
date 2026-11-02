export interface User {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  date_joined: string;
}

export interface Client {
  id: number;
  name: string;
  email: string;
  phone: string;
  notes: string;
  created_at: string;
}

export type InvoiceStatus = "draft" | "sent" | "paid" | "overdue";

export interface InvoiceLineItem {
  id: number;
  invoice: number;
  description: string;
  quantity: string;
  unit_price: string;
  line_total: string;
}

export interface Payment {
  id: number;
  invoice: number;
  amount: string;
  paid_date: string;
  method: string;
}

export interface Invoice {
  id: number;
  client: number;
  client_name: string;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  status: InvoiceStatus;
  notes: string;
  total: string;
  amount_paid: string;
  amount_due: string;
  days_overdue: number;
  line_items: InvoiceLineItem[];
  payments: Payment[];
  created_at: string;
}

export interface OverdueInvoiceRow {
  id: number;
  client_name: string;
  total: string;
  amount_due: string;
  days_overdue: number;
}

export interface DashboardSummary {
  total_outstanding: string;
  total_paid_this_month: string;
  overdue_invoices: OverdueInvoiceRow[];
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
