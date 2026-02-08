#!/usr/bin/env bash
# Run username migration on production.
# Run this script from the ZoneIn-Backend directory (e.g. on the prod server).
# It uses DATABASE_URL from .env in this directory — do NOT use placeholder values.
#
# Usage:
#   ./run_username_migration_prod.sh [--dry-run]
#
# If you need to point at a different DB, set DATABASE_URL before running:
#   export DATABASE_URL="postgresql://user:pass@real-host:5432/dbname"
#   ./run_username_migration_prod.sh --dry-run

set -e
cd "$(dirname "$0")"

# Load .env if present (so we use the same DB as the app on this machine)
if [ -f .env ]; then
  set -a
  source .env
  set +a
  echo "Loaded .env from $(pwd)"
fi

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: DATABASE_URL is not set. Add it to .env or export it."
  echo "Example .env line: DATABASE_URL=postgresql://user:pass@host:5432/dbname"
  echo "Do NOT use placeholder text like USER or PROD_DB_HOST — use real values."
  exit 1
fi

# Show which host we're connecting to (don't print password)
echo "Using DATABASE_URL (host: $(echo "$DATABASE_URL" | sed -E 's|.*@([^/:]+).*|\1|'))."
if [ "$1" = "--dry-run" ]; then
  python3 migrate_usernames_to_first_last_number.py --dry-run
else
  echo "Run with --dry-run first to preview changes."
  read -p "Apply migration to prod? [y/N] " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 migrate_usernames_to_first_last_number.py
  else
    echo "Aborted."
  fi
fi
