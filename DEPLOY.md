# ZoneIn Backend - Production Deployment

## Prerequisites

You'll need:
1. **Google Cloud VM** with external IP
2. **PostgreSQL database** (Cloud SQL or local)
3. **Google OAuth credentials** (Client ID and Secret)
4. **Domain name** (zonein.io) pointing to your server

## Production Configuration

**Pre-configured values:**
- **Google Cloud VM IP:** `34.132.57.0`
- **Database:** `postgresql://myuser:mypassword@localhost:5432/zonein`
- **Base URL:** `http://34.132.57.0:8000` (update to `https://api.zonein.io` when DNS is ready)

**Required environment variables (set these on your server):**
- `GOOGLE_CLIENT_ID` - Your Google OAuth Client ID
- `GOOGLE_CLIENT_SECRET` - Your Google OAuth Client Secret  
- `JWT_SECRET` - Your JWT secret (at least 32 characters)

**Note:** If using Cloud SQL instead of local PostgreSQL, update `DATABASE_URL` in the setup script.

## Deployment Steps

### 1. On Your Local Machine (Prepare)

```bash
cd ZoneIn-Backend

# Commit the setup scripts
git add setup_production.sh seed_production.py README_PRODUCTION.md systemd_service.example DEPLOY.md
git commit -m "Add production setup scripts"
git push origin main
```

### 2. On Google Cloud VM

```bash
# Clone the repository
git clone https://github.com/AbhinavBajaj/ZoneIn-Backend.git
cd ZoneIn-Backend

# Install PostgreSQL if not already installed
sudo apt-get update
sudo apt-get install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres psql << EOF
CREATE DATABASE zonein;
CREATE USER myuser WITH PASSWORD 'mypassword';
GRANT ALL PRIVILEGES ON DATABASE zonein TO myuser;
ALTER USER myuser CREATEDB;
\q
EOF

# Set production secrets as environment variables
# Get these values from PRODUCTION_SECRETS.txt (not in git) or set them manually:
export GOOGLE_CLIENT_ID="your-google-client-id"
export GOOGLE_CLIENT_SECRET="your-google-client-secret"
export JWT_SECRET="your-jwt-secret"
export BASE_URL="http://34.132.57.0:8000"

# Run setup
chmod +x setup_production.sh
./setup_production.sh
```

### 3. Start the Server

```bash
# Option 1: Direct (for testing)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Option 2: Using systemd (recommended)
# Copy systemd_service.example to /etc/systemd/system/zonein-backend.service
# Edit with your paths and environment variables
sudo systemctl daemon-reload
sudo systemctl enable zonein-backend
sudo systemctl start zonein-backend

# Option 3: Using PM2
npm install -g pm2
pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name zonein-backend
pm2 save
pm2 startup
```

### 4. Configure Nginx (Recommended)

```bash
sudo apt-get install nginx
sudo nano /etc/nginx/sites-available/zonein-api
```

Add:
```nginx
server {
    listen 80;
    server_name api.zonein.io;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:
```bash
sudo ln -s /etc/nginx/sites-available/zonein-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. Set Up SSL (Let's Encrypt)

```bash
sudo apt-get install certbot python3-certbot-nginx
sudo certbot --nginx -d api.zonein.io
```

## Frontend Configuration

The frontend will automatically detect `zonein.io` and use `https://api.zonein.io` as the API URL.

If you need to override, set `VITE_API_URL` during build:
```bash
VITE_API_URL=https://api.zonein.io npm run build
```

## Testing

After deployment:
```bash
# Test health endpoint
curl https://api.zonein.io/health

# Test from frontend
# Visit https://zonein.io and check browser console for API calls
```

## Troubleshooting

- **Database connection issues:** Check DATABASE_URL and firewall rules
- **OAuth not working:** Verify GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and BASE_URL
- **CORS errors:** Check that frontend domain is allowed in backend CORS settings
- **Port not accessible:** Check firewall rules and nginx configuration
