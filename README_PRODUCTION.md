# ZoneIn Backend - Production Deployment Guide

## Quick Setup

1. **Set environment variables:**
   ```bash
   export DATABASE_URL="postgresql://user:password@host:5432/zonein"
   export GOOGLE_CLIENT_ID="your-client-id.apps.googleusercontent.com"
   export GOOGLE_CLIENT_SECRET="your-client-secret"
   export JWT_SECRET="your-random-secret-at-least-32-chars"
   export BASE_URL="https://api.zonein.io"
   ```

2. **Run setup script:**
   ```bash
   chmod +x setup_production.sh
   ./setup_production.sh
   ```

3. **Start the server:**
   ```bash
   # Option 1: Direct uvicorn
   uvicorn app.main:app --host 0.0.0.0 --port 8000
   
   # Option 2: Using systemd (see systemd_service.example)
   # Option 3: Using PM2
   pm2 start "uvicorn app.main:app --host 0.0.0.0 --port 8000" --name zonein-backend
   ```

## Google Cloud Setup

### 1. Create VM Instance
- Choose appropriate machine type (e.g., e2-small or e2-medium)
- Allow HTTP/HTTPS traffic
- Note the external IP address

### 2. Install Dependencies
```bash
# Update system
sudo apt-get update
sudo apt-get install -y python3 python3-pip postgresql-client

# Install Python dependencies
pip3 install -r requirements.txt
```

### 3. Database Setup
- Use Cloud SQL (PostgreSQL) or install PostgreSQL on the VM
- Create database: `createdb zonein` (if using local PostgreSQL)
- Or use connection string for Cloud SQL

### 4. Configure Firewall
```bash
# Allow port 8000 (or use nginx reverse proxy on port 80/443)
sudo ufw allow 8000/tcp
```

### 5. Set Up Reverse Proxy (Recommended)
Use nginx to proxy requests:
```nginx
server {
    listen 80;
    server_name api.zonein.io;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## Environment Variables

Create a `.env` file or set environment variables:

```bash
DATABASE_URL=postgresql://user:password@host:5432/zonein
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
JWT_SECRET=your-random-secret-at-least-32-chars
BASE_URL=https://api.zonein.io
```

## DNS Configuration

1. Point `api.zonein.io` to your Google Cloud VM's external IP
2. Or use the same domain with a subdomain

## Testing

After deployment, test the API:
```bash
curl https://api.zonein.io/health
```

## Monitoring

- Check logs: `journalctl -u zonein-backend -f` (if using systemd)
- Or: `pm2 logs zonein-backend` (if using PM2)
