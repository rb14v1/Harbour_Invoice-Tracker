import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { extractErrorMessage } from "../../api/client";
import {
  addLineItem,
  addPayment,
  deleteLineItem,
  deletePayment,
  getInvoice,
  markInvoiceSent,
} from "../../api/invoices";
import type { Invoice } from "../../types";
import { formatMoney, today } from "../../utils/format";
import { StatusBadge } from "./StatusBadge";

export function InvoiceDetailPage() {
  const { id } = useParams<{ id: string }>();
  const invoiceId = Number(id);
  const navigate = useNavigate();

  const [invoice, setInvoice] = useState<Invoice | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [description, setDescription] = useState("");
  const [quantity, setQuantity] = useState("1");
  const [unitPrice, setUnitPrice] = useState("");
  const [addingLineItem, setAddingLineItem] = useState(false);

  const [amount, setAmount] = useState("");
  const [paidDate, setPaidDate] = useState(today());
  const [method, setMethod] = useState("");
  const [addingPayment, setAddingPayment] = useState(false);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const res = await getInvoice(invoiceId);
      setInvoice(res.data);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [invoiceId]);

  async function handleMarkSent() {
    setError(null);
    try {
      await markInvoiceSent(invoiceId);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleAddLineItem(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setAddingLineItem(true);
    try {
      await addLineItem(invoiceId, { description, quantity, unit_price: unitPrice });
      setDescription("");
      setQuantity("1");
      setUnitPrice("");
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setAddingLineItem(false);
    }
  }

  async function handleDeleteLineItem(lineItemId: number) {
    setError(null);
    try {
      await deleteLineItem(invoiceId, lineItemId);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  async function handleAddPayment(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setAddingPayment(true);
    try {
      await addPayment(invoiceId, { amount, paid_date: paidDate, method });
      setAmount("");
      setPaidDate(today());
      setMethod("");
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setAddingPayment(false);
    }
  }

  async function handleDeletePayment(paymentId: number) {
    setError(null);
    try {
      await deletePayment(invoiceId, paymentId);
      await load();
    } catch (err) {
      setError(extractErrorMessage(err));
    }
  }

  if (loading) return <p>Loading...</p>;
  if (!invoice) return <p>Invoice not found.</p>;

  return (
    <div>
      <div className="page-header">
        <h1>Invoice {invoice.invoice_number}</h1>
        <div className="actions">
          {invoice.status === "draft" && <button onClick={handleMarkSent}>Mark as sent</button>}
          <button className="secondary" onClick={() => navigate("/invoices")}>Back to invoices</button>
        </div>
      </div>

      {error && <div className="form-error">{error}</div>}

      <div className="card">
        <div className="summary-grid">
          <div className="summary-tile">
            <div className="label">Client</div>
            <div className="value">{invoice.client_name}</div>
          </div>
          <div className="summary-tile">
            <div className="label">Status</div>
            <div className="value"><StatusBadge status={invoice.status} /></div>
          </div>
          <div className="summary-tile">
            <div className="label">Issue / Due</div>
            <div className="value">{invoice.issue_date} / {invoice.due_date}</div>
          </div>
          <div className="summary-tile">
            <div className="label">Total</div>
            <div className="value">{formatMoney(invoice.total)}</div>
          </div>
          <div className="summary-tile">
            <div className="label">Paid</div>
            <div className="value positive">{formatMoney(invoice.amount_paid)}</div>
          </div>
          <div className="summary-tile">
            <div className="label">Amount due</div>
            <div className="value negative">{formatMoney(invoice.amount_due)}</div>
          </div>
        </div>
        {invoice.notes && <p className="muted">Notes: {invoice.notes}</p>}
        {invoice.status === "overdue" && (
          <p className="form-error">{invoice.days_overdue} day(s) overdue.</p>
        )}
      </div>

      <div className="card">
        <h2>Line items</h2>
        <table>
          <thead>
            <tr>
              <th>Description</th>
              <th>Qty</th>
              <th>Unit price</th>
              <th>Line total</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {invoice.line_items.map((item) => (
              <tr key={item.id}>
                <td>{item.description}</td>
                <td>{item.quantity}</td>
                <td>{formatMoney(item.unit_price)}</td>
                <td>{formatMoney(item.line_total)}</td>
                <td className="actions">
                  <button className="danger" onClick={() => handleDeleteLineItem(item.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {invoice.line_items.length === 0 && (
              <tr><td colSpan={5} className="muted">No line items yet.</td></tr>
            )}
          </tbody>
        </table>
        <form className="inline-form" onSubmit={handleAddLineItem}>
          <label>
            Description
            <input value={description} onChange={(e) => setDescription(e.target.value)} required />
          </label>
          <label>
            Quantity
            <input type="number" step="0.01" min="0.01" value={quantity} onChange={(e) => setQuantity(e.target.value)} required />
          </label>
          <label>
            Unit price
            <input type="number" step="0.01" min="0" value={unitPrice} onChange={(e) => setUnitPrice(e.target.value)} required />
          </label>
          <button type="submit" disabled={addingLineItem}>Add line item</button>
        </form>
      </div>

      <div className="card">
        <h2>Payments</h2>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Amount</th>
              <th>Method</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {invoice.payments.map((p) => (
              <tr key={p.id}>
                <td>{p.paid_date}</td>
                <td>{formatMoney(p.amount)}</td>
                <td>{p.method}</td>
                <td className="actions">
                  <button className="danger" onClick={() => handleDeletePayment(p.id)}>Delete</button>
                </td>
              </tr>
            ))}
            {invoice.payments.length === 0 && (
              <tr><td colSpan={4} className="muted">No payments recorded yet.</td></tr>
            )}
          </tbody>
        </table>
        <form className="inline-form" onSubmit={handleAddPayment}>
          <label>
            Amount
            <input type="number" step="0.01" min="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} required />
          </label>
          <label>
            Date
            <input type="date" value={paidDate} onChange={(e) => setPaidDate(e.target.value)} required />
          </label>
          <label>
            Method
            <input value={method} onChange={(e) => setMethod(e.target.value)} placeholder="bank transfer" />
          </label>
          <button type="submit" disabled={addingPayment}>Record payment</button>
        </form>
      </div>
    </div>
  );
}
