#!/usr/bin/env bash
# From local: push is already done. This script SSHs to theloveguru, pulls, and runs migrations.
# Usage: ./deploy_pull_migrate.sh [remote-backend-path]
# Default remote path: ~/Documents/ZoneIn-Backend (set REMOTE_BACKEND_PATH to override)

set -e
REMOTE_PATH="${1:-$REMOTE_BACKEND_PATH}"
REMOTE_PATH="${REMOTE_PATH:-~/Documents/ZoneIn-Backend}"

# Pass path as single-quoted so remote shell expands ~ (e.g. '~/Documents/ZoneIn-Backend')
REMOTE_CMD="cd $REMOTE_PATH && git pull origin main && ( [ -f .env ] && export \$(grep -v '^#' .env | xargs) ); python3 -m alembic upgrade head"
echo "==> SSH theloveguru: $REMOTE_CMD"
ssh theloveguru "$REMOTE_CMD"
