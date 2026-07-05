# AI Office Analytics — React Dashboard

React (Vite) source for the AI Office Analytics dashboard. Builds directly
into `../frontend`, which the Flask backend (`../backend/app.py`) serves as
static files. See the top-level `README.md` for full build/run instructions.

Quick start:

```bash
npm install
npm run build   # writes into ../frontend, served by the Flask backend
```

For local UI development with hot-reload against a running backend:

```bash
npm run dev     # http://localhost:5173, proxies API calls to :5000
```
