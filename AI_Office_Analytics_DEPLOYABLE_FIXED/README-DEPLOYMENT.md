# Deploying AI Office Analytics online

## Why this needs two separate deployments

- **Frontend** (`frontend_react/`, React + Vite) → deploys fine to **Vercel**. It's a static site.
- **Backend** (`backend/`, Flask + OpenCV + InsightFace/ONNXRuntime) → **cannot** run on Vercel.
  Vercel only runs short-lived serverless functions; this backend is a long-running process
  with heavy native dependencies (OpenCV, ONNXRuntime) and a face-recognition model it loads
  once at startup. It needs a real, persistent server: **Render**, **Railway**, **Fly.io**, or
  your own VPS all work. `render.yaml` is included and ready to go for Render.

## Why the camera now works after deployment

The original code opened the camera with `cv2.VideoCapture(0)` **on the server** — that only
ever sees a webcam physically plugged into whatever machine runs Flask. A cloud server has no
such camera, so this could never have worked online no matter how it was hosted.

This has been restructured so the **browser** captures the visitor's own webcam
(`navigator.mediaDevices.getUserMedia`) and posts a frame roughly once a second to a new
endpoint, `POST /api/detect_frame`. That endpoint runs the exact same `recognizer.process_frame()`
call the old server-camera stream used — same face detection, same entry/exit logic, same
attendance/payment side effects — and returns the annotated frame for the browser to display.
Nothing in `recognition.py` or `attendance.py` changed.

There is no microphone-driven feature anywhere in this app currently (no audio recording,
no voice commands) — no code in the project reads from a microphone — so there's nothing to
wire up there. If you want a specific microphone-based feature, that would be new functionality
to design and add.

## One-time setup

### 1. Backend → Render

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, point it at the repo. It will read `render.yaml` and
   provision the service + a 1GB persistent disk automatically.
3. After the first deploy, copy the service URL, e.g. `https://ai-office-analytics-api.onrender.com`.
4. In Render's dashboard for the service, set `FRONTEND_ORIGIN` to your real Vercel URL once you
   have it (step 2 below) — it defaults to `*` so nothing breaks in the meantime.

Notes:
- Face recognition (InsightFace) downloads its model files on first run — the first request
  after a cold start will be slow. Keep the service warm on a paid plan for production use.
- Employees / photos / payment records are written under `/var/data` (see `render.yaml`), which
  is the persistent disk — they survive restarts and redeploys. Without a mounted disk, most
  PaaS free tiers wipe the filesystem on every redeploy.

### 2. Frontend → Vercel

1. In Vercel: **New Project**, import the same repo. `vercel.json` at the repo root tells Vercel
   to build `frontend_react/` and serve `frontend/` (the build output) — no manual config needed.
2. In the Vercel project's **Environment Variables**, add:
   - `VITE_API_BASE_URL` = your Render backend URL from step 1 (no trailing slash).
3. Deploy. Redeploy after adding/changing the env var (Vite bakes it in at build time).

### 3. Lock down CORS

Once both URLs are stable, set `FRONTEND_ORIGIN` on the backend to the exact Vercel URL instead
of `*`, and redeploy the backend. This restricts which origins can call your API.

## Local development is unchanged

`cd backend && python app.py` (port 5000) and `cd frontend_react && npm run dev` (port 5173,
proxies to :5000) still work exactly as before — `VITE_API_BASE_URL` only matters for
production builds.

## Package structure / gunicorn entrypoint

`backend/` is now a real Python package (`backend/__init__.py`), so it can be launched the
standard, deployment-friendly way from the **project root**:

```bash
gunicorn backend.app:app --bind 0.0.0.0:$PORT --workers 1 --threads 4 --timeout 120
```

This is exactly what `Procfile` and `render.yaml`'s `startCommand` use. Internally, `app.py`,
`attendance.py`, and `recognition.py` import their sibling modules with package-relative
imports (`from .employees import employee_store`, etc.) with a fallback to plain imports, so
both of the following keep working with zero changes:

- `gunicorn backend.app:app` / `python -m backend.app` from the project root (package mode —
  what Render uses)
- `cd backend && python app.py` (direct-script mode — local dev, unchanged)

## Environment variables reference

| Variable | Where | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | frontend_react (build-time) | Full backend URL. Empty = same-origin (local dev / Flask serving the built frontend). |
| `FRONTEND_ORIGIN` | backend | Allowed CORS origin(s) for the deployed frontend. `*` by default. |
| `DATA_DIR`, `PHOTOS_DIR`, `UNKNOWN_DIR` | backend | Override storage paths — point these at a mounted persistent disk in production. |
| `DEMO_MODE`, `DEMO_SECONDS_PER_REAL_SECOND` | backend | Existing demo time-scaling controls — unchanged. |
| `FACE_MODEL_PACK`, `FACE_CTX_ID`, `FACE_DET_SIZE`, etc. | backend | Existing InsightFace tuning knobs — unchanged. |
