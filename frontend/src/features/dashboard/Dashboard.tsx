import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { fetchDashboard } from "../../api/dashboard";
import { extractErrorMessage } from "../../api/client";
import type { DashboardSummary } from "../../types";
import { formatMoney } from "../../utils/format";

export function Dashboard() {
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchDashboard()
      .then((res) => setSummary(res.data))
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h1>Dashboard</h1>
      </div>

      {error && <div className="form-error">{error}</div>}

      {loading || !summary ? (
        <p>Loading...</p>
      ) : (
        <>
          <div className="summary-grid">
            <div className="summary-tile">
              <div className="label">Total outstanding</div>
              <div className="value negative">{formatMoney(summary.total_outstanding)}</div>
            </div>
            <div className="summary-tile">
              <div className="label">Paid this month</div>
              <div className="value positive">{formatMoney(summary.total_paid_this_month)}</div>
            </div>
            <div className="summary-tile">
              <div className="label">Overdue invoices</div>
              <div className="value">{summary.overdue_invoices.length}</div>
            </div>
          </div>

          <div className="card">
            <h2>Overdue invoices</h2>
            {summary.overdue_invoices.length === 0 && <p className="muted">Nothing overdue. Nice.</p>}
            {summary.overdue_invoices.length > 0 && (
              <table>
                <thead>
                  <tr>
                    <th>Client</th>
                    <th>Total</th>
                    <th>Amount due</th>
                    <th>Days overdue</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {summary.overdue_invoices.map((row) => (
                    <tr key={row.id}>
                      <td>{row.client_name}</td>
                      <td>{formatMoney(row.total)}</td>
                      <td>{formatMoney(row.amount_due)}</td>
                      <td>{row.days_overdue}</td>
                      <td><Link to={`/invoices/${row.id}`}>View</Link></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  );
}
