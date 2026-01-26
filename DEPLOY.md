# ZoneIn Backend - Production Deployment

## Prerequisites

You'll need:
1. **Google Cloud VM** with external IP
2. **PostgreSQL database** (Cloud SQL or local)
3. **Google OAuth credentials** (Client ID and Secret)
4. **Domain name** (zonein.io) pointing to your server

## Required Information

Before running the setup, you'll need:

1. **Database Connection String:**
   ```
   DATABASE_URL=postgresql://user:password@host:5432/zonein
   ```

2. **Google OAuth Credentials:**
   - Client ID: `your-client-id.apps.googleusercontent.com`
   - Client Secret: `your-client-secret`

3. **JWT Secret:**
   - A random string at least 32 characters long
   - Generate with: `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`

4. **Base URL:**
   - Your production API URL: `https://api.zonein.io` (or your IP/domain)

5. **Google Cloud VM IP:**
   - The external IP address of your VM instance

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
git clone https://github.com/your-username/ZoneIn-Backend.git
cd ZoneIn-Backend

# Set environment variables
export DATABASE_URL="postgresql://user:password@host:5432/zonein"
export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
export GOOGLE_CLIENT_SECRET="your-client-secret"
export JWT_SECRET="your-jwt-secret-here"
export BASE_URL="https://api.zonein.io"

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
