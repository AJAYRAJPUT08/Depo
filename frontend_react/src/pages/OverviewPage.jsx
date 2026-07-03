import { useState } from "react";
import { getActivityLog, getCurrentEmployee, getDashboardSummary, getOpenSessions, listEmployees } from "../lib/api";
import { usePolling, useClock } from "../lib/useClock";
import CameraFeed from "../components/CameraFeed";
import MetricCards from "../components/MetricCards";
import IdentityPanel from "../components/IdentityPanel";
import EmployeeStatusGrid from "../components/EmployeeStatusGrid";
import ActivityLog from "../components/ActivityLog";

export default function OverviewPage({ cameraAvailable, onNavigate }) {
  const now = useClock();
  const [summary, setSummary] = useState(null);
  const [identity, setIdentity] = useState(null);
  const [activity, setActivity] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [openSessions, setOpenSessions] = useState([]);

  usePolling(() => getDashboardSummary().then(setSummary).catch(() => {}), 2000);
  usePolling(() => getCurrentEmployee().then(setIdentity).catch(() => {}), 1000);
  usePolling(() => getActivityLog(12).then(setActivity).catch(() => {}), 2000);

  // Powers the "no face detected" fallback panel: every registered
  // employee with their live working status, so the identity panel
  // never shows an empty state.
  usePolling(() => listEmployees().then(setEmployees).catch(() => {}), 3000);
  usePolling(() => getOpenSessions().then(setOpenSessions).catch(() => {}), 1000);

  const faceDetected = Boolean(identity?.detected);

  return (
    <section className="page-view active-view">
      <div className="page-header">
        <div>
          <h1>Dashboard Overview</h1>
          <p>Real-time office monitoring and analytics</p>
        </div>
        <div className="header-meta">
          <div className="meta-pill">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <rect x="3" y="4" width="18" height="18" rx="2" />
              <line x1="16" y1="2" x2="16" y2="6" />
              <line x1="8" y1="2" x2="8" y2="6" />
              <line x1="3" y1="10" x2="21" y2="10" />
            </svg>
            <span>{now.toLocaleDateString("en-US", { day: "2-digit", month: "short", year: "numeric" })}</span>
          </div>
          <div className="meta-pill">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            <span>{now.toLocaleTimeString("en-US", { hour12: true })}</span>
          </div>
        </div>
      </div>

      <MetricCards summary={summary} />

      <div className="overview-grid">
        <div className="panel">
          <div className="panel-header">
            <h3>Live CCTV Feed - Main Entrance</h3>
            <span className="live-tag">
              <span className="dot"></span>Live
            </span>
          </div>
          <CameraFeed cameraAvailable={cameraAvailable} />
        </div>

        {faceDetected ? (
          <IdentityPanel data={identity} />
        ) : (
          <EmployeeStatusGrid employees={employees} openSessions={openSessions} />
        )}
      </div>

      <ActivityLog items={activity} onViewAll={() => onNavigate("reports")} />
    </section>
  );
}
