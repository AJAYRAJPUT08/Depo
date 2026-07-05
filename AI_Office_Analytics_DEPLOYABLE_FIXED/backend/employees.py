"""
Employee Store
--------------
Owns the list of registered employees (name, hourly rate, enrollment
photo). Persisted to a JSON file so employees survive a server restart.
No employee is hardcoded — every employee is added dynamically through
the /api/employees endpoint, which the Employees tab in the UI calls.
"""
import os
import json
import threading
import uuid
import time


class EmployeeStore:

    def __init__(self, data_dir=None, photos_dir=None):
        backend_dir = os.path.dirname(os.path.abspath(__file__))

        self.data_dir = data_dir or os.environ.get("DATA_DIR") or os.path.abspath(os.path.join(backend_dir, "..", "data"))
        self.photos_dir = photos_dir or os.environ.get("PHOTOS_DIR") or os.path.abspath(os.path.join(backend_dir, "..", "employee_photos"))
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.photos_dir, exist_ok=True)

        self.db_path = os.path.join(self.data_dir, "employees.json")
        self._lock = threading.RLock()
        self._employees = {}  # id -> dict

        self._load()

    # --------------------
    # persistence
    # --------------------

    def _load(self):
        with self._lock:
            if os.path.exists(self.db_path):
                try:
                    with open(self.db_path, "r") as f:
                        data = json.load(f)
                    self._employees = {e["id"]: e for e in data}
                except Exception as e:
                    print(f"[EmployeeStore] failed to load employees.json: {e}")
                    self._employees = {}
            else:
                self._employees = {}

    def _save(self):
        with self._lock:
            try:
                with open(self.db_path, "w") as f:
                    json.dump(list(self._employees.values()), f, indent=2)
            except Exception as e:
                print(f"[EmployeeStore] failed to save employees.json: {e}")

    # --------------------
    # CRUD
    # --------------------

    def list_employees(self):
        with self._lock:
            return sorted(self._employees.values(), key=lambda e: e["name"].lower())

    def get_employee(self, employee_id):
        with self._lock:
            return self._employees.get(employee_id)

    def add_employee(self, name, hourly_rate, photo_file_storage=None):
        """
        photo_file_storage: a Flask FileStorage object (request.files['photo'])
        or None if no photo supplied yet.
        """
        with self._lock:
            employee_id = uuid.uuid4().hex[:12]

            photo_filename = None
            if photo_file_storage is not None:
                ext = os.path.splitext(photo_file_storage.filename or "")[1].lower()
                if ext not in (".jpg", ".jpeg", ".png"):
                    ext = ".jpg"
                photo_filename = f"{employee_id}{ext}"
                save_path = os.path.join(self.photos_dir, photo_filename)
                photo_file_storage.save(save_path)

            employee = {
                "id": employee_id,
                "name": name.strip(),
                "hourly_rate": float(hourly_rate),
                "photo_filename": photo_filename,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "status": "OUTSIDE",  # OUTSIDE | INSIDE — maintained by attendance engine
            }
            self._employees[employee_id] = employee
            self._save()
            return employee

    def update_employee(self, employee_id, name=None, hourly_rate=None, photo_file_storage=None):
        with self._lock:
            emp = self._employees.get(employee_id)
            if not emp:
                return None

            if name is not None and name.strip():
                emp["name"] = name.strip()
            if hourly_rate is not None:
                emp["hourly_rate"] = float(hourly_rate)

            if photo_file_storage is not None:
                ext = os.path.splitext(photo_file_storage.filename or "")[1].lower()
                if ext not in (".jpg", ".jpeg", ".png"):
                    ext = ".jpg"
                # remove old photo file if it had a different name
                old_filename = emp.get("photo_filename")
                photo_filename = f"{employee_id}{ext}"
                save_path = os.path.join(self.photos_dir, photo_filename)
                photo_file_storage.save(save_path)
                if old_filename and old_filename != photo_filename:
                    old_path = os.path.join(self.photos_dir, old_filename)
                    if os.path.exists(old_path):
                        try:
                            os.remove(old_path)
                        except OSError:
                            pass
                emp["photo_filename"] = photo_filename

            self._save()
            return emp

    def delete_employee(self, employee_id):
        with self._lock:
            emp = self._employees.pop(employee_id, None)
            if emp and emp.get("photo_filename"):
                photo_path = os.path.join(self.photos_dir, emp["photo_filename"])
                if os.path.exists(photo_path):
                    try:
                        os.remove(photo_path)
                    except OSError:
                        pass
            self._save()
            return emp

    def set_status(self, employee_id, status):
        with self._lock:
            emp = self._employees.get(employee_id)
            if emp:
                emp["status"] = status
                self._save()

    def count(self):
        with self._lock:
            return len(self._employees)

    def count_inside(self):
        with self._lock:
            return sum(1 for e in self._employees.values() if e.get("status") == "INSIDE")


# global singleton
employee_store = EmployeeStore()
