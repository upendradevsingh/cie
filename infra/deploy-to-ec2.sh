#!/usr/bin/env bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CIE — Deploy update to EC2 instance
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Pulls latest code and redeploys. Credentials stay in /etc/cie/env.
#
# Usage:
#   ./deploy-to-ec2.sh <PRIVATE_IP> <SSH_KEY_PATH>
#   ./deploy-to-ec2.sh --ssm <SSH_KEY_PATH>     # reads IP from SSM
#
# Example:
#   ./deploy-to-ec2.sh 10.0.1.42 ~/.ssh/pms-backend-key-1752795223.pem
#   ./deploy-to-ec2.sh --ssm ~/.ssh/pms-backend-key-1752795223.pem
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -euo pipefail

REGION="${CIE_REGION:-us-east-1}"
TARGET_IP="${1:-}"
SSH_KEY="${2:-}"

# If --ssm flag, read IP from SSM Parameter Store
if [[ "$TARGET_IP" == "--ssm" ]]; then
  SSH_KEY="${2:-}"
  TARGET_IP=$(aws ssm get-parameter \
    --region "$REGION" \
    --name "/cie/private-ip" \
    --query 'Parameter.Value' \
    --output text 2>/dev/null) || { echo "ERROR: Could not read /cie/private-ip from SSM"; exit 1; }
  echo "Read CIE IP from SSM: ${TARGET_IP}"
fi

if [[ -z "$TARGET_IP" ]] || [[ -z "$SSH_KEY" ]]; then
  echo "Usage: $0 <PRIVATE_IP|--ssm> <SSH_KEY_PATH>"
  exit 1
fi

SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deploying CIE to $TARGET_IP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ─── 1. Pull latest code ──────────────────────────────────────────────
echo "Pulling latest code..."
ssh $SSH_OPTS ubuntu@$TARGET_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/cie
git fetch origin
git checkout main
git pull origin main
REMOTE_SCRIPT

# ─── 2. Verify credentials (self-heal from SSM if missing) ───────────
echo "Verifying credentials..."
ssh $SSH_OPTS ubuntu@$TARGET_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
if [[ ! -f /etc/cie/env ]]; then
  echo "WARNING: /etc/cie/env not found. Pulling from SSM..."
  if sudo /usr/local/bin/cie-pull-secrets; then
    echo "Secrets pulled from SSM successfully."
  else
    echo "ERROR: Cannot pull secrets from SSM. Run setup-instance.sh first."
    exit 1
  fi
fi
echo "Credentials file present ($(sudo stat -c '%a %U:%G' /etc/cie/env))"

# Verify SSM SecureString access
IMDS_TOKEN=$(curl -sX PUT "http://169.254.169.254/latest/api/token" \
  -H "X-aws-ec2-metadata-token-ttl-seconds: 60" 2>/dev/null || true)
REGION=$(curl -s -H "X-aws-ec2-metadata-token: $IMDS_TOKEN" \
  http://169.254.169.254/latest/meta-data/placement/region 2>/dev/null || echo "us-east-1")
if aws ssm get-parameter --region "$REGION" --name "/cie/secrets/jwt-secret" \
    --with-decryption --query 'Parameter.Value' --output text >/dev/null 2>&1; then
  echo "SSM SecureString access verified."
else
  echo "WARNING: Cannot decrypt SSM SecureString. Check IAM role has kms:Decrypt."
fi
REMOTE_SCRIPT

# ─── 3. Rebuild and restart via systemd ───────────────────────────────
echo "Rebuilding and restarting services..."
ssh $SSH_OPTS ubuntu@$TARGET_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/cie

# Rebuild containers with new code
sudo docker compose -f docker-compose.prod.yml build

# Restart via systemd (reads /etc/cie/env)
sudo systemctl restart cie

echo "Waiting for API health..."
for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/health >/dev/null 2>&1; then
    echo "API healthy"
    break
  fi
  if [ $i -eq 30 ]; then
    echo "WARNING: Health check did not pass after 60s"
    sudo docker compose -f docker-compose.prod.yml logs --tail=20 cie-api
    exit 1
  fi
  sleep 2
done
REMOTE_SCRIPT

# ─── 4. Run migrations ───────────────────────────────────────────────
echo "Running Alembic migrations..."
ssh $SSH_OPTS ubuntu@$TARGET_IP 'bash -s' <<'REMOTE_SCRIPT'
set -e
cd /opt/cie
sudo docker compose -f docker-compose.prod.yml exec -T cie-api alembic upgrade head
REMOTE_SCRIPT

# ─── 5. Verify ───────────────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Deployment complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  CIE API: http://$TARGET_IP:8000"
echo "  Health:  http://$TARGET_IP:8000/health"
echo ""
