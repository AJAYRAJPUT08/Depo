import os
import cv2
import time
import numpy as np
from flask import Flask, Response, jsonify, send_file, request
from flask_cors import CORS

from employees import employee_store
from attendance import attendance_engine
from recognition import get_recognizer

# Initialize Flask App.
# frontend/ now holds the built React dashboard (see frontend_react/,
# built via `npm run build`, output configured to land here). Flask
# serves it as static files: static_url_path="" means any built asset
# (e.g. /assets/index-XXXX.js) is served directly from its real path,
# while our own explicit API/video/photo routes below still take
# precedence over same-named static files.
app = Flask(__name__, static_folder="../frontend", static_url_path="")

# --------------------------------------------------------------
# CORS
# --------------------------------------------------------------
# When the React frontend is deployed separately from this backend
# (e.g. frontend on Vercel, backend on Render/Railway), browser
# requests to /api/*, /video, /photo/*, etc. are cross-origin, so the
# backend must explicitly allow them. Set FRONTEND_ORIGIN to the
# deployed frontend's exact origin (e.g. https://my-app.vercel.app)
# in production; it defaults to "*" so local/dev setups keep working
# with zero configuration.
FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "*")
CORS(app, resources={r"/*": {"origins": FRONTEND_ORIGIN}}, supports_credentials=False)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PHOTOS_DIR = os.path.abspath(os.path.join(BASE_DIR, "../employee_photos"))
UNKNOWN_DIR = os.path.abspath(os.path.join(BASE_DIR, "../unknown_faces"))
FRONTEND_DIR = os.path.abspath(os.path.join(BASE_DIR, "../frontend"))

os.makedirs(PHOTOS_DIR, exist_ok=True)
os.makedirs(UNKNOWN_DIR, exist_ok=True)


class CameraStream:
    """
    Continuous live video streaming generator.
    Reused from the original project's camera architecture: tries the
    real hardware webcam (CCTV/USB feed) first, on either source 0 or 1.
    If no physical camera is available, the frontend falls back to a
    temporary demo video clip (handled client-side) instead of faking
    a backend feed.
    """
    def __init__(self, camera_src=0):
        self.camera_src = camera_src
        self.cap = None
        self.init_camera()

    def init_camera(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_src)
            if self.cap.isOpened():
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                print(f"[AI Office Analytics] Camera connected on source {self.camera_src}")
            else:
                self.cap = cv2.VideoCapture(1)
                if self.cap.isOpened():
                    self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                    self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                    self.cap.set(cv2.CAP_PROP_FPS, 30)
                    print("[AI Office Analytics] Camera connected on source 1")
                else:
                    print("[AI Office Analytics] No physical camera detected. /video will report unavailable; "
                          "the dashboard will use a temporary demo feed instead.")
        except Exception as e:
            print(f"[AI Office Analytics] Camera initialization error: {e}")

    def is_available(self):
        return self.cap is not None and self.cap.isOpened()

    def generate_frames(self):
        recognizer = get_recognizer()
        while True:
            frame = None
            if self.cap and self.cap.isOpened():
                ret, img = self.cap.read()
                if ret and img is not None:
                    frame = cv2.flip(img, 1)

            if frame is None:
                frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                cv2.putText(frame, "NO CCTV CAMERA DETECTED", (350, 350),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (60, 60, 220), 2)
                cv2.putText(frame, "Connect a camera and restart the backend", (300, 395),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (60, 60, 220), 2)
                time.sleep(1)

            processed_frame = recognizer.process_frame(frame)

            ret, buffer = cv2.imencode('.jpg', processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
            if ret:
                frame_bytes = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')


camera_stream = CameraStream()

# Initialize the recognition engine eagerly (not lazily inside the
# generator) so employee counts / training status are correct from the
# very first dashboard load, even before anyone opens /video.
get_recognizer()

# ==========================================
# PAGE / STATIC ROUTES
# ==========================================

@app.route("/")
def index():
    return send_file(os.path.join(FRONTEND_DIR, "index.html"))

@app.route("/video")
def video():
    if not camera_stream.is_available():
        return jsonify({"error": "no_camera"}), 503
    return Response(camera_stream.generate_frames(),
                     mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route("/camera_status")
def camera_status():
    # "available" historically meant "server has a physical webcam"
    # (CameraStream / the /video MJPEG route below). Browser-based
    # capture (/api/detect_frame) works independently of this and is
    # always available as long as the visitor's own device has a
    # camera, which the frontend checks for itself via getUserMedia.
    return jsonify({"available": camera_stream.is_available(), "browser_capture": True})

@app.route("/api/detect_frame", methods=["POST"])
def api_detect_frame():
    """
    Browser-based camera pipeline (works after deployment, unlike the
    old /video route which needs a webcam physically attached to the
    server). The frontend captures a frame from the visitor's own
    webcam via getUserMedia, draws it to a canvas, and POSTs it here
    as an image file (multipart field 'frame') roughly once a second.

    This reuses recognizer.process_frame() exactly as the legacy
    /video MJPEG loop does — same detection, same drawing, same
    attendance_engine.register_detection()/clear_current_detection()
    side effects — so entry/exit, time tracking and payment logic are
    completely unchanged. We just return the annotated JPEG back to
    the browser to display, instead of streaming it from a local cv2
    VideoCapture.
    """
    file = request.files.get("frame")
    if file is None:
        return jsonify({"error": "missing 'frame' file"}), 400

    file_bytes = np.frombuffer(file.read(), dtype=np.uint8)
    frame = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
    if frame is None:
        return jsonify({"error": "could not decode image"}), 400

    recognizer = get_recognizer()
    processed_frame = recognizer.process_frame(frame)

    ret, buffer = cv2.imencode(".jpg", processed_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not ret:
        return jsonify({"error": "could not encode result"}), 500

    return Response(buffer.tobytes(), mimetype="image/jpeg")

@app.route("/photo/<path:filename>")
def serve_employee_photo(filename):
    file_path = os.path.join(PHOTOS_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "", 404

@app.route("/unknown_photo/<path:filename>")
def serve_unknown_photo(filename):
    file_path = os.path.join(UNKNOWN_DIR, filename)
    if os.path.exists(file_path):
        return send_file(file_path)
    return "", 404

# ==========================================
# DASHBOARD / STATUS API
# ==========================================

@app.route("/api/dashboard_summary")
def api_dashboard_summary():
    return jsonify(attendance_engine.get_dashboard_summary())

@app.route("/api/current_employee")
def api_current_employee():
    return jsonify(attendance_engine.get_current_employee_panel())

@app.route("/api/activity_log")
def api_activity_log():
    limit = int(request.args.get("limit", 50))
    return jsonify(attendance_engine.get_activity_log(limit=limit))

@app.route("/api/open_sessions")
def api_open_sessions():
    return jsonify(attendance_engine.get_open_sessions())

# ==========================================
# EMPLOYEE MANAGEMENT API
# ==========================================

@app.route("/api/employees", methods=["GET"])
def api_list_employees():
    employees = employee_store.list_employees()
    for emp in employees:
        emp["photo_url"] = f"/photo/{emp['photo_filename']}" if emp.get("photo_filename") else None
    return jsonify(employees)

@app.route("/api/employees", methods=["POST"])
def api_add_employee():
    name = request.form.get("name", "").strip()
    hourly_rate = request.form.get("hourly_rate", "0").strip()
    photo = request.files.get("photo")

    if not name:
        return jsonify({"error": "Employee name is required"}), 400
    try:
        hourly_rate = float(hourly_rate)
        if hourly_rate < 0:
            raise ValueError
    except ValueError:
        return jsonify({"error": "Hourly rate must be a valid non-negative number"}), 400

    employee = employee_store.add_employee(name, hourly_rate, photo)

    # Retrain the recognizer so the new face is recognized immediately
    get_recognizer().load_known_faces()

    employee["photo_url"] = f"/photo/{employee['photo_filename']}" if employee.get("photo_filename") else None
    return jsonify(employee), 201

@app.route("/api/employees/<employee_id>", methods=["PUT"])
def api_update_employee(employee_id):
    name = request.form.get("name")
    hourly_rate = request.form.get("hourly_rate")
    photo = request.files.get("photo")

    if hourly_rate is not None:
        try:
            hourly_rate = float(hourly_rate)
        except ValueError:
            return jsonify({"error": "Hourly rate must be a valid number"}), 400

    employee = employee_store.update_employee(employee_id, name=name, hourly_rate=hourly_rate, photo_file_storage=photo)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    get_recognizer().load_known_faces()

    employee["photo_url"] = f"/photo/{employee['photo_filename']}" if employee.get("photo_filename") else None
    return jsonify(employee)

@app.route("/api/employees/<employee_id>", methods=["DELETE"])
def api_delete_employee(employee_id):
    employee = employee_store.delete_employee(employee_id)
    if not employee:
        return jsonify({"error": "Employee not found"}), 404

    get_recognizer().load_known_faces()
    return jsonify({"success": True})

# ==========================================
# REPORTS / PAYMENT LOGS API
# ==========================================

@app.route("/api/records")
def api_records():
    employee_id = request.args.get("employee_id")
    date = request.args.get("date")
    limit = int(request.args.get("limit", 200))
    return jsonify(attendance_engine.get_records(employee_id=employee_id, date=date, limit=limit))


if __name__ == "__main__":
    print("=========================================================")
    print("   AI Office Analytics — Employee Time & Payment Tracker")
    print("=========================================================")
    app.run(host="0.0.0.0", port=5000, threaded=True, debug=False, use_reloader=False)
