import { apiClient } from "./client";
import type { Invoice, InvoiceLineItem, InvoiceStatus, Paginated, Payment } from "../types";

export interface InvoiceFilters {
  status?: InvoiceStatus;
  client?: number;
}

export interface InvoiceInput {
  client: number;
  invoice_number: string;
  issue_date: string;
  due_date: string;
  notes?: string;
}

export interface LineItemInput {
  description: string;
  quantity: string;
  unit_price: string;
}

export interface PaymentInput {
  amount: string;
  paid_date: string;
  method?: string;
}

export function listInvoices(filters: InvoiceFilters = {}) {
  return apiClient.get<Paginated<Invoice>>("/invoices/", { params: { ...filters, page_size: 100 } });
}

export function getInvoice(id: number) {
  return apiClient.get<Invoice>(`/invoices/${id}/`);
}

export function createInvoice(data: InvoiceInput) {
  return apiClient.post<Invoice>("/invoices/", data);
}

export function updateInvoice(id: number, data: InvoiceInput) {
  return apiClient.put<Invoice>(`/invoices/${id}/`, data);
}

export function deleteInvoice(id: number) {
  return apiClient.delete(`/invoices/${id}/`);
}

export function markInvoiceSent(id: number) {
  return apiClient.post<Invoice>(`/invoices/${id}/mark-sent/`);
}

export function addLineItem(invoiceId: number, data: LineItemInput) {
  return apiClient.post<InvoiceLineItem>(`/invoices/${invoiceId}/line-items/`, data);
}

export function deleteLineItem(invoiceId: number, lineItemId: number) {
  return apiClient.delete(`/invoices/${invoiceId}/line-items/${lineItemId}/`);
}

export function addPayment(invoiceId: number, data: PaymentInput) {
  return apiClient.post<Payment>(`/invoices/${invoiceId}/payments/`, data);
}

export function deletePayment(invoiceId: number, paymentId: number) {
  return apiClient.delete(`/invoices/${invoiceId}/payments/${paymentId}/`);
}
