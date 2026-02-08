# Username format migration: firstname_lastname_N

Usernames are now **firstname_lastname_N** (e.g. `abhinav_bajaj_1`, `vineeta_bajaj_1`, `mary_nasimova_1`). The backend assigns N chronologically (first user with that first+last name gets _1, etc.) so there are no conflicts.

## Backend logic (already in place)

- **New users**: On sign-in, `generate_unique_username(db, full_name)` in `app/services/username.py` builds the base from the Google name (e.g. "Abhinav Bajaj" → `abhinav_bajaj`) and assigns the next free N.
- **Existing users**: Run the migration script once per environment.

## Run migration on local and prod

1. **Backup** the DB (especially prod).
2. **Dry run** (optional):
   ```bash
   cd ZoneIn-Backend
   python migrate_usernames_to_first_last_number.py --dry-run
   ```
3. **Apply**:
   ```bash
   python migrate_usernames_to_first_last_number.py
   ```

Users are processed in `created_at` order so N is chronological per base. Ensure `users.name` is set correctly (e.g. "Vineeta Bajaj", "Mary Nasimova", "Abhinav Bajaj") so the base is correct; if `name` is missing, the script falls back to the part before `@` in email (e.g. `abhinav_user_1`).

After migration, existing usernames like `vineeta-5x_1r-4-` or `abhinav-qjixhw2p` will be replaced by `vineeta_bajaj_1`, `abhinav_bajaj_1`, etc., according to each user’s `name` and creation order.
