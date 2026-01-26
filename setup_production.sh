#!/bin/bash
# Production setup script for ZoneIn Backend
# This script sets up the backend server on Google Cloud

set -e

echo "🚀 Setting up ZoneIn Backend for production..."

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Please run this script from the ZoneIn-Backend directory"
    exit 1
fi

# Default production values (can be overridden by environment variables)
# These are pre-configured for quick setup - update if needed
DEFAULT_DATABASE_URL="postgresql://myuser:mypassword@localhost:5432/zonein"
DEFAULT_GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID:-REPLACE_WITH_YOUR_CLIENT_ID}"
DEFAULT_GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET:-REPLACE_WITH_YOUR_CLIENT_SECRET}"
DEFAULT_JWT_SECRET="${JWT_SECRET:-REPLACE_WITH_YOUR_JWT_SECRET}"
DEFAULT_BASE_URL="http://34.132.57.0:8000"

# Use environment variables if set, otherwise use defaults
DATABASE_URL=${DATABASE_URL:-$DEFAULT_DATABASE_URL}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID:-$DEFAULT_GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET:-$DEFAULT_GOOGLE_CLIENT_SECRET}
JWT_SECRET=${JWT_SECRET:-$DEFAULT_JWT_SECRET}
BASE_URL=${BASE_URL:-$DEFAULT_BASE_URL}

echo "📋 Using configuration:"
echo "   DATABASE_URL: ${DATABASE_URL}"
echo "   GOOGLE_CLIENT_ID: ${GOOGLE_CLIENT_ID}"
echo "   BASE_URL: ${BASE_URL}"

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOF
# Production Configuration
DATABASE_URL=${DATABASE_URL}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
JWT_SECRET=${JWT_SECRET}
BASE_URL=${BASE_URL}
EOF
    echo "✅ .env file created"
else
    echo "ℹ️  .env file already exists, skipping creation"
    echo "   Update it manually if needed"
fi

# Install dependencies
echo "📦 Installing Python dependencies..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

# Run database migrations
echo "🗄️  Running database migrations..."
alembic upgrade head

# Run seed script if it exists
if [ -f "seed_production.py" ]; then
    echo "🌱 Seeding database with initial data..."
    python3 seed_production.py
fi

echo ""
echo "✅ Production setup complete!"
echo ""
echo "📋 Next steps:"
echo "   1. Verify .env file has correct values"
echo "   2. Run the server: python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "   3. Or use a process manager like systemd, supervisor, or PM2"
echo ""
