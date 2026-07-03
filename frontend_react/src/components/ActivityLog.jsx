import { formatCurrency } from "../lib/format";

export default function ActivityLog({ items, onViewAll }) {
  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Real Time Activity Logs</h3>
        <button className="activity-panel-header-action" onClick={onViewAll}>
          View All Logs
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="5" y1="12" x2="19" y2="12" />
            <polyline points="12 5 19 12 12 19" />
          </svg>
        </button>
      </div>
      <div>
        {!items || items.length === 0 ? (
          <div className="activity-empty">Waiting for activity. Employees will appear here as they enter and exit.</div>
        ) : (
          items.map((item, idx) => {
            const isEntry = item.event_type === "ENTRY";
            return (
              <div className="activity-row" key={idx}>
                <div className={`activity-icon ${isEntry ? "entry" : "exit"}`}>
                  {isEntry ? (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  ) : (
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                      <line x1="19" y1="12" x2="5" y2="12" />
                      <polyline points="12 19 5 12 12 5" />
                    </svg>
                  )}
                </div>
                <div className="activity-text">
                  <strong>{item.employee_name}</strong>{" "}
                  <span className="action">{isEntry ? "entered the office" : "exited the office"}</span>
                </div>
                <div className="activity-time">{item.time}</div>
                <div className={`activity-badge ${isEntry ? "entry" : "exit"}`}>{isEntry ? "ENTRY" : "EXIT"}</div>
                <span className="activity-paid">
                  {!isEntry && item.payment != null ? `Paid: ${formatCurrency(item.payment)}` : ""}
                </span>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
