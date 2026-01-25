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
| DELETE | `/reports` | Bearer | Delete all reports for the current user |
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

- `timeline_buckets_json`: JSON array of `{ bucket_start_ts, bucket_duration_sec, state }` with `state` one of `"focused"` | `"distracted"` | `"neutral"`. No URLs, app names, or raw events.
- Reports are upserted by `(userId, sessionId)`.

## Tests

```bash
pytest tests/ -v
```

Uses SQLite for tests. Covers: health, auth redirect/callback (mocked), POST create/upsert, GET list/by-id, DELETE all reports, auth isolation (user cannot read others’ reports).

## Deployment (Render / Fly / Railway)

- Set env vars in the platform dashboard.
- Use `DATABASE_URL` from Supabase/Neon.
- Set `BASE_URL` to your deployed backend URL (e.g. `https://zonein-api.fly.dev`).
- Add `BASE_URL` and your UI origin to CORS in `app/main.py` if needed.
- Run `alembic upgrade head` as a release command or one-off job.
- Start with `uvicorn app.main:app --host 0.0.0.0 --port 8000` (or the port the platform provides).

## Data model (summary)

- **users**: `id`, `google_sub` (unique), `email`, `name`, `created_at`
- **session_reports**: `id`, `user_id`, `session_id`, `started_at`, `ended_at`, `duration_sec`, `focused_sec`, `distracted_sec`, `neutral_sec`, `zone_in_score`, `timeline_buckets_json`, `cloud_ai_enabled`, `created_at`. Unique on `(user_id, session_id)`.

No analytics, no raw behavior data, no per-event API calls.
