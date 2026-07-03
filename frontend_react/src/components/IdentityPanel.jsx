import { formatCurrencyPrecise, formatRate } from "../lib/format";
import { resolveUrl } from "../lib/api";

export default function IdentityPanel({ data }) {
  const isInside = data?.detected && data?.status === "INSIDE";

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>Identified Employee</h3>
        <span className="live-tag green">
          <span className="dot"></span>Live
        </span>
      </div>
      <div className="identity-body">
        <div className="identity-top">
          {data?.detected && data?.photo_url ? (
            <img className="identity-photo" src={`${resolveUrl(data.photo_url)}?t=${Date.now()}`} alt={data.name} />
          ) : (
            <div className="identity-photo-placeholder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
          )}
          <div className="identity-name-block">
            <strong>{data?.detected ? data.name : "No employee detected"}</strong>
            <span className={`status-pill ${isInside ? "inside" : "outside"}`}>
              <span className="dot"></span>
              <span>{isInside ? "INSIDE OFFICE" : "OUTSIDE OFFICE"}</span>
            </span>
          </div>
        </div>

        <div className="identity-detail-row">
          <span className="identity-detail-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            Entry Time
          </span>
          <span className="identity-detail-value">{data?.entry_time || "—"}</span>
        </div>
        <div className="identity-detail-row">
          <span className="identity-detail-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            Current Duration
          </span>
          <span className="identity-detail-value green">{data?.duration_str || "—"}</span>
        </div>
        <div className="identity-detail-row">
          <span className="identity-detail-label">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <path d="M12 6v12M9 9.5c0-1.4 1.3-2.5 3-2.5s3 1.1 3 2.5-1.3 2.5-3 2.5-3 1.1-3 2.5 1.3 2.5 3 2.5 3-1.1 3-2.5" />
            </svg>
            Hourly Rate
          </span>
          <span className="identity-detail-value">{formatRate(data?.hourly_rate)}</span>
        </div>

        <div className="payment-box">
          <span className="payment-box-label">Current Payment</span>
          <span className="payment-box-value">{formatCurrencyPrecise(data?.current_payment)}</span>
        </div>
      </div>
    </div>
  );
}
