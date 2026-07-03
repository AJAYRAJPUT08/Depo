import { resolveUrl } from "../lib/api";

export default function EmployeeCard({ employee, onEdit, onDelete }) {
  return (
    <div className="employee-card">
      <div className="employee-card-top">
        {employee.photo_url ? (
          <img className="employee-card-photo" src={`${resolveUrl(employee.photo_url)}?t=${Date.now()}`} alt={employee.name} />
        ) : (
          <div className="employee-card-photo-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
        )}
        <div>
          <div className="employee-card-name">{employee.name}</div>
          <div className="employee-card-rate">₹{Number(employee.hourly_rate).toLocaleString("en-IN")} / hr</div>
        </div>
      </div>
      <div className="employee-card-footer">
        {employee.status === "INSIDE" ? (
          <span className="status-pill inside">
            <span className="dot"></span>INSIDE
          </span>
        ) : (
          <span className="status-pill outside">
            <span className="dot"></span>OUTSIDE
          </span>
        )}
        <div className="employee-card-actions">
          <button className="icon-btn" title="Edit" onClick={() => onEdit(employee)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.12 2.12 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
          <button className="icon-btn danger" title="Delete" onClick={() => onDelete(employee)}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polyline points="3 6 5 6 21 6" />
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
