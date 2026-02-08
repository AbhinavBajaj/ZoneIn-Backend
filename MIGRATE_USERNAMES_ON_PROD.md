# Run username migration on production

This updates prod user IDs from the old format (`abhinav-ecn4u5vi`, `mary-uxf47jxd`, `vineeta-5x_1r-4-`) to the new format (`abhinav_bajaj_1`, `mary_nasimova_1`, `vineeta_bajaj_1`).

## Prerequisites

- SSH access to the production server (or any machine that can reach the prod database)
- Prod `DATABASE_URL` (PostgreSQL connection string)

## Option A: SSH into prod server and run migration there

1. **Backup the prod database** (e.g. `pg_dump` or your provider’s backup).

2. **SSH into the prod server:**
   ```bash
   ssh your-user@your-prod-host
   ```

3. **Go to the app directory** (where ZoneIn-Backend is deployed):
   ```bash
   cd /path/to/ZoneIn-Backend   # use your actual deploy path
   ```

4. **Activate the app’s Python env** (if you use a venv/conda):
   ```bash
   source .venv/bin/activate
   # or: source venv/bin/activate
   ```

5. **Ensure prod `DATABASE_URL` is set** (in `.env`, or export it):
   ```bash
   export DATABASE_URL="postgresql://user:password@host:5432/dbname"
   ```

6. **Dry run** (see what would change, no writes):
   ```bash
   python3 migrate_usernames_to_first_last_number.py --dry-run
   ```
   You should see the three users listed with old → new usernames.

7. **Apply the migration:**
   ```bash
   python3 migrate_usernames_to_first_last_number.py
   ```

8. **Restart the backend** (if it’s a long-running process) so it uses the updated DB:
   ```bash
   sudo systemctl restart zonein-backend
   # or however you restart the app
   ```

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
