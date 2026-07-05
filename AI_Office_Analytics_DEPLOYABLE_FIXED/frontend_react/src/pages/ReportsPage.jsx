import { useEffect, useState } from "react";
import { getRecords } from "../lib/api";
import { useToast } from "../lib/ToastContext";
import { formatCurrency, formatDateDisplay } from "../lib/format";

export default function ReportsPage({ employees }) {
  const [employeeId, setEmployeeId] = useState("");
  const [date, setDate] = useState("");
  const [records, setRecords] = useState(null);
  const showToast = useToast();

  useEffect(() => {
    getRecords({ employeeId, date })
      .then(setRecords)
      .catch(() => showToast("Could not load reports.", "error"));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [employeeId, date]);

  return (
    <section className="page-view active-view">
      <div className="page-header">
        <div>
          <h1>Reports</h1>
          <p>Complete entry and exit history for every employee</p>
        </div>
      </div>

      <div className="filter-bar">
        <select className="filter-select" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)}>
          <option value="">All Employees</option>
          {employees.map((emp) => (
            <option key={emp.id} value={emp.id}>
              {emp.name}
            </option>
          ))}
        </select>
        <input type="date" className="filter-input" value={date} onChange={(e) => setDate(e.target.value)} />
        <button
          className="btn-secondary"
          onClick={() => {
            setEmployeeId("");
            setDate("");
          }}
        >
          Clear Filters
        </button>
      </div>

      <div className="panel">
        <table className="data-table">
          <thead>
            <tr>
              <th>Employee</th>
              <th>Date</th>
              <th>Entry Time</th>
              <th>Exit Time</th>
              <th>Duration</th>
              <th>Payment</th>
            </tr>
          </thead>
          <tbody>
            {!records || records.length === 0 ? (
              <tr>
                <td colSpan={6} className="cell-muted">
                  No attendance records yet.
                </td>
              </tr>
            ) : (
              records.map((r) => (
                <tr key={r.id}>
                  <td className="cell-name">{r.employee_name}</td>
                  <td>{formatDateDisplay(r.date)}</td>
                  <td>{r.entry_time}</td>
                  <td>{r.exit_time}</td>
                  <td>{r.duration_str}</td>
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
