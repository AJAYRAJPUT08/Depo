import { useEffect, useState } from "react";
import { getCameraStatus } from "../lib/api";

export default function SettingsPage() {
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [notifications, setNotifications] = useState(false);
  const [cameraStatus, setCameraStatus] = useState("Checking camera status…");

  async function checkCamera() {
    setCameraStatus("Checking camera status…");
    try {
      const data = await getCameraStatus();
      setCameraStatus(
        data.available
          ? "Connected — live CCTV feed is active"
          : "No physical camera detected — dashboard is showing a temporary demo feed"
      );
    } catch (e) {
      setCameraStatus("Could not reach backend to check camera status");
    }
  }

  useEffect(() => {
    checkCamera();
  }, []);

  return (
    <section className="page-view active-view">
      <div className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Configure system preferences</p>
        </div>
      </div>

      <div className="panel settings-section">
        <div className="panel-header">
          <h3>General</h3>
        </div>
        <div className="panel-body">
          <div className="settings-row">
            <div className="settings-row-label">
              <strong>Currency</strong>
              <span>Used for all payment calculations</span>
            </div>
            <select className="filter-select" defaultValue="INR">
              <option value="INR">₹ Indian Rupee (INR)</option>
              <option value="USD">$ US Dollar (USD)</option>
              <option value="EUR">€ Euro (EUR)</option>
            </select>
          </div>
          <div className="settings-row">
            <div className="settings-row-label">
              <strong>Auto-refresh dashboard</strong>
              <span>Poll backend for live updates every second</span>
            </div>
            <div className={`toggle${autoRefresh ? " on" : ""}`} onClick={() => setAutoRefresh((v) => !v)}></div>
          </div>
          <div className="settings-row">
            <div className="settings-row-label">
              <strong>Desktop notifications</strong>
              <span>Notify on every employee entry / exit</span>
            </div>
            <div className={`toggle${notifications ? " on" : ""}`} onClick={() => setNotifications((v) => !v)}></div>
          </div>
        </div>
      </div>

      <div className="panel settings-section">
        <div className="panel-header">
          <h3>Camera</h3>
        </div>
        <div className="panel-body">
          <div className="settings-row">
            <div className="settings-row-label">
              <strong>Camera source</strong>
              <span>{cameraStatus}</span>
            </div>
            <button className="btn-secondary" onClick={checkCamera}>
              Re-check
            </button>
          </div>
          <div className="settings-row">
            <div className="settings-row-label">
              <strong>Exit grace period</strong>
              <span>Seconds an employee can leave the frame before being treated as gone into the office</span>
            </div>
            <span className="cell-muted">6 seconds</span>
          </div>
        </div>
      </div>

      <div className="panel settings-section">
        <div className="panel-header">
          <h3>About</h3>
        </div>
        <div className="panel-body">
          <div className="settings-row">
            <div className="settings-row-label">
              <strong>AI Office Analytics</strong>
              <span>Smart Office Monitoring System — v1.0</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
