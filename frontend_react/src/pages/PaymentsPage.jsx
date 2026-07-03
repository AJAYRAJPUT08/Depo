import { useEffect, useState } from "react";
import { getRecords } from "../lib/api";
import { useToast } from "../lib/ToastContext";
import { formatCurrency, formatDateDisplay } from "../lib/format";

export default function PaymentsPage() {
  const [records, setRecords] = useState(null);
  const showToast = useToast();

  useEffect(() => {
    getRecords()
      .then(setRecords)
      .catch(() => showToast("Could not load payment logs.", "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <section className="page-view active-view">
      <div className="page-header">
        <div>
          <h1>Payment Logs</h1>
          <p>All calculated payments based on hours worked</p>
        </div>
      </div>

      <div className="panel">
        <table className="data-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Date</th>
              <th>Hours Worked</th>
              <th>Hourly Rate</th>
              <th>Total Payment</th>
            </tr>
          </thead>
          <tbody>
            {!records || records.length === 0 ? (
              <tr>
                <td colSpan={5} className="cell-muted">
                  No payment records yet.
                </td>
              </tr>
            ) : (
              records.map((r) => (
                <tr key={r.id}>
                  <td className="cell-name">{r.employee_name}</td>
                  <td>{formatDateDisplay(r.date)}</td>
                  <td>{(r.duration_seconds / 3600).toFixed(2)} hrs</td>
                  <td>₹{Number(r.hourly_rate).toLocaleString("en-IN")} / hr</td>
                  <td className="cell-payment">{formatCurrency(r.payment)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}
