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

# Check for required environment variables
if [ -z "$DATABASE_URL" ]; then
    echo "⚠️  Warning: DATABASE_URL not set. Using SQLite (not recommended for production)"
    echo "   Set DATABASE_URL=postgresql://user:password@host:5432/dbname for production"
fi

if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ]; then
    echo "⚠️  Warning: Google OAuth credentials not set"
    echo "   Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET"
fi

if [ -z "$JWT_SECRET" ]; then
    echo "❌ Error: JWT_SECRET must be set for production"
    exit 1
fi

if [ -z "$BASE_URL" ]; then
    echo "⚠️  Warning: BASE_URL not set. Using default http://localhost:8000"
    echo "   Set BASE_URL=https://api.zonein.io (or your production URL)"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from environment variables..."
    cat > .env << EOF
# Production Configuration
DATABASE_URL=${DATABASE_URL:-sqlite:///./zonein.db}
GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
JWT_SECRET=${JWT_SECRET}
BASE_URL=${BASE_URL:-http://localhost:8000}
EOF
    echo "✅ .env file created"
else
    echo "ℹ️  .env file already exists, skipping creation"
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
