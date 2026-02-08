# Run username migration on production

This updates prod user IDs from the old format (`abhinav-ecn4u5vi`, `mary-uxf47jxd`, `vineeta-5x_1r-4-`) to the new format (`abhinav_bajaj_1`, `mary_nasimova_1`, `vineeta_bajaj_1`).

---

## Quick “what to do”

- **The Leadership Board with old names** is served by the app at **34.132.57.0:8000**. That app is connected to **one** database (prod). You need to run the migration **against that same database**.
- **Your local `.env`** has `DATABASE_URL=postgresql://myuser:mypassword@localhost:5432/zonein` — that is your **local** DB. Migrating that only updates local, not the prod app.
- So you have to run the migration **on the server 34.132.57.0** (or with a connection string that points to the **prod** DB). The prod DB URL is whatever the app on 34.132.57.0 uses (usually in `.env` on that server).

**Steps:**

1. **SSH into the prod server** (where the app at 34.132.57.0 runs):
   ```bash
   ssh YOUR_USER@34.132.57.0
   ```
   Use the same user/host you use to deploy (e.g. `ssh abhinav_bajaj2023@34.132.57.0` or from `~/.ssh/config`).

2. **Go to the backend app directory on that server** (where `.env` and the code live):
   ```bash
   cd ~/ZoneIn-Backend
   # or: cd /home/abhinav_bajaj2023/ZoneIn-Backend
   # use: find /home -name "migrate_usernames_to_first_last_number.py" 2>/dev/null
   ```

3. **On that server, the `.env` is the prod one.** The script reads `DATABASE_URL` from `.env` automatically. Dry-run:
   ```bash
   python3 migrate_usernames_to_first_last_number.py --dry-run
   ```
   You should see the three users (abhinav, mary, vineeta) with old → new usernames.

4. **Apply the migration:**
   ```bash
   python3 migrate_usernames_to_first_last_number.py
   ```

5. **Restart the backend** on that server so the app picks up the new data:
   ```bash
   sudo systemctl restart zonein-backend
   # or: pkill -f uvicorn; cd ~/ZoneIn-Backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 &
   ```

If you don’t have SSH to 34.132.57.0, you need the **prod** `DATABASE_URL` from whoever manages that server (or from the host’s `.env`). Then from your laptop, with that URL in `.env` or `export DATABASE_URL="..."`, run the same script — only if your machine can reach the prod DB (direct or via tunnel).

---

## Prerequisites

- SSH access to the production server (or the prod `DATABASE_URL` and network access to that DB).

## Option A: SSH into prod server and run migration there

1. **Backup the prod database** (e.g. `pg_dump` or your provider’s backup).

2. **SSH into the prod server:**
   ```bash
   ssh your-user@34.132.57.0
   ```

3. **Go to the app directory** (where ZoneIn-Backend is deployed and where `.env` lives):
   ```bash
   cd ~/ZoneIn-Backend
   ```

4. **Activate the app’s Python env** (if you use a venv):
   ```bash
   source .venv/bin/activate
   # or: source venv/bin/activate
   ```

5. **No need to set `DATABASE_URL` by hand** — the script uses the app’s config and loads `.env` from the current directory.

6. **Dry run** (see what would change, no writes):
   ```bash
   python3 migrate_usernames_to_first_last_number.py --dry-run
   ```

7. **Apply the migration:**
   ```bash
   python3 migrate_usernames_to_first_last_number.py
   ```

8. **Restart the backend** (see step 5 in “Quick what to do” above).

## Option B: Run migration from your laptop using prod DATABASE_URL

If your laptop can reach the prod database (e.g. via SSH tunnel or allowed IP):

1. **Backup the prod database.**

2. **On your machine**, clone or open ZoneIn-Backend and set prod `DATABASE_URL`:
   ```bash
   cd /path/to/ZoneIn-Backend
   export DATABASE_URL="postgresql://user:password@prod-db-host:5432/dbname"
   ```

3. **Dry run:**
   ```bash
   python3 migrate_usernames_to_first_last_number.py --dry-run
   ```

4. **Apply:**
   ```bash
   python3 migrate_usernames_to_first_last_number.py
   ```

## Expected result

- Users are processed in **created_at** order.
- Each user gets `firstname_lastname_N` from their `name` (or email prefix if `name` is missing).
- Example outcome:
  - `abhinav-ecn4u5vi` → `abhinav_bajaj_1` (if `name` is e.g. "Abhinav Bajaj")
  - `mary-uxf47jxd` → `mary_nasimova_1` (if `name` is e.g. "Mary Nasimova")
  - `vineeta-5x_1r-4-` → `vineeta_bajaj_1` (if `name` is e.g. "Vineeta Bajaj")

Ensure `users.name` is set correctly in prod for these three users so the bases are right; the script uses `user.name` and falls back to the part before `@` in `user.email`.

## If you use an SSH tunnel to the prod DB

```bash
# Terminal 1: create tunnel (example: prod DB is on same server as app)
ssh -L 5433:localhost:5432 your-user@your-prod-host

# Terminal 2: run migration against local port
cd /path/to/ZoneIn-Backend
export DATABASE_URL="postgresql://user:password@localhost:5433/dbname"
python3 migrate_usernames_to_first_last_number.py --dry-run
python3 migrate_usernames_to_first_last_number.py
```

After this, the Leadership Board and Published Reports will show the new usernames once the app is restarted or reloads data from the DB.
