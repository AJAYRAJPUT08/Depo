# AI Office Analytics — Employee Time Tracking + Payment System

Converted from the original VISION_AI face-recognition surveillance project
into a complete AI-powered employee time tracking and payment system, with
the UI rebuilt to match the approved "AI Office Analytics" dashboard design.

## Face recognition engine — upgraded to InsightFace

`backend/recognition.py` was rebuilt on InsightFace (SCRFD detector +
ArcFace-style embedding model, run via ONNXRuntime), replacing the old
OpenCV Haar-cascade + LBPH engine. This is a straight swap of the engine
internals only; every other file's contract stays identical:

- `get_recognizer()`, `process_frame()`, `load_known_faces()`,
  `save_unknown()` keep the same names, signatures, and call sites in
  `app.py` and `attendance.py`.
- Lock-in/debounce behaviour (a verified identity doesn't flicker to
  "Unrecognized" for a couple of noisy frames) is preserved, now driven by
  cosine similarity between embeddings instead of LBPH distance.
- Enrollment is unchanged from the employee's point of view — upload one
  clear photo per employee and the gallery embedding is built automatically.

Why InsightFace: it pairs a small SCRFD detector with an ArcFace-style
embedding model distributed as compact ONNX files, so it runs comfortably
on CPU-only machines and is noticeably lighter/faster than DeepFace, which
wraps much heavier backbones behind TensorFlow.

Real-time performance tuning, all via optional environment variables:

- `FACE_MODEL_PACK` (default `buffalo_s`) — InsightFace model pack.
  `buffalo_sc` is even lighter/faster with lower accuracy; `buffalo_l` is
  heavier and more accurate.
- `FACE_DET_SIZE` (default `320`) — detector input size in px. Lower is
  faster but shortens effective detection range.
- `FACE_PROCESS_EVERY_N_FRAMES` (default `3`) — only run detection and
  recognition every Nth frame; frames in between just redraw the last
  known box/label, so the stream still looks smooth without paying for
  inference on every single frame.
- `FACE_FRAME_SCALE` (default `1.0`) — extra downscale of the whole frame
  before inference on very low-end hardware, e.g. `0.6`. Boxes are scaled
  back up automatically for drawing.
- `FACE_MATCH_THRESHOLD` (default `0.38`) — cosine-similarity threshold to
  call it a confident match.
- `FACE_CTX_ID` (default `-1`) — `-1` means CPU. Set to `0` (and install
  `onnxruntime-gpu` instead of `onnxruntime`) if a NVIDIA GPU is available.

On low-end CPUs, start with the defaults; if the stream still feels
sluggish, raise `FACE_PROCESS_EVERY_N_FRAMES` to `4`-`6` and/or set
`FACE_FRAME_SCALE=0.6` to `0.75`.

First-run note: InsightFace downloads its model pack (a few MB, once) from
GitHub the first time it runs, so the very first backend start needs an
internet connection. After that it is cached in `~/.insightface/models/`
and startup is fully offline.

## What was reused from the old project

- **`backend/app.py`** — the Flask app structure, the `CameraStream` class
  (real hardware webcam / CCTV connection with graceful fallback), and the
  MJPEG `/video` streaming route are reused directly from the old project.
- **Photo serving, enrollment-by-upload pattern** — `/api/add_face` from the
  old project is now `/api/employees` (POST), same FileStorage-based upload
  pattern, now also storing an hourly rate.

## What's new

- **`backend/employees.py`** — dynamic, persistent employee store (JSON file
  on disk). Add / edit / delete employees from the UI; no employee is ever
  hardcoded. Each employee has a name, hourly rate, and enrollment photo.
- **`backend/attendance.py`** — the core time-tracking + payment engine. Turns
  raw per-frame face recognitions into debounced entry/exit events, tracks
  open sessions, computes `duration × hourly_rate = payment` on exit, and
  persists every completed session to `data/attendance_records.json` for the
  Reports and Payment Logs pages.
- **Frontend** — rebuilt as a React (Vite) single-page dashboard, replacing
  the previous plain HTML/CSS/vanilla-JS frontend. Same visual design
  (white, modern dashboard) and the same six tabs — Overview, Live CCTV,
  Employee Tracking, Payment Logs, Reports, and Settings — now implemented
  as React components in `frontend_react/src/`, calling the exact same
  Flask API. See "Frontend (React)" below for how to build/run it.

## Running it

```bash
cd backend
pip install -r ../requirements.txt
python app.py
```

Then open `http://localhost:5000`.

If no physical camera is detected, the backend reports this via
`/camera_status` and the dashboard automatically falls back to a temporary
demo video clip in the Live CCTV panel, exactly as requested, so the UI is
never blank during a demo. Once a real CCTV/webcam is connected and the
backend restarted, the live `/video` MJPEG stream takes over automatically.

## Frontend (React)

The dashboard lives in `frontend_react/` (Vite + React, plain CSS — no
UI framework). It builds directly into `frontend/`, which `backend/app.py`
serves as static files, so in production you only ever run the Flask
server — there's no separate frontend server or build step needed at
runtime.

**Production build** (do this whenever you change the React source):

```bash
cd frontend_react
npm install
npm run build
```

This writes `index.html` + hashed `assets/*.js` / `*.css` straight into
`../frontend/`, overwriting the previous build. Then just run the Flask
backend as usual (`python backend/app.py`) and open `http://localhost:5000`
— it now serves the freshly built dashboard.

**Local frontend dev with hot-reload** (optional, only for iterating on the
UI):

```bash
# terminal 1
cd backend && python app.py          # Flask API on :5000

# terminal 2
cd frontend_react && npm run dev     # Vite dev server on :5173
```

Open `http://localhost:5173` — Vite's dev server proxies `/api`, `/video`,
`/camera_status`, `/photo`, and `/unknown_photo` through to the Flask
backend on `:5000` (see `frontend_react/vite.config.js`), so the live
camera feed and all data work exactly as in production while you edit
React components with instant hot-reload.

## How entry/exit/payment works

The single CCTV camera sits **outside the office entrance** — once an
employee walks past it into the office, the camera can no longer see them
for the rest of the day. The engine is built around that:

1. A face appears in the camera frame for the first time today →
   `recognition.py` matches it against enrolled employee photos.
2. On a confident match, `attendance.py` opens a session and logs an ENTRY
   event with a timestamp. The internal timer starts here.
3. While the employee is still walking up to / through the door, they may
   be seen for a few more consecutive frames — this is still the *same*
   entry, not a new one, so nothing else happens.
4. Once the employee has been continuously **absent** from the camera for
   longer than the exit grace period (6s, tunable in `attendance.py`), they
   are assumed to have walked into the office. The session stays open and
   the timer **keeps running internally** — it does not stop, and it is
   never based on how long they were visible on camera.
5. Hours later, when that **same employee's face is detected again** at the
   camera (leaving for the night), that reappearance is treated as the
   EXIT: the timer stops, `duration = exit_time − entry_time` (the full
   time they were inside, including all the hours they were invisible to
   the camera), `payment = duration_hours × hourly_rate`, and an EXIT event
   with the payment is logged and persisted.
6. Reports and Payment Logs read directly from the persisted attendance
   records, so history survives a server restart.

### Demo time simulation

Short test/demo clips (someone on camera for a few seconds) don't produce a
realistic office session on their own. To keep demos convincing,
`attendance.py` can scale the real entry→exit gap into a simulated duration
before it's used for the timer, activity log, records and payment:

- Controlled by two env vars, both optional:
  - `DEMO_MODE` — `true` (default) or `false`.
  - `DEMO_SECONDS_PER_REAL_SECOND` — default `480` (1 real second = 8
    simulated minutes), so a ~5s clip becomes a ~40-minute session.
- Detection/entry/exit logic itself always runs on real time — only the
  *reported* duration/payment is scaled.
- For a real deployment (real CCTV, real shifts), set `DEMO_MODE=false` to
  go back to raw entry→exit duration.

## Adding employees

Go to **Employee Tracking → Add Employee**, upload a clear face photo, enter
their name and hourly rate, and save. The face recognizer retrains
immediately so the new employee is recognized on the very next frame —
no backend restart required.
