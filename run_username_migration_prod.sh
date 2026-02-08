#!/usr/bin/env bash
# Run username migration on production.
# Usage:
#   export DATABASE_URL="postgresql://..."   # prod connection string
#   ./run_username_migration_prod.sh [--dry-run]

set -e
cd "$(dirname "$0")"

if [ -z "$DATABASE_URL" ]; then
  echo "ERROR: Set DATABASE_URL to your production database connection string."
  echo "Example: export DATABASE_URL=\"postgresql://user:pass@host:5432/dbname\""
  exit 1
fi

echo "Using DATABASE_URL from environment (host: $(echo "$DATABASE_URL" | sed -E 's|.*@([^/]+)/.*|\1|'))."
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
