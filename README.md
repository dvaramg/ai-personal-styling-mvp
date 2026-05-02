# AI Personal Styling

Full-stack demo for **body-aware outfit recommendations**, optional **AI outfit previews** (Replicate), **internationalization** (Korean / Chinese / English), and modular add-ons (e.g. hat recommendations). Suitable as a portfolio piece showing API design, pragmatic ML integration, and product-minded UX.

## Overview

Users upload full-body photos; the backend derives a **structured body profile** (ranges and labels, not exact measurements) and returns **multiple styled looks** with reasoning, color logic, and proportion tips. Images are generated **sequentially** with throttling to respect external API rate limits.

```
ai_styling/
├── backend/          # FastAPI service
├── frontend/       # React + Vite + TypeScript
└── docs/           # Design notes, screenshots placeholders
```

## Features

- **Outfit recommendation** — Scene, budget, optional style; multiple looks with structured items and explanations.
- **Body analysis (MVP)** — Photo-based inference with **estimated height/weight ranges**, shoulder/waist/thigh/leg signals, styling direction; user can **manually correct** height/weight before recommending.
- **Outfit image previews** — Optional SDXL via Replicate; **serial generation**, delays, and **retry on rate limit** for look 2; negative prompts to reduce off-brand outputs.
- **i18n** — `react-i18next` with browser language detection; KRW / CNY / USD display for budgets.
- **Hat recommendation (MVP)** — Separate API and `/hat` page, isolated from core outfit flow.
- **Wardrobe (skeleton)** — Separate page for future inventory and insights.

## Tech stack

| Layer    | Stack |
|----------|--------|
| Frontend | React 18, TypeScript, Vite, `react-i18next`, `i18next-browser-languagedetector` |
| Backend  | Python 3.12+, FastAPI, Pydantic v2, Uvicorn |
| Images   | Replicate (SDXL Lightning), in-memory prompt cache |
| Config   | `python-dotenv`, `.env` for secrets (never committed) |

## Getting started

### Prerequisites

- Node.js 18+ and npm  
- Python 3.12+  
- (Optional) [Replicate](https://replicate.com) API token for image generation

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # set REPLICATE_API_TOKEN for previews (optional)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API base URL: `http://localhost:8000` — OpenAPI docs at `/docs`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Default dev server: `http://localhost:5173` (Vite). The app calls the API at `http://localhost:8000` — adjust if you proxy or change ports.

### Production build

```bash
cd frontend && npm run build
```

Serve `frontend/dist/` with any static host; point API calls to your deployed backend.

## Demo screenshots

Add your own captures under `docs/screenshots/` and reference them here, for example:

```markdown
![Recommendation flow](docs/screenshots/recommend-flow.png)
![Body analysis card](docs/screenshots/body-analysis.png)
![Hat MVP](docs/screenshots/hat-mvp.png)
```

See `docs/screenshots/README.md` for filenames and layout suggestions.

## Challenges

- **Third-party rate limits** — Replicate allows limited burst traffic; the backend generates images **one at a time** with **delays** and a **single retry** after 429 on the second look, while still returning a full JSON recommendation payload.
- **Prompt stability** — Balancing “body-aware” wording without triggering unwanted tropes (e.g. shirtless or hyper-athletic renders); positive prompts emphasize **clothing-first** phrasing and **negative prompts** filter common failure modes.
- **Honest UX for inference** — Height/weight from photos are shown only as **estimated ranges**, with explicit copy and **manual overrides** so users are not misled.

## Future work

- Real **vision models** for body segmentation and measurements (replace heuristic MVP).
- **Async job queue** for image generation with webhook or SSE progress (true 1/3, 2/3, 3/3 from server state).
- **Auth**, persisted profiles, and wardrobe CRUD wired to a database.
- **E2E tests** and CI (lint, typecheck, `pytest`, `npm run build`).
- **Docker Compose** for one-command local and demo deploys.

## License

Private / portfolio use unless you add an explicit license.
