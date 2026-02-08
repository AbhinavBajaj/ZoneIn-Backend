# Deploy (pull + migrate on prod)

From your **local** machine after pushing:

```bash
cd ZoneIn-Backend
git push origin main
./deploy_pull_migrate.sh
```

That SSHs to **theloveguru**, runs `git pull` and `alembic upgrade head` in the backend repo (default path: `~/Documents/ZoneIn-Backend`). To use a different path: `./deploy_pull_migrate.sh '~/other/path/ZoneIn-Backend'`.

---

# Backfill production (total_focused_sec, etc.)

Profile "Total time" and leaderboard use `users.total_focused_sec`. Backfill it for existing prod users so profiles and leaderboard show correct totals.

## 1. SSH access

Add the prod host to your SSH config:

```bash
cat prod_ssh_config_snippet.txt >> ~/.ssh/config
```

Then test: `ssh theloveguru` (you may be prompted to accept the host key once).

## 2. Option A: Run backfill on the server

SSH in and run the backfill where the app and DB are reachable:

```bash
ssh theloveguru
cd /path/to/ZoneIn-Backend   # or your repo path on the server
source .venv/bin/activate    # if you use a venv
export $(grep -v '^#' .env | xargs)   # load DATABASE_URL from .env
python backfill_total_focused_sec.py
```

Ensure `.env` on the server has `DATABASE_URL` pointing at the production database.

## 3. Option B: Run backfill locally with prod DB URL

If your machine can reach the prod database (e.g. via tunnel or allowed IP):

```bash
cd /path/to/ZoneIn-Backend
export DATABASE_URL="postgresql://user:pass@host:5432/dbname"   # from prod .env
python backfill_total_focused_sec.py
```

Or put `DATABASE_URL=...` in a `.env` file and run:

```bash
set -a && source .env && set +a && python backfill_total_focused_sec.py
```

## What gets backfilled

- **backfill_total_focused_sec.py** – sets `users.total_focused_sec` from the sum of `session_reports.focused_sec` per user. Run this so "Total time" on profiles and the leaderboard is correct for all users.

Top Focus App and ZoneIn Last Activity are computed from the latest report at request time (no backfill needed).
