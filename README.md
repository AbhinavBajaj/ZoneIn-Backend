# ZoneIn-Backend

Privacy-first backend for **ZoneIn**: stores only **aggregated focus session reports**. All raw data (per-event logs, URLs, app names, screenshots, AI decisions) stays **local** on the user’s machine.

## Purpose

- **Google sign-in** (OAuth, JWT)
- **Store aggregated session reports** (bucketed timeline, no raw behavior)
- Power **calendar + report view** in ZoneIn UI
- Optional leaderboard later (not implemented)

## Stack

- Python 3.11+, **FastAPI**
- **SQLite** for local dev (default); **Postgres** for production (Supabase / Neon)
- **SQLAlchemy** 2, **Alembic** migrations
- **JWT** auth issued by backend
- **Google OAuth** (OpenID Connect)

## Env vars

Create a `.env` file (see `.env.example`):

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | **Optional.** Default `sqlite:///./zonein.db` for local dev (no Postgres). Use `postgresql://user:pass@host:5432/zonein` for production. |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth client secret |
| `JWT_SECRET` | Secret for signing JWTs (min 32 chars) |
| `BASE_URL` | Base URL of this backend, e.g. `http://localhost:8000` |

## Local run (SQLite, no Postgres)

```bash
python -m venv .venv
source .venv/bin/activate   # or .venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env       # set GOOGLE_*, JWT_SECRET, BASE_URL; leave DATABASE_URL unset for SQLite
```

**Migrations:**

```bash
alembic upgrade head
```

**Start server:**

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Or: `python run.py` (runs uvicorn on port 8000).

**Note:** Use a dedicated venv. The project uses **pydantic 2.x**; avoid mixing with envs that need pydantic 1.x (e.g. spacy 3.5).

**Troubleshooting:**
- **Postgres `connection refused`:** If you see `connection refused` to `localhost:5432`, Postgres is not running and your `.env` has `DATABASE_URL=postgresql://...`. Use SQLite instead: **remove `DATABASE_URL`** from `.env` (or set `DATABASE_URL=sqlite:///./zonein.db`), then run `alembic upgrade head` and start the server again.
- **"No events" / app says "Report sent" but backend shows nothing:** Another process may already be bound to port 8000 (e.g. an old uvicorn). The app sends to that process; you watch the new one, which fails with `address already in use`. **Before starting:** run `lsof -ti :8000 | xargs kill -9` (macOS/Linux) to free the port, then start **one** backend. Every request is logged as `[Backend] GET /health <- 127.0.0.1` and `[Backend] POST /reports -> 200`; if you never see these, requests are not reaching this process.

## API

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/health` | No | Health check |
| GET | `/auth/google/login` | No | Redirect to Google sign-in |
| GET | `/auth/google/callback` | No | OAuth callback; redirects to UI with `?token=...` |
| GET | `/me` | Bearer | Current user (id, email, name) |
| POST | `/reports` | Bearer | Create or upsert report (by `userId` + `sessionId`) |
| GET | `/reports?from=YYYY-MM-DD&to=YYYY-MM-DD&timezone=America/Los_Angeles` | Bearer | List reports in date range; `timezone` (IANA) interprets `from`/`to` as local dates |
| GET | `/reports/{id}` | Bearer | Get report by id |

**Auth:** `Authorization: Bearer <jwt>`.

**Google login flow:**  
1. Client redirects to `GET /auth/google/login?redirect_ui=http://localhost:5000`.  
2. User signs in with Google.  
3. Callback redirects to `{redirect_ui}/signin?token=<jwt>`.  
4. Client stores JWT and uses it for `/me`, `/reports`.

## Example POST /reports payload

Send `started_at` and `ended_at` in the **user’s local timezone** (with offset). The Mac app uses `TimeZone.current` when formatting.

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "started_at": "2026-01-24T10:00:00-08:00",
  "ended_at": "2026-01-24T14:00:00-08:00",
  "duration_sec": 14400,
  "focused_sec": 12000,
  "distracted_sec": 1200,
  "neutral_sec": 1200,
  "zone_in_score": 83.33,
  "timeline_buckets_json": "[{\"bucket_start_ts\": 36000, \"bucket_duration_sec\": 300, \"state\": \"focused\"}, {\"bucket_start_ts\": 36300, \"bucket_duration_sec\": 300, \"state\": \"distracted\"}]",
  "cloud_ai_enabled": true
}
```

- `timeline_buckets_json`: JSON array of **flat events** (one per app switch or Chrome/tab event). Each event: `{ start_ts, end_ts, kind ("browser"|"app"), label, classification, state, url? (browser), bundle_id? (app) }`. No nesting; old segment/activities format is not supported.
- Reports are upserted by `(userId, sessionId)`.

## Tests

```bash
pytest tests/ -v
```

Uses SQLite for tests. Covers: health, auth redirect/callback (mocked), POST create/upsert, GET list/by-id, auth isolation (user cannot read others’ reports).

## Deployment (Render / Fly / Railway)

- Set env vars in the platform dashboard.
- Use `DATABASE_URL` from Supabase/Neon.
- Set `BASE_URL` to your deployed backend URL (e.g. `https://zonein-api.fly.dev`).
- Add `BASE_URL` and your UI origin to CORS in `app/main.py` if needed.
- Run `alembic upgrade head` as a release command or one-off job.
- Start with `uvicorn app.main:app --host 0.0.0.0 --port 8000` (or the port the platform provides).

## Data model (summary)

- **users**: `id`, `google_sub` (unique), `email`, `name`, `created_at`
- **session_reports**: `id`, `user_id`, `session_id`, `started_at`, `ended_at`, `duration_sec`, `focused_sec`, `distracted_sec`, `neutral_sec`, `snoozed_sec`, `zone_in_score`, `focus_percentage`, `timeline_buckets_json`, `half_focused_segments_json`, `cloud_ai_enabled`, `created_at`. Unique on `(user_id, session_id)`.

**Where Chrome / browser URLs live:** In `session_reports.timeline_buckets_json`. That column is a JSON array of flat events; each event has `start_ts`, `end_ts`, `kind` (`"browser"` or `"app"`), `label`, `classification`, `state`, and optionally `url` (for browser tabs). There is no separate “websites” table; all event data for the report is in this JSON.

**Inspecting the latest report (timeline + Chrome URLs + segments):**

The backend DB is **not** the same as the macOS app’s DB. Use the **ZoneIn-Backend** repo and its DB (e.g. `ZoneIn-Backend/zonein.db` for SQLite).

1. **Create tables if needed** (from `ZoneIn-Backend`):
   ```bash
   cd /path/to/ZoneIn-Backend
   alembic upgrade head
   ```
2. **List events (Chrome + app) with Python** (uses same DB as backend):
   ```bash
   cd /path/to/ZoneIn-Backend
   python inspect_latest_report.py
   ```
3. **Raw SQLite** (must run from `ZoneIn-Backend` so `zonein.db` is the backend’s file):
   ```bash
   cd /path/to/ZoneIn-Backend
   sqlite3 zonein.db "SELECT timeline_buckets_json FROM session_reports ORDER BY ended_at DESC LIMIT 1;" | jq .
   ```
   Or list each event:
   ```bash
   sqlite3 zonein.db "SELECT json_extract(value,'$.kind') AS kind, json_extract(value,'$.label') AS label, json_extract(value,'$.state') AS state, json_extract(value,'$.url') AS url FROM session_reports, json_each(timeline_buckets_json) WHERE session_reports.id=(SELECT id FROM session_reports ORDER BY ended_at DESC LIMIT 1) ORDER BY json_extract(value,'$.start_ts');"
   ```
   If you run `sqlite3 zonein.db` from the **ZoneIn** (macOS app) repo, you’ll hit the app’s local DB, which has no `session_reports` table.

No analytics, no raw behavior data, no per-event API calls.
