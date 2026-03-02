#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# SalesLens — Provision a t3.medium spot instance in ap-south-1 (Mumbai)
#
# Creates:
#   - Security group (SSH, HTTP, HTTPS, App:8000, Frontend:3000)
#   - 30 GB gp3 EBS volume
#   - S3 bucket  saleslens-recordings-<random>
#   - IAM role + instance profile with scoped S3 access
#   - Spot instance running Ubuntu 24.04 LTS
#
# Usage:
#   ./provision-spot.sh              # provision everything
#   ./provision-spot.sh --dry-run    # print what would happen, do nothing
#
# Requires: aws cli v2, configured credentials with admin-level access.
# ---------------------------------------------------------------------------
set -euo pipefail

REGION="ap-south-1"
INSTANCE_TYPE="t3.medium"
VOLUME_SIZE=30
KEY_NAME="${SALESLENS_KEY_NAME:-saleslens-key}"
RANDOM_SUFFIX="$(head -c 4 /dev/urandom | xxd -p)"
BUCKET_NAME="saleslens-recordings-${RANDOM_SUFFIX}"
SG_NAME="saleslens-sg-${RANDOM_SUFFIX}"
ROLE_NAME="saleslens-ec2-role-${RANDOM_SUFFIX}"
PROFILE_NAME="saleslens-ec2-profile-${RANDOM_SUFFIX}"
DRY_RUN=false

# ── Parse flags ──────────────────────────────────────────────────────────────
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    *) echo "Unknown argument: $arg"; exit 1 ;;
  esac
done

log()  { echo "[saleslens] $*"; }
fail() { echo "[saleslens] ERROR: $*" >&2; exit 1; }

# ── Preflight ────────────────────────────────────────────────────────────────
command -v aws  >/dev/null 2>&1 || fail "aws CLI not found. Install: https://aws.amazon.com/cli/"
command -v jq   >/dev/null 2>&1 || fail "jq not found. Install: sudo apt install jq"

aws sts get-caller-identity >/dev/null 2>&1 || fail "AWS credentials not configured. Run: aws configure"

# ── Resolve Ubuntu 24.04 LTS AMI ────────────────────────────────────────────
log "Looking up Ubuntu 24.04 LTS AMI in ${REGION}..."
AMI_ID=$(aws ec2 describe-images \
  --region "$REGION" \
  --owners 099720109477 \
  --filters \
    "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*" \
    "Name=state,Values=available" \
  --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
  --output text 2>/dev/null) || true

if [[ -z "$AMI_ID" || "$AMI_ID" == "None" ]]; then
  # Fallback: try the older ssd naming convention
  AMI_ID=$(aws ec2 describe-images \
    --region "$REGION" \
    --owners 099720109477 \
    --filters \
      "Name=name,Values=ubuntu/images/hvm-ssd/ubuntu-noble-24.04-amd64-server-*" \
      "Name=state,Values=available" \
    --query 'sort_by(Images, &CreationDate)[-1].ImageId' \
    --output text)
fi

[[ -z "$AMI_ID" || "$AMI_ID" == "None" ]] && fail "Could not find Ubuntu 24.04 AMI in ${REGION}"
log "AMI: ${AMI_ID}"

# ── Dry-run summary ─────────────────────────────────────────────────────────
if $DRY_RUN; then
  cat <<EOF

=== DRY RUN — nothing will be created ===

Region:            ${REGION}
Instance type:     ${INSTANCE_TYPE} (spot)
AMI:               ${AMI_ID}
Volume:            ${VOLUME_SIZE} GB gp3
S3 bucket:         ${BUCKET_NAME}
Security group:    ${SG_NAME}
IAM role:          ${ROLE_NAME}
Key pair:          ${KEY_NAME}

Ports opened:      22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (API), 3000 (Frontend)
EOF
  exit 0
fi

# ── Get default VPC ──────────────────────────────────────────────────────────
log "Resolving default VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
  --region "$REGION" \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

[[ -z "$VPC_ID" || "$VPC_ID" == "None" ]] && fail "No default VPC found in ${REGION}"
log "VPC: ${VPC_ID}"

# ── Security Group ───────────────────────────────────────────────────────────
log "Creating security group: ${SG_NAME}..."
SG_ID=$(aws ec2 create-security-group \
  --region "$REGION" \
  --group-name "$SG_NAME" \
  --description "SalesLens — SSH, HTTP(S), App, Frontend" \
  --vpc-id "$VPC_ID" \
  --query 'GroupId' \
  --output text)

for PORT in 22 80 443 8000 3000; do
  aws ec2 authorize-security-group-ingress \
    --region "$REGION" \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port "$PORT" \
    --cidr 0.0.0.0/0 >/dev/null
done
log "Security group: ${SG_ID}"

# ── S3 Bucket ────────────────────────────────────────────────────────────────
log "Creating S3 bucket: ${BUCKET_NAME}..."
aws s3api create-bucket \
  --bucket "$BUCKET_NAME" \
  --region "$REGION" \
  --create-bucket-configuration LocationConstraint="$REGION" >/dev/null

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" >/dev/null

log "S3 bucket created: ${BUCKET_NAME}"

# ── IAM Role + Instance Profile ─────────────────────────────────────────────
log "Creating IAM role: ${ROLE_NAME}..."

TRUST_POLICY=$(cat <<'POLICY'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ec2.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
POLICY
)

aws iam create-role \
  --role-name "$ROLE_NAME" \
  --assume-role-policy-document "$TRUST_POLICY" \
  --description "SalesLens EC2 role — S3 access" >/dev/null

S3_POLICY=$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "s3:GetObject",
      "s3:PutObject",
      "s3:DeleteObject",
      "s3:ListBucket"
    ],
    "Resource": [
      "arn:aws:s3:::${BUCKET_NAME}",
      "arn:aws:s3:::${BUCKET_NAME}/*"
    ]
  }]
}
POLICY
)

aws iam put-role-policy \
  --role-name "$ROLE_NAME" \
  --policy-name "saleslens-s3-access" \
  --policy-document "$S3_POLICY" >/dev/null

aws iam create-instance-profile \
  --instance-profile-name "$PROFILE_NAME" >/dev/null

aws iam add-role-to-instance-profile \
  --instance-profile-name "$PROFILE_NAME" \
  --role-name "$ROLE_NAME" >/dev/null

# IAM propagation delay
log "Waiting for IAM profile to propagate..."
sleep 10

# ── Check / create key pair ──────────────────────────────────────────────────
if ! aws ec2 describe-key-pairs --region "$REGION" --key-names "$KEY_NAME" >/dev/null 2>&1; then
  log "Creating key pair: ${KEY_NAME}..."
  aws ec2 create-key-pair \
    --region "$REGION" \
    --key-name "$KEY_NAME" \
    --query 'KeyMaterial' \
    --output text > "${KEY_NAME}.pem"
  chmod 600 "${KEY_NAME}.pem"
  log "Private key saved to: ${KEY_NAME}.pem"
else
  log "Key pair '${KEY_NAME}' already exists — reusing."
fi

# ── Launch Spot Instance ─────────────────────────────────────────────────────
log "Launching spot instance..."

INSTANCE_ID=$(aws ec2 run-instances \
  --region "$REGION" \
  --image-id "$AMI_ID" \
  --instance-type "$INSTANCE_TYPE" \
  --key-name "$KEY_NAME" \
  --security-group-ids "$SG_ID" \
  --iam-instance-profile "Name=${PROFILE_NAME}" \
  --instance-market-options 'MarketType=spot,SpotOptions={SpotInstanceType=persistent,InstanceInterruptionBehavior=stop}' \
  --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":${VOLUME_SIZE},\"VolumeType\":\"gp3\",\"DeleteOnTermination\":true}}]" \
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=saleslens},{Key=Project,Value=saleslens},{Key=BucketName,Value=${BUCKET_NAME}}]" \
  --query 'Instances[0].InstanceId' \
  --output text)

log "Instance launched: ${INSTANCE_ID}"
log "Waiting for instance to enter running state..."

aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

PUBLIC_IP=$(aws ec2 describe-instances \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

# ── Save resource IDs for teardown ──────────────────────────────────────────
RESOURCE_FILE="saleslens-resources-${RANDOM_SUFFIX}.env"
cat > "$RESOURCE_FILE" <<EOF
# SalesLens provisioned resources — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)
REGION=${REGION}
INSTANCE_ID=${INSTANCE_ID}
SG_ID=${SG_ID}
SG_NAME=${SG_NAME}
BUCKET_NAME=${BUCKET_NAME}
ROLE_NAME=${ROLE_NAME}
PROFILE_NAME=${PROFILE_NAME}
KEY_NAME=${KEY_NAME}
PUBLIC_IP=${PUBLIC_IP}
RANDOM_SUFFIX=${RANDOM_SUFFIX}
EOF

# ── Done ─────────────────────────────────────────────────────────────────────
cat <<EOF

============================================================
  SalesLens infrastructure provisioned successfully!
============================================================

  Instance ID:   ${INSTANCE_ID}
  Public IP:     ${PUBLIC_IP}
  S3 Bucket:     ${BUCKET_NAME}
  Security Group:${SG_ID}
  IAM Role:      ${ROLE_NAME}
  Region:        ${REGION}

  Resource file:  ${RESOURCE_FILE}

  Next steps:
    1. SSH into the instance:
       ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP}

    2. Run the setup script on the instance:
       scp -i ${KEY_NAME}.pem infra/setup-instance.sh ubuntu@${PUBLIC_IP}:~
       ssh -i ${KEY_NAME}.pem ubuntu@${PUBLIC_IP} 'bash setup-instance.sh ${BUCKET_NAME}'

    3. Access the app:
       API:      http://${PUBLIC_IP}:8000
       Frontend: http://${PUBLIC_IP}:3000

  To tear down:
    ./infra/teardown.sh ${RESOURCE_FILE}
============================================================
EOF
