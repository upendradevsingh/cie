#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CIE — Instance setup script
#
# Run this ON the EC2 instance after provisioning. It installs Docker,
# clones the repo, configures credentials via systemd, and starts services.
#
# Credentials are stored in /etc/cie/env (root-only, mode 600) and loaded
# via systemd EnvironmentFile — never written to the repo or .env files.
#
# Designed for spot instances with persistent EBS — survives interruptions.
#
# Usage:
#   bash setup-instance.sh <S3_BUCKET_NAME>
#
# Example:
#   bash setup-instance.sh cie-recordings-a1b2c3d4
# ---------------------------------------------------------------------------
set -euo pipefail

REPO_URL="https://github.com/upendradevsingh/cie.git"
APP_DIR="/opt/cie"
DATA_DIR="/opt/cie-data"
S3_BUCKET="${1:-}"

log()  { echo "[cie-setup] $*"; }
fail() { echo "[cie-setup] ERROR: $*" >&2; exit 1; }

[[ -z "$S3_BUCKET" ]] && fail "Usage: bash setup-instance.sh <S3_BUCKET_NAME>"

# ── System updates ─────────────────────────────────────────────────────────
log "Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── Install AWS CLI (needed for SSM secret retrieval) ──────────────────────
if ! command -v aws &>/dev/null; then
  log "Installing AWS CLI v2..."
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
  sudo apt-get install -y -qq unzip
  unzip -q /tmp/awscliv2.zip -d /tmp/awscli
  sudo /tmp/awscli/aws/install
  rm -rf /tmp/awscliv2.zip /tmp/awscli
  log "AWS CLI installed: $(aws --version)"
else
  log "AWS CLI already installed."
fi

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
log "Cloning CIE repo..."
if [[ -d "$APP_DIR" ]]; then
  log "Directory exists — pulling latest..."
  cd "$APP_DIR"
  sudo git pull origin main
else
  sudo git clone "$REPO_URL" "$APP_DIR"
  sudo chown -R "$USER:$USER" "$APP_DIR"
  cd "$APP_DIR"
fi

# ── Mount attached EBS data volume (if present) ───────────────────────────
# If an existing EBS was attached via --ebs-volume, it shows up as /dev/xvdf
# (or /dev/nvme1n1 on Nitro instances). We mount it to /opt/cie-data.
log "Setting up persistent data directory..."

DATA_DEVICE=""
if [[ -b /dev/nvme1n1 ]]; then
  DATA_DEVICE="/dev/nvme1n1"
elif [[ -b /dev/xvdf ]]; then
  DATA_DEVICE="/dev/xvdf"
fi

if [[ -n "$DATA_DEVICE" ]]; then
  log "Found attached EBS data volume: ${DATA_DEVICE}"

  # Check if it already has a filesystem
  FS_TYPE=$(sudo blkid -o value -s TYPE "$DATA_DEVICE" 2>/dev/null || true)
  if [[ -z "$FS_TYPE" ]]; then
    log "No filesystem found — formatting as ext4..."
    sudo mkfs.ext4 -L cie-data "$DATA_DEVICE"
  else
    log "Existing ${FS_TYPE} filesystem detected — preserving data."
  fi

  sudo mkdir -p "$DATA_DIR"
  sudo mount "$DATA_DEVICE" "$DATA_DIR"

  # Add to fstab for auto-mount on reboot (idempotent)
  if ! grep -q "$DATA_DIR" /etc/fstab; then
    echo "LABEL=cie-data ${DATA_DIR} ext4 defaults,nofail 0 2" | sudo tee -a /etc/fstab >/dev/null
  fi
  log "EBS data volume mounted at ${DATA_DIR}"
else
  log "No attached EBS data volume — using root volume for data."
  sudo mkdir -p "$DATA_DIR"
fi

sudo mkdir -p "$DATA_DIR"/{postgres,redis,uploads}
sudo chown -R "$USER:$USER" "$DATA_DIR"

# ── Collect credentials ───────────────────────────────────────────────────
# Get region from instance metadata (IMDSv2)
IMDS_TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
INSTANCE_REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "us-east-1")

# Generate secrets that don't exist yet
POSTGRES_PASSWORD=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

# Read API keys from SSM if already stored, otherwise prompt
log "Checking SSM for pre-stored API keys..."

DEEPGRAM_KEY=$(aws ssm get-parameter \
  --region "$INSTANCE_REGION" \
  --name "/cie/secrets/deepgram-api-key" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text 2>/dev/null || true)

OPENAI_KEY=$(aws ssm get-parameter \
  --region "$INSTANCE_REGION" \
  --name "/cie/secrets/openai-api-key" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text 2>/dev/null || true)

if [[ -z "$DEEPGRAM_KEY" ]]; then
  echo ""
  read -rp "Enter your Deepgram API key (https://console.deepgram.com): " DEEPGRAM_KEY
  [[ -z "$DEEPGRAM_KEY" ]] && fail "Deepgram API key is required"
else
  log "Deepgram API key loaded from SSM."
fi

if [[ -z "$OPENAI_KEY" ]]; then
  echo ""
  read -rp "Enter your OpenAI API key (https://platform.openai.com/api-keys): " OPENAI_KEY
  [[ -z "$OPENAI_KEY" ]] && fail "OpenAI API key is required"
else
  log "OpenAI API key loaded from SSM."
fi

# Check if JWT secret exists in SSM, otherwise use generated one
EXISTING_JWT=$(aws ssm get-parameter \
  --region "$INSTANCE_REGION" \
  --name "/cie/secrets/jwt-secret" \
  --with-decryption \
  --query 'Parameter.Value' \
  --output text 2>/dev/null || true)

if [[ -n "$EXISTING_JWT" ]]; then
  JWT_SECRET="$EXISTING_JWT"
  log "JWT secret loaded from SSM."
fi

# ── Store secrets in SSM Parameter Store (SecureString, KMS encrypted) ────
log "Storing secrets in SSM Parameter Store..."

store_secret() {
  local name="$1" value="$2"
  aws ssm put-parameter \
    --region "$INSTANCE_REGION" \
    --name "$name" \
    --value "$value" \
    --type "SecureString" \
    --overwrite >/dev/null 2>&1 || \
  aws ssm put-parameter \
    --region "$INSTANCE_REGION" \
    --name "$name" \
    --value "$value" \
    --type "SecureString" >/dev/null
  log "  Stored: $name"
}

store_secret "/cie/secrets/postgres-password" "$POSTGRES_PASSWORD"
store_secret "/cie/secrets/jwt-secret"        "$JWT_SECRET"
store_secret "/cie/secrets/deepgram-api-key"  "$DEEPGRAM_KEY"
store_secret "/cie/secrets/openai-api-key"    "$OPENAI_KEY"

# Store non-secret config in SSM (for boot-time reconstruction)
aws ssm put-parameter \
  --region "$INSTANCE_REGION" \
  --name "/cie/config/s3-bucket" \
  --value "$S3_BUCKET" \
  --type "String" \
  --overwrite >/dev/null 2>&1 || \
aws ssm put-parameter \
  --region "$INSTANCE_REGION" \
  --name "/cie/config/s3-bucket" \
  --value "$S3_BUCKET" \
  --type "String" >/dev/null

log "All secrets stored in SSM (SecureString, KMS encrypted)."

# ── Create SSM secrets-pull script (runs on every boot) ──────────────────
log "Setting up SSM secrets-pull script..."
sudo mkdir -p /etc/cie
sudo tee /usr/local/bin/cie-pull-secrets >/dev/null <<'SCRIPT'
#!/usr/bin/env bash
# Pull secrets from SSM Parameter Store and write /etc/cie/env
# Called by systemd on every boot, before cie.service starts.
# If SSM is unreachable, falls back to existing /etc/cie/env.
set -euo pipefail

IMDS_TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region)

get_secret() {
  aws ssm get-parameter \
    --region "$REGION" \
    --name "$1" \
    --with-decryption \
    --query 'Parameter.Value' \
    --output text
}

get_config() {
  aws ssm get-parameter \
    --region "$REGION" \
    --name "$1" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null || echo "$2"
}

POSTGRES_PASSWORD=$(get_secret "/cie/secrets/postgres-password")
JWT_SECRET=$(get_secret "/cie/secrets/jwt-secret")
DEEPGRAM_API_KEY=$(get_secret "/cie/secrets/deepgram-api-key")
OPENAI_API_KEY=$(get_secret "/cie/secrets/openai-api-key")

S3_BUCKET=$(get_config "/cie/config/s3-bucket" "")

cat > /etc/cie/env <<EOF
# CIE credentials — pulled from SSM Parameter Store
# Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)
# Source: SSM SecureString (KMS encrypted at rest)

POSTGRES_DB=cie
POSTGRES_USER=cie
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DATABASE_URL=postgresql://cie:${POSTGRES_PASSWORD}@postgres:5432/cie

REDIS_URL=redis://redis:6379/0

JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256

TRANSCRIPTION_PROVIDER=deepgram
DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY}

OPENAI_API_KEY=${OPENAI_API_KEY}
LLM_MODEL=gpt-4o
LLM_FALLBACK_MODEL=gpt-4o

UPLOAD_DIR=/app/uploads
MAX_FILE_SIZE_MB=100
S3_BUCKET=${S3_BUCKET}
S3_REGION=${REGION}

CORS_ORIGINS=["*"]
EOF

chmod 600 /etc/cie/env
chown root:root /etc/cie/env

echo "[cie] Secrets pulled from SSM → /etc/cie/env"
SCRIPT
sudo chmod +x /usr/local/bin/cie-pull-secrets

# ── Write initial /etc/cie/env (first boot, before SSM pull is wired up) ──
log "Writing initial /etc/cie/env..."
sudo /usr/local/bin/cie-pull-secrets
log "Credentials written to /etc/cie/env (mode 600, root-only)."

# ── Create docker-compose.prod.yml ────────────────────────────────────────
log "Writing production docker-compose..."
cat > "$APP_DIR/docker-compose.prod.yml" <<'COMPOSE_EOF'
version: "3.9"

services:
  postgres:
    image: postgres:16-alpine
    restart: unless-stopped
    env_file:
      - /etc/cie/env
    environment:
      POSTGRES_DB: cie
      POSTGRES_USER: cie
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - /opt/cie-data/postgres:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-cie}"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy volatile-lru
    volumes:
      - /opt/cie-data/redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5

  cie-api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "8000:8000"
    env_file:
      - /etc/cie/env
    volumes:
      - /opt/cie-data/uploads:/app/uploads
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  cie-worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
    restart: unless-stopped
    env_file:
      - /etc/cie/env
    volumes:
      - /opt/cie-data/uploads:/app/uploads
    depends_on:
      postgres: {condition: service_healthy}
      redis: {condition: service_healthy}
    command: celery -A app.tasks worker --loglevel=info --concurrency=4 --max-tasks-per-child=100 -Q cie,default
COMPOSE_EOF

# ── Create SSM IP-update script (runs on every boot for spot resume) ──────
log "Setting up SSM IP-update script..."
sudo tee /usr/local/bin/cie-update-ssm-ip >/dev/null <<'SCRIPT'
#!/usr/bin/env bash
# Update /cie/private-ip in SSM Parameter Store with current private IP.
# Called by systemd on every boot so PMS always has the right address.
set -e

IMDS_TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60")
PRIVATE_IP=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
  http://169.254.169.254/latest/meta-data/local-ipv4)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region)

aws ssm put-parameter \
  --region "$REGION" \
  --name "/cie/private-ip" \
  --value "$PRIVATE_IP" \
  --type "String" \
  --overwrite >/dev/null

echo "[cie] SSM /cie/private-ip updated to ${PRIVATE_IP}"
SCRIPT
sudo chmod +x /usr/local/bin/cie-update-ssm-ip

# ── Create systemd services ──────────────────────────────────────────────

# 1. SSM IP update (runs on every boot)
sudo tee /etc/systemd/system/cie-update-ip.service >/dev/null <<EOF
[Unit]
Description=CIE — Update private IP in SSM Parameter Store
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/cie-update-ssm-ip

[Install]
WantedBy=multi-user.target
EOF

# 2. SSM secrets pull (runs on every boot — refreshes /etc/cie/env from SSM)
sudo tee /etc/systemd/system/cie-pull-secrets.service >/dev/null <<EOF
[Unit]
Description=CIE — Pull secrets from SSM Parameter Store
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/cie-pull-secrets

[Install]
WantedBy=multi-user.target
EOF

# 3. Main CIE service (depends on IP update + secrets pull)
log "Setting up systemd service..."
sudo tee /etc/systemd/system/cie.service >/dev/null <<EOF
[Unit]
Description=CIE — Conversation Intelligence Engine
Requires=docker.service
Wants=cie-update-ip.service cie-pull-secrets.service
After=docker.service cie-update-ip.service cie-pull-secrets.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=${APP_DIR}
EnvironmentFile=/etc/cie/env
ExecStart=/usr/bin/docker compose -f docker-compose.prod.yml up -d
ExecStop=/usr/bin/docker compose -f docker-compose.prod.yml down
ExecReload=/usr/bin/docker compose -f docker-compose.prod.yml up -d --build
TimeoutStartSec=300

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable cie-update-ip.service
sudo systemctl enable cie-pull-secrets.service
sudo systemctl enable cie.service

# ── Update SSM with private IP ────────────────────────────────────────────
log "Publishing private IP to SSM..."
sudo systemctl start cie-update-ip.service || log "WARNING: SSM IP update failed (IAM role may need ssm:PutParameter)"

# ── Start services ─────────────────────────────────────────────────────────
log "Starting services..."
cd "$APP_DIR"
sudo systemctl start cie.service

# Wait for postgres
log "Waiting for PostgreSQL..."
for i in $(seq 1 30); do
  if sudo docker compose -f docker-compose.prod.yml exec -T postgres pg_isready -U cie &>/dev/null; then
    break
  fi
  sleep 2
done

# ── Run migrations ─────────────────────────────────────────────────────────
log "Running Alembic migrations..."
sudo docker compose -f docker-compose.prod.yml exec -T cie-api alembic upgrade head

# ── Verify health ──────────────────────────────────────────────────────────
log "Verifying health endpoint..."
for i in $(seq 1 15); do
  if curl -sf http://localhost:8000/health &>/dev/null; then
    log "Health check passed!"
    break
  fi
  if [[ $i -eq 15 ]]; then
    log "WARNING: Health check did not pass after 30s. Check: sudo docker compose -f docker-compose.prod.yml logs cie-api"
  fi
  sleep 2
done

# ── Done ──────────────────────────────────────────────────────────────────
PRIVATE_IP=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
  http://169.254.169.254/latest/meta-data/local-ipv4 2>/dev/null || echo "<private-ip>")

cat <<EOF

============================================================
  CIE is running!
============================================================

  Private IP:    ${PRIVATE_IP}
  API:           http://${PRIVATE_IP}:8000
  Health:        http://${PRIVATE_IP}:8000/health
  SSM Parameter: /cie/private-ip → ${PRIVATE_IP}

  S3 Bucket: ${S3_BUCKET}
  Region:    ${INSTANCE_REGION}

  Secrets:     SSM Parameter Store (SecureString, KMS encrypted)
  Local cache: /etc/cie/env (pulled from SSM on every boot)
  Data:        /opt/cie-data/ (persistent on EBS)

  SSM Parameters:
    /cie/private-ip                 (String)
    /cie/secrets/postgres-password  (SecureString)
    /cie/secrets/jwt-secret         (SecureString)
    /cie/secrets/deepgram-api-key   (SecureString)
    /cie/secrets/openai-api-key     (SecureString)
    /cie/config/s3-bucket           (String)

  PMS integration:
    PMS reads CIE address from SSM:
      aws ssm get-parameter --name /cie/private-ip --query Parameter.Value --output text

  Useful commands:
    cd ${APP_DIR}
    sudo systemctl status cie             # service status
    sudo systemctl restart cie            # restart all
    sudo systemctl reload cie             # rebuild + restart
    sudo docker compose -f docker-compose.prod.yml logs -f   # follow logs

  To rotate a secret:
    aws ssm put-parameter --name /cie/secrets/<key> --value <new> --type SecureString --overwrite
    sudo /usr/local/bin/cie-pull-secrets   # refresh local env
    sudo systemctl restart cie             # apply

  Boot sequence:
    1. cie-update-ip.service  → publishes private IP to SSM
    2. cie-pull-secrets.service → pulls secrets from SSM → /etc/cie/env
    3. cie.service → starts Docker containers

============================================================
EOF
