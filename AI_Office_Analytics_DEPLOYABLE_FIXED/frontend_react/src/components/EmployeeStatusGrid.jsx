import { formatCurrencyPrecise } from "../lib/format";
import { resolveUrl } from "../lib/api";

/**
 * Shown on Overview in place of IdentityPanel whenever the camera currently
 * has no recognized face in frame. Instead of leaving the panel empty, it
 * lists every registered employee with their live status (derived from the
 * existing open-sessions data, same source IdentityPanel/MetricCards use),
 * so the panel never goes blank.
 */
export default function EmployeeStatusGrid({ employees = [], openSessions = [] }) {
  const sessionByEmployeeId = {};
  openSessions.forEach((session) => {
    sessionByEmployeeId[session.employee_id] = session;
  });

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>All Employees</h3>
        <span className="live-tag green">
          <span className="dot"></span>Live
        </span>
      </div>

      <div className="employee-status-grid">
        {employees.length === 0 ? (
          <div className="employee-status-empty">No employees registered yet.</div>
        ) : (
          employees.map((emp) => {
            const session = sessionByEmployeeId[emp.id];
            const isWorking = Boolean(session);

            return (
              <div className="employee-status-card" key={emp.id}>
                {emp.photo_url ? (
                  <img
                    className="employee-status-photo"
                    src={`${resolveUrl(emp.photo_url)}?t=${Date.now()}`}
                    alt={emp.name}
                  />
                ) : (
                  <div className="employee-status-photo-placeholder">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </div>
                )}

                <div className="employee-status-name">{emp.name}</div>

                <span className={`status-pill ${isWorking ? "inside" : "outside"}`}>
                  <span className="dot"></span>
                  <span>{isWorking ? "WORKING INSIDE OFFICE" : "NOT AT WORK"}</span>
                </span>

                <div className="employee-status-meta">
                  <span>Time: {isWorking ? session.duration_str : "0"}</span>
                  <span>Payment: {formatCurrencyPrecise(isWorking ? session.current_payment : 0)}</span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
