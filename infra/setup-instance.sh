#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# SalesLens — Instance setup script
#
# Run this ON the EC2 instance after provisioning. It installs Docker,
# clones the repo, configures the environment, and starts all services.
#
# Usage:
#   bash setup-instance.sh <S3_BUCKET_NAME>
#
# Example:
#   bash setup-instance.sh saleslens-recordings-a1b2c3d4
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_URL="https://github.com/upendradevsingh/saleslens.git"
APP_DIR="/opt/saleslens"
S3_BUCKET="${1:-}"

log()  { echo "[saleslens-setup] $*"; }
fail() { echo "[saleslens-setup] ERROR: $*" >&2; exit 1; }

[[ -z "$S3_BUCKET" ]] && fail "Usage: bash setup-instance.sh <S3_BUCKET_NAME>"

# ── System updates ─────────────────────────────────────────────────────────
log "Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── Install Docker ─────────────────────────────────────────────────────────
log "Installing Docker..."
if ! command -v docker &>/dev/null; then
  curl -fsSL https://get.docker.com | sudo sh
  sudo usermod -aG docker "$USER"
  log "Docker installed."
else
  log "Docker already installed."
fi

# ── Install Docker Compose v2 ─────────────────────────────────────────────
log "Installing Docker Compose v2..."
if ! docker compose version &>/dev/null; then
  sudo apt-get install -y -qq docker-compose-plugin
  log "Docker Compose v2 installed."
else
  log "Docker Compose v2 already installed."
fi

# ── Install git ────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
  sudo apt-get install -y -qq git
fi

# ── Clone repo ─────────────────────────────────────────────────────────────
log "Cloning SalesLens repo..."
if [[ -d "$APP_DIR" ]]; then
  log "Directory exists — pulling latest..."
  cd "$APP_DIR"
  sudo git pull origin main
else
  sudo git clone "$REPO_URL" "$APP_DIR"
  sudo chown -R "$USER:$USER" "$APP_DIR"
  cd "$APP_DIR"
fi

# ── Configure environment ──────────────────────────────────────────────────
log "Setting up .env..."
cp .env.example .env

# Get region from instance metadata (IMDSv2)
TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
INSTANCE_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "ap-south-1")

# Set S3 configuration
sed -i "s|^S3_BUCKET=.*|S3_BUCKET=${S3_BUCKET}|" .env
sed -i "s|^S3_REGION=.*|S3_REGION=${INSTANCE_REGION}|" .env

# AWS credentials are not needed — the instance role provides access via IMDS
sed -i "s|^AWS_ACCESS_KEY_ID=.*|AWS_ACCESS_KEY_ID=|" .env
sed -i "s|^AWS_SECRET_ACCESS_KEY=.*|AWS_SECRET_ACCESS_KEY=|" .env

# Generate a secure secret key
SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
sed -i "s|^SECRET_KEY=.*|SECRET_KEY=${SECRET}|" .env

# Prompt for required API keys
echo ""
echo "=== API Key Configuration ==="
echo ""

read -rp "Enter your Deepgram API key (https://console.deepgram.com): " DEEPGRAM_KEY
if [[ -n "$DEEPGRAM_KEY" ]]; then
  sed -i "s|^DEEPGRAM_API_KEY=.*|DEEPGRAM_API_KEY=${DEEPGRAM_KEY}|" .env
fi

read -rp "Enter your OpenAI API key (https://platform.openai.com/api-keys): " OPENAI_KEY
if [[ -n "$OPENAI_KEY" ]]; then
  sed -i "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=${OPENAI_KEY}|" .env
fi

log ".env configured."

# ── Start services ─────────────────────────────────────────────────────────
log "Starting services with Docker Compose..."
sudo docker compose up -d --build

# Wait for postgres to be ready
log "Waiting for PostgreSQL to be ready..."
for i in $(seq 1 30); do
  if sudo docker compose exec -T postgres pg_isready -U saleslens &>/dev/null; then
    break
  fi
  sleep 2
done

# ── Run migrations ─────────────────────────────────────────────────────────
log "Running Alembic migrations..."
sudo docker compose exec -T backend alembic upgrade head

# ── Verify health ──────────────────────────────────────────────────────────
log "Verifying health endpoint..."
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/health &>/dev/null; then
    log "Health check passed!"
    break
  fi
  if [[ $i -eq 15 ]]; then
    log "WARNING: Health check did not pass after 30s. Check logs: docker compose logs backend"
  fi
  sleep 2
done

# ── Systemd service for auto-restart ───────────────────────────────────────
log "Setting up systemd service..."
sudo tee /etc/systemd/system/saleslens.service >/dev/null <<EOF
[Unit]
Description=SalesLens Docker Compose Application
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
ExecStart=/usr/bin/docker compose up -d
ExecStop=/usr/bin/docker compose down
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable saleslens.service
log "Systemd service enabled — SalesLens will auto-start on boot."

# ── Done ───────────────────────────────────────────────────────────────────
PUBLIC_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "<instance-ip>")

cat <<EOF

============================================================
  SalesLens is running!
============================================================

  API:      http://${PUBLIC_IP}:8000
  Frontend: http://${PUBLIC_IP}:3000
  Health:   http://${PUBLIC_IP}:8000/health

  S3 Bucket: ${S3_BUCKET}
  Region:    ${INSTANCE_REGION}

  Useful commands:
    cd ${APP_DIR}
    sudo docker compose logs -f        # follow logs
    sudo docker compose restart         # restart all
    sudo docker compose exec backend alembic upgrade head  # re-run migrations

============================================================
EOF
