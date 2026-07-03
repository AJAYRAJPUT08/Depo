import { useState } from "react";
import { ToastProvider } from "./lib/ToastContext";
import { getCameraStatus, listEmployees } from "./lib/api";
import { usePolling } from "./lib/useClock";
import Sidebar from "./components/Sidebar";
import OverviewPage from "./pages/OverviewPage";
import CctvPage from "./pages/CctvPage";
import EmployeesPage from "./pages/EmployeesPage";
import PaymentsPage from "./pages/PaymentsPage";
import ReportsPage from "./pages/ReportsPage";
import SettingsPage from "./pages/SettingsPage";

function AppShell() {
  const [activePage, setActivePage] = useState("overview");
  const [cameraAvailable, setCameraAvailable] = useState(false);
  const [employees, setEmployees] = useState([]);

  // Camera availability is shared by the Overview + Live CCTV pages.
  usePolling(() => getCameraStatus().then((d) => setCameraAvailable(!!d.available)).catch(() => {}), 5000);

  // Employee list is shared by the Employees page and the Reports filter dropdown.
  usePolling(() => listEmployees().then(setEmployees).catch(() => {}), 5000);

  return (
    <div className="app-shell">
      <Sidebar activePage={activePage} onNavigate={setActivePage} cameraAvailable={cameraAvailable} />

      <main className="main-content">
        {activePage === "overview" && <OverviewPage cameraAvailable={cameraAvailable} onNavigate={setActivePage} />}
        {activePage === "cctv" && <CctvPage cameraAvailable={cameraAvailable} />}
        {activePage === "employees" && <EmployeesPage onEmployeesChanged={setEmployees} />}
        {activePage === "payments" && <PaymentsPage />}
        {activePage === "reports" && <ReportsPage employees={employees} />}
        {activePage === "settings" && <SettingsPage />}
      </main>
    </div>
  );
}

export default function App() {
  return (
    <ToastProvider>
      <AppShell />
    </ToastProvider>
  );
}
