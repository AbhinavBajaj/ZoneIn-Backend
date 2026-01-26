# Quick Start - Production Deployment

## On Your Google Cloud VM (34.132.57.0)

### Step 1: Install PostgreSQL

```bash
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib python3 python3-pip
```

### Step 2: Create Database

```bash
sudo -u postgres psql << EOF
CREATE DATABASE zonein;
CREATE USER myuser WITH PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE zonein TO myuser;
ALTER USER myuser CREATEDB;
\q
EOF
```

### Step 3: Clone and Setup

```bash
# Clone repository
git clone https://github.com/AbhinavBajaj/ZoneIn-Backend.git
cd ZoneIn-Backend

# Set environment variables with your secrets
# Get actual values from PRODUCTION_SECRETS.txt (local file, not in git)
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export JWT_SECRET="your-jwt-secret"
export BASE_URL="http://34.132.57.0:8000"

# Run setup
chmod +x setup_production.sh
./setup_production.sh
```

### Step 4: Start Server

```bash
# Test run
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Or use PM2 for production
npm install -g pm2
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name zonein-backend
pm2 save
pm2 startup
```

### Step 5: Configure Firewall

```bash
# Allow port 8000
sudo ufw allow 8000/tcp
sudo ufw enable
```

## Test

```bash
curl http://34.132.57.0:8000/health
```

Should return: `{"status":"ok"}`

## Frontend Configuration

The frontend (ZoneInUI) is already configured to:
- Auto-detect `zonein.io` domain
- Use `http://34.132.57.0:8000` as API URL when on production

## Next Steps

1. Set up DNS: Point `zonein.io` to `34.132.57.0`
2. Set up SSL: Use Let's Encrypt for HTTPS
3. Update BASE_URL to `https://api.zonein.io` once DNS is ready
4. Update Google OAuth redirect URI to include `https://api.zonein.io/auth/google/callback`
