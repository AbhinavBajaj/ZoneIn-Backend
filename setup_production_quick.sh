#!/bin/bash
# Quick production setup with pre-configured values
# This script uses the production credentials already configured

set -e

echo "🚀 Quick Production Setup for ZoneIn Backend..."

# Check if we're in the right directory
if [ ! -f "app/main.py" ]; then
    echo "❌ Error: Please run this script from the ZoneIn-Backend directory"
    exit 1
fi

# Production configuration
# IMPORTANT: Set these environment variables before running
# Or update this script with your actual values (but don't commit secrets to git)
export DATABASE_URL="${DATABASE_URL:-postgresql://myuser:mypassword@localhost:5432/zonein}"
export GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}"
export GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}"
export JWT_SECRET="${JWT_SECRET}"
export BASE_URL="${BASE_URL:-http://34.132.57.0:8000}"

# Check if required variables are set
if [ -z "$GOOGLE_CLIENT_ID" ] || [ -z "$GOOGLE_CLIENT_SECRET" ] || [ -z "$JWT_SECRET" ]; then
    echo "❌ Error: Missing required environment variables"
    echo ""
    echo "Please set:"
    echo "  export GOOGLE_CLIENT_ID='your-client-id'"
    echo "  export GOOGLE_CLIENT_SECRET='your-client-secret'"
    echo "  export JWT_SECRET='your-jwt-secret'"
    echo ""
    echo "Or create a .env file with these values"
    exit 1
fi

echo "📋 Configuration:"
echo "   Database: PostgreSQL (myuser/mypassword)"
echo "   Base URL: ${BASE_URL}"
echo "   Google OAuth: Configured"
echo ""

# Run the main setup script
./setup_production.sh

echo ""
echo "✅ Quick setup complete!"
echo "   Note: Update BASE_URL to https://api.zonein.io once DNS is configured"
