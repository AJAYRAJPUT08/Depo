import { useEffect, useState } from "react";
import { deleteEmployee, listEmployees, saveEmployee } from "../lib/api";
import { useToast } from "../lib/ToastContext";
import EmployeeCard from "../components/EmployeeCard";
import EmployeeModal from "../components/EmployeeModal";

export default function EmployeesPage({ onEmployeesChanged }) {
  const [employees, setEmployees] = useState([]);
  const [loaded, setLoaded] = useState(false);
  const [modalEmployee, setModalEmployee] = useState(undefined); // undefined = closed, null = add, {} = edit
  const showToast = useToast();

  async function refresh() {
    try {
      const data = await listEmployees();
      setEmployees(data);
      setLoaded(true);
      onEmployeesChanged?.(data);
    } catch (e) {
      showToast("Could not load employees. Check backend connection.", "error");
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleSave({ id, name, hourlyRate, photoFile }) {
    try {
      await saveEmployee({ id, name, hourlyRate, photoFile });
      showToast(id ? "Employee updated." : "Employee added.", "success");
      setModalEmployee(undefined);
      refresh();
    } catch (err) {
      showToast(err.message || "Failed to save employee.", "error");
    }
  }

  async function handleDelete(employee) {
    if (!window.confirm(`Remove ${employee.name} from the system? Their past attendance records will be kept.`)) {
      return;
    }
    try {
      await deleteEmployee(employee.id);
      showToast("Employee removed.", "success");
      refresh();
    } catch (err) {
      showToast(err.message || "Failed to delete employee.", "error");
    }
  }

  return (
    <section className="page-view active-view">
      <div className="page-header">
        <div>
          <h1>Employee Tracking</h1>
          <p>Manage registered employees and their hourly rates</p>
        </div>
      </div>

      <div className="toolbar">
        <span className="metric-sub">
          {employees.length} employee{employees.length === 1 ? "" : "s"} registered
        </span>
        <button className="btn-primary" onClick={() => setModalEmployee(null)}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          Add Employee
        </button>
      </div>

      <div className="employee-grid">
        {loaded && employees.length === 0 ? (
          <div className="empty-state" style={{ gridColumn: "1/-1" }}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
              <circle cx="9" cy="7" r="4" />
              <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
              <path d="M16 3.13a4 4 0 0 1 0 7.75" />
            </svg>
            <p>No employees registered yet. Click "Add Employee" to enroll your first employee.</p>
          </div>
        ) : (
          employees.map((emp) => (
            <EmployeeCard key={emp.id} employee={emp} onEdit={setModalEmployee} onDelete={handleDelete} />
          ))
        )}
      </div>

      {modalEmployee !== undefined && (
        <EmployeeModal employee={modalEmployee} onClose={() => setModalEmployee(undefined)} onSave={handleSave} />
      )}
    </section>
  );
}
