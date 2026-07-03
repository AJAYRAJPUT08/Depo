"""
Face Recognition Engine (InsightFace)
--------------------------------------
Upgraded from the original OpenCV Haar-cascade + LBPH engine to
InsightFace (SCRFD detector + ArcFace-style embedding model, run
through ONNXRuntime). This gives much stronger recognition accuracy
and is faster / lighter than DeepFace, especially on CPU-only
("low hardware") machines.

Public interface is UNCHANGED from the old engine, so nothing else in
the project has to change:
    - get_recognizer()
    - recognizer.process_frame(frame)
    - recognizer.load_known_faces()
    - recognizer.save_unknown(...)

app.py, attendance.py, employees.py and the whole frontend keep
working exactly as before.

Performance / low-hardware strategy:
    1. Detection input size is capped (FACE_DET_SIZE, default 320px)
       instead of running the detector on the full-res frame.
    2. Recognition (detect + embed + match) only runs once every
       FACE_PROCESS_EVERY_N_FRAMES frames (default 3). On the frames
       in between, we simply redraw the last known boxes/labels, so
       the video still looks smooth with no visible stutter while
       skipping the expensive inference most of the time.
    3. Optional extra downscale (FACE_FRAME_SCALE, default 1.0) for
       very weak hardware — the whole frame is shrunk before being
       handed to InsightFace and boxes are scaled back up for drawing.
    4. Uses the small/fast InsightFace model pack ("buffalo_s") by
       default instead of the large one. Override with FACE_MODEL_PACK
       if more accuracy is needed and the hardware can take it.
"""
import os
import time
import threading
import numpy as np
import cv2
from datetime import datetime

from insightface.app import FaceAnalysis

from employees import employee_store
from attendance import attendance_engine


def _env_int(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _env_float(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class FaceRecognitionEngine:

    def __init__(self, photos_dir=None, unknown_dir=None):
        backend_dir = os.path.dirname(os.path.abspath(__file__))

        self.photos_dir = photos_dir or os.environ.get("PHOTOS_DIR") or os.path.abspath(
            os.path.join(backend_dir, "..", "employee_photos")
        )
        self.unknown_dir = unknown_dir or os.environ.get("UNKNOWN_DIR") or os.path.abspath(
            os.path.join(backend_dir, "..", "unknown_faces")
        )

        os.makedirs(self.photos_dir, exist_ok=True)
        os.makedirs(self.unknown_dir, exist_ok=True)

        # ---------------- tunables (env-overridable) ----------------
        # Small/fast pack by default -> good fit for low-end CPUs.
        model_pack = os.environ.get("FACE_MODEL_PACK", "buffalo_s")
        det_size = _env_int("FACE_DET_SIZE", 320)
        # -1 = CPU (onnxruntime CPUExecutionProvider). Set to 0 for GPU.
        ctx_id = _env_int("FACE_CTX_ID", -1)

        # Cosine-similarity thresholds (embeddings are unit vectors,
        # so higher = more similar). ArcFace-style embeddings from
        # InsightFace typically separate genuine/impostor pairs well
        # above ~0.35-0.40.
        self.MATCH_THRESHOLD = _env_float("FACE_MATCH_THRESHOLD", 0.38)
        self.LOCK_THRESHOLD = _env_float("FACE_LOCK_THRESHOLD", 0.30)
        self.LOCK_SECONDS = _env_float("FACE_LOCK_SECONDS", 5)

        # Only run full detection+recognition every Nth frame.
        self.PROCESS_EVERY_N_FRAMES = max(1, _env_int("FACE_PROCESS_EVERY_N_FRAMES", 3))

        # Optional extra downscale of the frame before inference
        # (1.0 = off). e.g. 0.6 -> run inference on 60% size frame.
        self.FRAME_SCALE = min(1.0, max(0.2, _env_float("FACE_FRAME_SCALE", 1.0)))

        providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] if ctx_id >= 0 else ["CPUExecutionProvider"]

        print(f"[AI Office Analytics] loading InsightFace model pack '{model_pack}' "
              f"(det_size={det_size}, ctx_id={ctx_id}, frame_scale={self.FRAME_SCALE}) ...")
        self.app = FaceAnalysis(name=model_pack, providers=providers)
        self.app.prepare(ctx_id=ctx_id, det_size=(det_size, det_size))
        print("[AI Office Analytics] InsightFace ready")

        # employee_id gallery: parallel arrays for fast vectorized matching
        self.known_ids = []
        self.known_embeddings = None  # np.ndarray [N, 512], unit-normalized rows
        self.is_trained = False
        self._train_lock = threading.RLock()

        self.last_unknown_save = 0

        # Bounded "lock-in" memory so a verified identity doesn't flicker
        # to UNKNOWN for a couple of noisy/skipped frames in a row.
        self._locked_employee_id = None
        self._lock_started_at = 0

        # Cache of the last recognition pass, redrawn on skipped frames
        # so the stream still looks continuous without re-running inference.
        self._frame_counter = 0
        self._last_results = []  # list of {"box": (x1,y1,x2,y2), "color": ..., "label": ...}

        self.load_known_faces()

    # --------------------
    # (re)build embedding gallery from employee_store enrollment photos
    # --------------------

    def load_known_faces(self):
        """
        Builds the face-embedding gallery from every enrollment photo
        registered in employee_store. Called at startup and again any
        time an employee is added/updated/removed so the camera
        recognizes them immediately.
        """
        with self._train_lock:
            ids = []
            embeddings = []

            employees = employee_store.list_employees()
            for emp in employees:
                photo_path = (
                    os.path.join(self.photos_dir, emp["photo_filename"])
                    if emp.get("photo_filename") else None
                )
                if not photo_path or not os.path.exists(photo_path):
                    continue

                img = cv2.imread(photo_path)
                if img is None:
                    continue

                faces = self.app.get(img)
                if not faces:
                    print(f"[AI Office Analytics] no face detected in enrollment photo "
                          f"for '{emp['name']}', skipping")
                    continue

                # If the enrollment photo has more than one face, use the
                # largest one (closest to camera / most likely the subject).
                face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
                emb = face.normed_embedding.astype(np.float32)

                ids.append(emp["id"])
                embeddings.append(emb)

            if embeddings:
                self.known_ids = ids
                self.known_embeddings = np.vstack(embeddings)
                self.is_trained = True
            else:
                self.known_ids = []
                self.known_embeddings = None
                self.is_trained = False

            print(f"[AI Office Analytics] face gallery built for {len(self.known_ids)} employee(s)")

    # --------------------
    # save unknown face capture
    # --------------------

    def save_unknown(self, frame, x, y, w, h):
        now = time.time()
        if now - self.last_unknown_save < 5:
            return ""
        self.last_unknown_save = now

        filename = "unknown_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg"
        path = os.path.join(self.unknown_dir, filename)

        crop = frame[
            max(0, y - 20):min(frame.shape[0], y + h + 20),
            max(0, x - 20):min(frame.shape[1], x + w + 20)
        ]
        if crop.size > 0:
            cv2.imwrite(path, crop)
        return "/unknown_photo/" + filename

    # --------------------
    # embedding matching (cosine similarity — embeddings are unit vectors)
    # --------------------

    def recognize_face(self, embedding):
        """Returns (employee_id_or_None, confidence, is_known) for a single face embedding."""
        if not self.is_trained or self.known_embeddings is None:
            return None, 0, False

        sims = self.known_embeddings @ embedding
        best_idx = int(np.argmax(sims))
        best_sim = float(sims[best_idx])
        employee_id = self.known_ids[best_idx]

        now = time.time()

        if best_sim >= self.MATCH_THRESHOLD:
            confidence = int(min(99, max(60, best_sim * 100)))
            self._locked_employee_id = employee_id
            self._lock_started_at = now
            return employee_id, confidence, True

        lock_active = (
            self._locked_employee_id is not None
            and (now - self._lock_started_at) <= self.LOCK_SECONDS
        )

        if best_sim >= self.LOCK_THRESHOLD and lock_active and employee_id == self._locked_employee_id:
            confidence = int(min(70, max(45, best_sim * 100)))
            return employee_id, confidence, True

        return None, int(max(0, best_sim * 100)), False

    # --------------------
    # process a single video frame: detect (every Nth frame), recognize, draw, log attendance
    # --------------------

    def process_frame(self, frame):
        self._frame_counter += 1
        run_recognition = (self._frame_counter % self.PROCESS_EVERY_N_FRAMES == 0)

        if run_recognition:
            if self.FRAME_SCALE < 1.0:
                small = cv2.resize(frame, None, fx=self.FRAME_SCALE, fy=self.FRAME_SCALE,
                                    interpolation=cv2.INTER_LINEAR)
                inv_scale = 1.0 / self.FRAME_SCALE
            else:
                small = frame
                inv_scale = 1.0

            faces = self.app.get(small)

            if not faces:
                attendance_engine.clear_current_detection()
                self._last_results = []
            else:
                results = []
                for face in faces:
                    x1, y1, x2, y2 = [v * inv_scale for v in face.bbox]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(frame.shape[1] - 1, x2), min(frame.shape[0] - 1, y2)
                    w, h = x2 - x1, y2 - y1

                    emb = face.normed_embedding.astype(np.float32)
                    employee_id, conf, is_known = self.recognize_face(emb)

                    if is_known:
                        color = (0, 200, 90)
                        emp = employee_store.get_employee(employee_id)
                        label = f"{emp['name']} ({conf}%)" if emp else f"Employee ({conf}%)"
                        attendance_engine.register_detection(employee_id, conf, True)
                    else:
                        color = (40, 40, 255)
                        self.save_unknown(frame, x1, y1, w, h)
                        label = f"Unrecognized ({conf}%)"
                        attendance_engine.register_detection(None, conf, False)

                    results.append({"box": (x1, y1, x2, y2), "color": color, "label": label})

                self._last_results = results

        # Draw the cached (or freshly computed) results every frame, so
        # the stream still looks smooth on frames we skipped inference on.
        for r in self._last_results:
            x1, y1, x2, y2 = r["box"]
            cv2.rectangle(frame, (x1, y1), (x2, y2), r["color"], 2)
            cv2.putText(frame, r["label"], (x1, max(20, y1 - 10)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, r["color"], 2)

        return frame


# singleton
recognizer_engine = None


def get_recognizer():
    global recognizer_engine
    if recognizer_engine is None:
        recognizer_engine = FaceRecognitionEngine()
    return recognizer_engine
