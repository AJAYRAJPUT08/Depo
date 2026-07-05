"""
Attendance Engine
-----------------
This is the core business logic of the AI Employee Time Tracking +
Payment System. It owns:

  - Debounced entry/exit detection from raw per-frame face recognitions
  - Open attendance sessions (employee currently inside, with entry time)
  - Closed attendance records (entry, exit, duration, payment) persisted
    to disk so Reports / Payment Logs survive a restart
  - The "currently identified employee" live panel shown on Overview
  - The real-time activity log feed

Architecturally this replaces the old project's state.py, but reuses
its thread-safe singleton + debounce pattern.
"""
import os
import json
import threading
import time
import uuid
from datetime import datetime

try:
    from .employees import employee_store
except ImportError:
    from employees import employee_store


class AttendanceEngine:

    def __init__(self, data_dir=None):
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = data_dir or os.environ.get("DATA_DIR") or os.path.abspath(os.path.join(backend_dir, "..", "data"))
        os.makedirs(self.data_dir, exist_ok=True)
        self.records_path = os.path.join(self.data_dir, "attendance_records.json")

        self._lock = threading.RLock()

        # employee_id -> { entry_time: epoch, entry_time_str }
        self._open_sessions = {}

        # closed records, most recent first
        self._records = []

        # live "currently detected" panel state
        self.current_employee_id = None
        self.current_confidence = 0
        self.current_is_known = False

        # activity log, most recent first
        self.activity_log = []
        self._activity_max_len = 100

        # debounce bookkeeping per employee so a flickery detection
        # doesn't cause repeated entry/exit toggles
        self._last_seen_at = {}          # employee_id -> epoch of last frame seen
        self._last_unknown_seen_at = 0
        self._no_face_since = None

        # how long an employee must be continuously absent from frame
        # before we consider it an EXIT (avoids false exits from a
        # person briefly turning their head, walking out of frame edge, etc.)
        # (after ENTRY) walked into the office. This does NOT end their
        # session — it arms the "away" flag so their NEXT detection is
        # treated as EXIT rather than a duplicate entry.
        self.EXIT_GRACE_SECONDS = 6

        # --------------------
        # DEMO TIME SIMULATION
        # --------------------
        # Short demo/test clips (a person on camera for a few seconds)
        # produce a real entry->exit gap of a few seconds, which is not
        # a realistic office session. When DEMO_MODE is on, the *real*
        # wall-clock gap between entry and exit is scaled up into a
        # simulated office duration before it's used for the dashboard
        # timer, activity log, records and payment calculation.
        #
        # DEMO_SECONDS_PER_REAL_SECOND controls the scale. Per the current
        # rule, 1 real second = 1 virtual minute = 60 simulated seconds,
        # so a 120-second real session is reported/paid as 120 minutes
        # (2 hours) worked. Detection/entry/exit logic itself is untouched
        # and still runs on real time — only the reported duration/payment
        # is simulated.
        #
        # Turn this off for a real production deployment (real CCTV,
        # real shifts) by setting DEMO_MODE=false in the environment,
        # which restores raw entry->exit duration.
        self.DEMO_MODE = os.environ.get("DEMO_MODE", "true").strip().lower() != "false"
        try:
            self.DEMO_SECONDS_PER_REAL_SECOND = float(os.environ.get("DEMO_SECONDS_PER_REAL_SECOND", 60))
        except (TypeError, ValueError):
            self.DEMO_SECONDS_PER_REAL_SECOND = 60.0

        # minimum time between a logged entry and treating a later
        # detection as a fresh re-entry (avoids duplicate entries from jitter).
        # This is checked against the RAW (real, unscaled) gap so it still
        # correctly filters out single-frame flicker even though the
        # reported/simulated duration is scaled up for the demo.
        self.MIN_SESSION_SECONDS = 0.4 if self.DEMO_MODE else 3

        # after an EXIT is detected, the same person's face is often
        # still visible in the next few frames (they haven't physically
        # left the camera's view yet), which would otherwise be picked
        # up as an instant fresh ENTRY. Ignore re-detections of the same
        # employee for EXIT_COOLDOWN_SECONDS (real/wall-clock time) after
        # their EXIT before allowing them to be recognized again.
        self.EXIT_COOLDOWN_SECONDS = 60
        # employee_id -> epoch time of their last EXIT
        self._last_exit_at = {}

        self._load_records()

    # --------------------
    # demo time simulation helper
    # --------------------

    def _simulate_duration(self, raw_seconds):
        """Scales a raw (real) elapsed-seconds value into the reported
        demo duration, if DEMO_MODE is on. No-op otherwise."""
        raw_seconds = max(0, raw_seconds)
        if self.DEMO_MODE:
            return raw_seconds * self.DEMO_SECONDS_PER_REAL_SECOND
        return raw_seconds

    # --------------------
    # persistence
    # --------------------

    def _load_records(self):
        with self._lock:
            if os.path.exists(self.records_path):
                try:
                    with open(self.records_path, "r") as f:
                        self._records = json.load(f)
                except Exception as e:
                    print(f"[AttendanceEngine] failed to load attendance_records.json: {e}")
                    self._records = []

    def _save_records(self):
        with self._lock:
            try:
                with open(self.records_path, "w") as f:
                    json.dump(self._records, f, indent=2)
            except Exception as e:
                print(f"[AttendanceEngine] failed to save attendance_records.json: {e}")

    # --------------------
    # detection ingestion (called every frame by recognition.py)
    # --------------------

    def register_detection(self, employee_id, confidence, is_known):
        with self._lock:
            now = time.time()

            # cooldown: this employee just EXITED — ignore this same
            # face/identity entirely until EXIT_COOLDOWN_SECONDS has
            # passed, so the still-visible face doesn't get reprocessed
            # or trigger an instant re-ENTRY.
            if is_known and employee_id:
                last_exit = self._last_exit_at.get(employee_id)
                if last_exit is not None and (now - last_exit) < self.EXIT_COOLDOWN_SECONDS:
                    self.current_employee_id = None
                    self.current_confidence = 0
                    self.current_is_known = False
                    return

            self.current_employee_id = employee_id
            self.current_confidence = int(confidence)
            self.current_is_known = is_known

            if is_known and employee_id:
                self._last_seen_at[employee_id] = now
                self._no_face_since = None

                session = self._open_sessions.get(employee_id)

                if session is None:
                    # Not currently tracked at all -> this is a fresh ENTRY.
                    self._start_session(employee_id, now)
                elif session.get("away"):
                    # Employee had left the camera's view after entering
                    # (i.e. walked into the office) and has now reappeared
                    # in front of the camera -> this is the EXIT.
                    # The internal timer kept running the whole time they
                    # were away, so duration = now - entry_time.
                    self._end_session(employee_id, now)
                else:
                    # Still being seen continuously as part of the same
                    # entry event (walking up to / through the door). Not
                    # a new entry and not an exit yet — do nothing.
                    pass
            else:
                self._last_unknown_seen_at = now

    def clear_current_detection(self):
        """Called every frame where no face is detected at all."""
        with self._lock:
            now = time.time()
            if self._no_face_since is None:
                self._no_face_since = now

            self.current_employee_id = None
            self.current_confidence = 0
            self.current_is_known = False

            # An employee who has been continuously out of frame for
            # EXIT_GRACE_SECONDS after their entry is assumed to have
            # walked into the office. This does NOT end their session or
            # stop their timer — it only flips a flag so that the NEXT
            # time their face is seen again, register_detection() knows
            # to treat that reappearance as the EXIT event instead of
            # mistaking it for a second entry. The timer keeps running
            # internally the whole time they're away from the camera.
            for employee_id, session in self._open_sessions.items():
                if session.get("away"):
                    continue
                last_seen = self._last_seen_at.get(employee_id, 0)
                if now - last_seen >= self.EXIT_GRACE_SECONDS:
                    session["away"] = True
                    emp = employee_store.get_employee(employee_id)
                    if emp:
                        print(f"[Attendance] {emp['name']} left the camera view — "
                              f"timer keeps running (inside office)")

    # --------------------
    # session lifecycle
    # --------------------

    def _start_session(self, employee_id, now):
        emp = employee_store.get_employee(employee_id)
        if not emp:
            return

        self._open_sessions[employee_id] = {
            "entry_time": now,
            "entry_time_str": datetime.now().strftime("%I:%M:%S %p"),
            # becomes True once the employee has been continuously out of
            # frame for EXIT_GRACE_SECONDS (i.e. they've walked into the
            # office). Only once this is True does the next face-detection
            # for this employee count as an EXIT — see register_detection().
            "away": False,
        }
        employee_store.set_status(employee_id, "INSIDE")

        self._log_activity(emp["name"], "ENTRY", datetime.now().strftime("%I:%M:%S %p"))
        print(f"[Attendance] {emp['name']} ENTERED at {self._open_sessions[employee_id]['entry_time_str']}")

    def _end_session(self, employee_id, now):
        session = self._open_sessions.pop(employee_id, None)
        if not session:
            return

        # start the re-entry cooldown for this employee, regardless of
        # whether this turns out to be a valid or too-short session
        self._last_exit_at[employee_id] = now

        raw_duration_seconds = max(0, now - session["entry_time"])

        # Ignore sessions shorter than MIN_SESSION_SECONDS (checked
        # against RAW/real elapsed time) — almost certainly a false
        # trigger (single-frame flicker), not a real entry/exit.
        if raw_duration_seconds < self.MIN_SESSION_SECONDS:
            employee_store.set_status(employee_id, "OUTSIDE")
            return

        emp = employee_store.get_employee(employee_id)
        if not emp:
            employee_store.set_status(employee_id, "OUTSIDE")
            return

        # DEMO TIME SIMULATION: report/pay based on the simulated
        # duration, not the raw real-time gap (see __init__ for the scale).
        duration_seconds = self._simulate_duration(raw_duration_seconds)

        hourly_rate = float(emp.get("hourly_rate", 0))
        hours = duration_seconds / 3600.0
        payment = round(hours * hourly_rate, 2)

        exit_time_str = datetime.now().strftime("%I:%M:%S %p")

        record = {
            "id": uuid.uuid4().hex[:12],
            "employee_id": employee_id,
            "employee_name": emp["name"],
            "date": datetime.now().strftime("%Y-%m-%d"),
            "entry_time": session["entry_time_str"],
            "exit_time": exit_time_str,
            "duration_seconds": int(duration_seconds),
            "duration_str": self._format_duration(duration_seconds),
            "hourly_rate": hourly_rate,
            "payment": payment,
            "logged_at": time.time(),
        }

        with self._lock:
            self._records.insert(0, record)
            self._save_records()

        employee_store.set_status(employee_id, "OUTSIDE")
        self._log_activity(emp["name"], "EXIT", exit_time_str, payment=payment, duration_str=record["duration_str"])
        print(f"[Attendance] {emp['name']} EXITED at {exit_time_str} — duration {record['duration_str']}, payment ₹{payment}")

    def _format_duration(self, seconds):
        seconds = int(seconds)
        h = seconds // 3600
        m = (seconds % 3600) // 60
        s = seconds % 60
        if h > 0:
            return f"{h}h {m}m {s}s"
        if m > 0:
            return f"{m}m {s}s"
        return f"{s}s"

    # --------------------
    # activity log
    # --------------------

    def _log_activity(self, employee_name, event_type, time_str, payment=None, duration_str=None):
        entry = {
            "employee_name": employee_name,
            "event_type": event_type,  # ENTRY | EXIT
            "time": time_str,
            "payment": payment,
            "duration_str": duration_str,
        }
        self.activity_log.insert(0, entry)
        if len(self.activity_log) > self._activity_max_len:
            self.activity_log = self.activity_log[:self._activity_max_len]

    # --------------------
    # live dashboard status
    # --------------------

    def get_current_employee_panel(self):
        """Returns the data for the 'Identified Employee' card on Overview."""
        with self._lock:
            if not self.current_is_known or not self.current_employee_id:
                return {
                    "detected": False,
                    "name": "No employee detected",
                    "status": "OUTSIDE",
                    "photo_url": None,
                    "entry_time": None,
                    "duration_str": None,
                    "duration_seconds": 0,
                    "hourly_rate": 0,
                    "current_payment": 0,
                }

            emp = employee_store.get_employee(self.current_employee_id)
            if not emp:
                return {
                    "detected": False,
                    "name": "No employee detected",
                    "status": "OUTSIDE",
                    "photo_url": None,
                    "entry_time": None,
                    "duration_str": None,
                    "duration_seconds": 0,
                    "hourly_rate": 0,
                    "current_payment": 0,
                }

            session = self._open_sessions.get(self.current_employee_id)
            now = time.time()

            if session:
                duration_seconds = self._simulate_duration(now - session["entry_time"])
                hours = duration_seconds / 3600.0
                current_payment = round(hours * float(emp.get("hourly_rate", 0)), 2)
                entry_time_str = session["entry_time_str"]
            else:
                duration_seconds = 0
                current_payment = 0
                entry_time_str = None

            photo_url = f"/photo/{emp['photo_filename']}" if emp.get("photo_filename") else None

            return {
                "detected": True,
                "employee_id": emp["id"],
                "name": emp["name"],
                "status": emp.get("status", "OUTSIDE"),
                "photo_url": photo_url,
                "entry_time": entry_time_str,
                "duration_str": self._format_duration(duration_seconds),
                "duration_seconds": int(duration_seconds),
                "hourly_rate": emp.get("hourly_rate", 0),
                "current_payment": current_payment,
                "confidence": self.current_confidence,
            }

    def get_dashboard_summary(self):
        """Top metric cards: total employees, currently inside, total hours today, total payment today."""
        with self._lock:
            today = datetime.now().strftime("%Y-%m-%d")
            today_records = [r for r in self._records if r["date"] == today]

            total_seconds_today = sum(r["duration_seconds"] for r in today_records)
            total_payment_today = sum(r["payment"] for r in today_records)

            # include ongoing open sessions in "hours worked today"
            # (simulated duration, same as the rest of the demo)
            now = time.time()
            for employee_id, session in self._open_sessions.items():
                open_duration = self._simulate_duration(now - session["entry_time"])
                total_seconds_today += open_duration
                emp = employee_store.get_employee(employee_id)
                if emp:
                    hours = open_duration / 3600.0
                    total_payment_today += hours * float(emp.get("hourly_rate", 0))

            return {
                "total_employees": employee_store.count(),
                "currently_inside": employee_store.count_inside(),
                "total_hours_today": round(total_seconds_today / 3600.0, 1),
                "total_payment_today": round(total_payment_today, 2),
            }

    def get_activity_log(self, limit=50):
        with self._lock:
            return self.activity_log[:limit]

    def get_records(self, employee_id=None, date=None, limit=200):
        with self._lock:
            records = self._records
            if employee_id:
                records = [r for r in records if r["employee_id"] == employee_id]
            if date:
                records = [r for r in records if r["date"] == date]
            return records[:limit]

    def get_open_sessions(self):
        with self._lock:
            result = []
            now = time.time()
            for employee_id, session in self._open_sessions.items():
                emp = employee_store.get_employee(employee_id)
                if not emp:
                    continue
                duration = self._simulate_duration(now - session["entry_time"])
                result.append({
                    "employee_id": employee_id,
                    "employee_name": emp["name"],
                    "entry_time": session["entry_time_str"],
                    "duration_str": self._format_duration(duration),
                    "hourly_rate": emp.get("hourly_rate", 0),
                    "current_payment": round((duration / 3600.0) * float(emp.get("hourly_rate", 0)), 2),
                })
            return result


# global singleton
attendance_engine = AttendanceEngine()
