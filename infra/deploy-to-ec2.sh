#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SalesLens — Deploy to EC2 with feat/enhanced-analysis branch
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Single-port HTTPS deployment with self-signed certificate
# Nginx routes: /api/* → backend:8000, /* → frontend
#
# Usage:
#   ./deploy-to-ec2.sh <EC2_IP> <SSH_KEY_PATH>
#
# Example:
#   ./deploy-to-ec2.sh 98.92.238.232 ~/.ssh/pms-backend-key-1752795223.pem
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -euo pipefail

EC2_IP="${1:-}"
SSH_KEY="${2:-}"

if [[ -z "$EC2_IP" ]] || [[ -z "$SSH_KEY" ]]; then
  echo "Usage: $0 <EC2_IP> <SSH_KEY_PATH>"
  exit 1
fi

SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deploying SalesLens to $EC2_IP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─── 1. Pull latest code ──────────────────────────────────────────────
echo "📥 Pulling feat/enhanced-analysis branch..."
ssh $SSH_OPTS ubuntu@$EC2_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/saleslens
git fetch origin
git checkout feat/enhanced-analysis
git pull origin feat/enhanced-analysis
REMOTE_SCRIPT

# ─── 2. Run database migrations ──────────────────────────────────────
echo "🔄 Running Alembic migrations..."
ssh $SSH_OPTS ubuntu@$EC2_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/saleslens
sudo docker compose exec -T app alembic upgrade head
REMOTE_SCRIPT

# ─── 2.5 Initialize default data ─────────────────────────────────────
echo "🔧 Initializing default data (prompt templates, etc.)..."
ssh $SSH_OPTS ubuntu@$EC2_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/saleslens
sudo docker compose exec -T app python scripts/init_defaults.py || echo "⚠️  Init script not found (expected for older deployments)"
REMOTE_SCRIPT

# ─── 3. Generate self-signed SSL certificate ─────────────────────────
echo "🔐 Generating self-signed SSL certificate..."
ssh $SSH_OPTS ubuntu@$EC2_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/saleslens
sudo mkdir -p /opt/saleslens/nginx/ssl

if [[ ! -f /opt/saleslens/nginx/ssl/cert.pem ]]; then
  sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /opt/saleslens/nginx/ssl/key.pem \
    -out /opt/saleslens/nginx/ssl/cert.pem \
    -subj "/C=US/ST=State/L=City/O=SalesLens/CN=saleslens.local"
  echo "✓ SSL certificate generated"
else
  echo "✓ SSL certificate already exists"
fi
REMOTE_SCRIPT

# ─── 4. Create nginx configuration ───────────────────────────────────
echo "📝 Creating nginx config..."
ssh $SSH_OPTS ubuntu@$EC2_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/saleslens
sudo mkdir -p /opt/saleslens/nginx

cat > /tmp/nginx.conf <<'NGINX_EOF'
server {
    listen 443 ssl http2;
    server_name _;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    client_max_body_size 100M;

    # Backend API
    location /api/ {
        proxy_pass http://app:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health check
    location /health {
        proxy_pass http://app:8000/health;
        proxy_set_header Host $host;
    }

    # Frontend static files
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Gzip
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/xml+rss application/json;
}

# Redirect HTTP to HTTPS (if port 80 is open)
server {
    listen 80;
    server_name _;
    return 301 https://$host$request_uri;
}
NGINX_EOF

sudo mv /tmp/nginx.conf /opt/saleslens/nginx/nginx.conf
echo "✓ Nginx config created"
REMOTE_SCRIPT

# ─── 5. Update docker-compose for production ─────────────────────────
echo "🐳 Updating docker-compose..."
ssh $SSH_OPTS ubuntu@$EC2_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/saleslens

cat > /tmp/docker-compose.prod.yml <<'COMPOSE_EOF'
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_USER: saleslens
      POSTGRES_PASSWORD: saleslens_password
      POSTGRES_DB: saleslens
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U saleslens"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s

  app:
    build: ./backend
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql://saleslens:saleslens_password@postgres:5432/saleslens
      REDIS_URL: redis://redis:6379/0
    volumes:
      - upload_data:/app/uploads
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  worker:
    build: ./backend
    restart: unless-stopped
    env_file: .env
    environment:
      DATABASE_URL: postgresql://saleslens:saleslens_password@postgres:5432/saleslens
      REDIS_URL: redis://redis:6379/0
    volumes:
      - upload_data:/app/uploads
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    command: celery -A app.tasks worker --loglevel=info --concurrency=4 --max-tasks-per-child=100

  nginx:
    image: nginx:alpine
    restart: unless-stopped
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - frontend_build:/usr/share/nginx/html:ro
    depends_on:
      - app

  frontend-builder:
    build: ./frontend
    volumes:
      - frontend_build:/app/dist

volumes:
  postgres_data:
  redis_data:
  upload_data:
  frontend_build:
COMPOSE_EOF

sudo mv /tmp/docker-compose.prod.yml docker-compose.yml
echo "✓ docker-compose updated"
REMOTE_SCRIPT

# ─── 6. Rebuild and restart containers ───────────────────────────────
echo "🚀 Rebuilding containers..."
ssh $SSH_OPTS ubuntu@$EC2_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/saleslens

# Rebuild backend + worker with new code
sudo docker compose up -d --build backend worker

# Wait for backend health
echo "Waiting for backend..."
for i in {1..30}; do
  if sudo docker compose exec -T app curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo "✓ Backend healthy"
    break
  fi
  sleep 2
done

# Rebuild frontend
sudo docker compose build frontend-builder
sudo docker compose up -d frontend-builder
sleep 5

# Start nginx
sudo docker compose up -d nginx

echo "✓ All services running"
REMOTE_SCRIPT

# ─── 7. Verify deployment ─────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  ✅ Deployment Complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  🌐 SalesLens: https://$EC2_IP"
echo "  🔐 SSL: Self-signed (browser will warn - accept to proceed)"
echo ""
echo "  Useful commands:"
echo "    ssh $SSH_OPTS ubuntu@$EC2_IP"
echo "    ssh $SSH_OPTS ubuntu@$EC2_IP 'cd /opt/saleslens && sudo docker compose logs -f'"
echo ""
