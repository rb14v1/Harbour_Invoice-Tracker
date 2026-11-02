import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listClients } from "../../api/clients";
import { extractErrorMessage } from "../../api/client";
import { createInvoice, deleteInvoice, listInvoices, markInvoiceSent } from "../../api/invoices";
import type { Client, Invoice, InvoiceStatus } from "../../types";
import { formatMoney, today } from "../../utils/format";
import { StatusBadge } from "./StatusBadge";

export function InvoicesPage() {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<InvoiceStatus | "">("");

  const [clientId, setClientId] = useState<number | "">("");
  const [invoiceNumber, setInvoiceNumber] = useState("");
  const [issueDate, setIssueDate] = useState(today());
  const [dueDate, setDueDate] = useState(today());
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function loadClients() {
    const res = await listClients();
    setClients(res.data.results);
  }

  async function loadInvoices() {
    setLoading(true);
    setError(null);
    try {
      const res = await listInvoices({ status: statusFilter || undefined });
      setInvoices(res.data.results);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadClients();
  }, []);

  useEffect(() => {
    loadInvoices();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  function resetForm() {
    setClientId("");
    setInvoiceNumber("");
    setIssueDate(today());
    setDueDate(today());
    setNotes("");
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!clientId) {
      setError("Select a client.");
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await createInvoice({
        client: Number(clientId),
        invoice_number: invoiceNumber,
        issue_date: issueDate,
        due_date: dueDate,
        notes,
      });
      resetForm();
      await loadInvoices();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleMarkSent(id: number) {
    setError(null);
    try {
      await markInvoiceSent(id);
      await loadInvoices();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this invoice?")) return;
    setError(null);
    try {
      await deleteInvoice(id);
      await loadInvoices();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  return (
    <div>
      <div className="page-header">
        <h1>Invoices</h1>
        <label>
          Status{" "}
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as InvoiceStatus | "")}>
            <option value="">All</option>
            <option value="draft">Draft</option>
            <option value="sent">Sent</option>
            <option value="paid">Paid</option>
            <option value="overdue">Overdue</option>
          </select>
        </label>
      </div>

      <div className="card">
        <form className="inline-form" onSubmit={handleSubmit}>
          <label>
            Client
            <select value={clientId} onChange={(e) => setClientId(e.target.value ? Number(e.target.value) : "")} required>
              <option value="">Select...</option>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>{c.name}</option>
              ))}
            </select>
          </label>
          <label>
            Invoice #
            <input value={invoiceNumber} onChange={(e) => setInvoiceNumber(e.target.value)} required />
          </label>
          <label>
            Issue date
            <input type="date" value={issueDate} onChange={(e) => setIssueDate(e.target.value)} required />
          </label>
          <label>
            Due date
            <input type="date" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
          </label>
          <label>
            Notes
            <input value={notes} onChange={(e) => setNotes(e.target.value)} />
          </label>
          <button type="submit" disabled={submitting}>Create invoice</button>
        </form>
        {error && <div className="form-error">{error}</div>}
      </div>

      <div className="card">
        {loading ? (
          <p>Loading...</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Invoice #</th>
                <th>Client</th>
                <th>Issue date</th>
                <th>Due date</th>
                <th>Status</th>
                <th>Total</th>
                <th>Amount due</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {invoices.map((inv) => (
                <tr key={inv.id}>
                  <td><Link to={`/invoices/${inv.id}`}>{inv.invoice_number}</Link></td>
                  <td>{inv.client_name}</td>
                  <td>{inv.issue_date}</td>
                  <td>{inv.due_date}</td>
                  <td><StatusBadge status={inv.status} /></td>
                  <td>{formatMoney(inv.total)}</td>
                  <td>{formatMoney(inv.amount_due)}</td>
                  <td className="actions">
                    {inv.status === "draft" && (
                      <button className="secondary" onClick={() => handleMarkSent(inv.id)}>Mark sent</button>
                    )}
                    <button className="danger" onClick={() => handleDelete(inv.id)}>Delete</button>
                  </td>
                </tr>
              ))}
              {invoices.length === 0 && (
                <tr><td colSpan={8} className="muted">No invoices for this filter.</td></tr>
              )}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
