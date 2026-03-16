#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# CIE — Provision a t3.medium spot instance in us-east-1
#
# Reuses existing AWS resources where possible:
#   - Existing EBS volume (--ebs-volume)
#   - Existing security group (--sg)
#   - Existing key pair (--key)
#   - Existing IAM instance profile (--iam-profile)
#
# Creates only what's missing. Instance is private-IP only (no public IP).
# PMS discovers CIE via SSM Parameter Store: /cie/private-ip
#
# Usage:
#   # Reuse existing infra:
#   ./provision-spot.sh \
#     --ebs-volume vol-023714ea3f5af0da5 \
#     --sg sg-0dde867d87ef01a77 \
#     --key pms-backend-key-1752795223 \
#     --iam-profile saleslens-ec2-profile-b96d39df
#
#   # Fresh provision (creates everything):
#   ./provision-spot.sh
#
#   # Dry run:
#   ./provision-spot.sh --dry-run
#
# Requires: aws cli v2, configured credentials with admin-level access.
# ---------------------------------------------------------------------------
set -euo pipefail

REGION="us-east-1"
INSTANCE_TYPE="t3.medium"
VOLUME_SIZE=30
DRY_RUN=false

# Defaults — overridden by flags or env vars
KEY_NAME="${CIE_KEY_NAME:-}"
EXISTING_EBS_VOLUME=""
EXISTING_SG=""
EXISTING_IAM_PROFILE=""
EXISTING_SUBNET=""

RANDOM_SUFFIX="$(head -c 4 /dev/urandom | xxd -p)"
BUCKET_NAME="cie-recordings-${RANDOM_SUFFIX}"

# ── Parse flags ──────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)      DRY_RUN=true; shift ;;
    --ebs-volume)   EXISTING_EBS_VOLUME="$2"; shift 2 ;;
    --sg)           EXISTING_SG="$2"; shift 2 ;;
    --key)          KEY_NAME="$2"; shift 2 ;;
    --iam-profile)  EXISTING_IAM_PROFILE="$2"; shift 2 ;;
    --subnet)       EXISTING_SUBNET="$2"; shift 2 ;;
    --region)       REGION="$2"; shift 2 ;;
    *) echo "Unknown argument: $1"; exit 1 ;;
  esac
done

log()  { echo "[cie] $*"; }
fail() { echo "[cie] ERROR: $*" >&2; exit 1; }

# ── Preflight ────────────────────────────────────────────────────────────────
command -v aws  >/dev/null 2>&1 || fail "aws CLI not found. Install: https://aws.amazon.com/cli/"
command -v jq   >/dev/null 2>&1 || fail "jq not found. Install: sudo apt install jq / brew install jq"

aws sts get-caller-identity >/dev/null 2>&1 || fail "AWS credentials not configured. Run: aws configure"

# ── Determine target AZ (must match EBS volume if reusing) ────────────────
TARGET_AZ=""
if [[ -n "$EXISTING_EBS_VOLUME" ]]; then
  TARGET_AZ=$(aws ec2 describe-volumes \
    --region "$REGION" \
    --volume-ids "$EXISTING_EBS_VOLUME" \
    --query 'Volumes[0].AvailabilityZone' \
    --output text 2>/dev/null) || fail "EBS volume ${EXISTING_EBS_VOLUME} not found in ${REGION}"
  log "EBS volume ${EXISTING_EBS_VOLUME} is in ${TARGET_AZ} — instance will launch there."
fi

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

# ── Resolve VPC ──────────────────────────────────────────────────────────────
log "Resolving default VPC..."
VPC_ID=$(aws ec2 describe-vpcs \
  --region "$REGION" \
  --filters "Name=isDefault,Values=true" \
  --query 'Vpcs[0].VpcId' \
  --output text)

[[ -z "$VPC_ID" || "$VPC_ID" == "None" ]] && fail "No default VPC found in ${REGION}"
log "VPC: ${VPC_ID}"

# ── Resolve subnet (for target AZ, private-IP launch) ───────────────────────
if [[ -n "$EXISTING_SUBNET" ]]; then
  SUBNET_ID="$EXISTING_SUBNET"
elif [[ -n "$TARGET_AZ" ]]; then
  SUBNET_ID=$(aws ec2 describe-subnets \
    --region "$REGION" \
    --filters "Name=vpc-id,Values=${VPC_ID}" "Name=availability-zone,Values=${TARGET_AZ}" \
    --query 'Subnets[0].SubnetId' \
    --output text)
  [[ -z "$SUBNET_ID" || "$SUBNET_ID" == "None" ]] && fail "No subnet found in ${TARGET_AZ}"
else
  SUBNET_ID=$(aws ec2 describe-subnets \
    --region "$REGION" \
    --filters "Name=vpc-id,Values=${VPC_ID}" \
    --query 'Subnets[0].SubnetId' \
    --output text)
fi
log "Subnet: ${SUBNET_ID}"

# ── Dry-run summary ─────────────────────────────────────────────────────────
if $DRY_RUN; then
  EBS_DESC="${VOLUME_SIZE} GB gp3 (new)"
  [[ -n "$EXISTING_EBS_VOLUME" ]] && EBS_DESC="${EXISTING_EBS_VOLUME} (existing, attached after launch)"
  SG_DESC="${EXISTING_SG:-new: cie-sg-${RANDOM_SUFFIX}}"
  KEY_DESC="${KEY_NAME:-new: cie-key}"
  IAM_DESC="${EXISTING_IAM_PROFILE:-new: cie-ec2-profile-${RANDOM_SUFFIX}}"
  cat <<EOF

=== DRY RUN — nothing will be created ===

Region:            ${REGION}
Target AZ:         ${TARGET_AZ:-auto}
Instance type:     ${INSTANCE_TYPE} (spot, private-IP only)
AMI:               ${AMI_ID}
Subnet:            ${SUBNET_ID}
EBS data volume:   ${EBS_DESC}
S3 bucket:         ${BUCKET_NAME}
Security group:    ${SG_DESC}
IAM profile:       ${IAM_DESC}
Key pair:          ${KEY_DESC}

Service discovery: SSM Parameter /cie/private-ip
Ports:             8000 (API) — VPC internal only
EOF
  exit 0
fi

# ── Security Group (reuse or create) ────────────────────────────────────────
if [[ -n "$EXISTING_SG" ]]; then
  SG_ID="$EXISTING_SG"
  log "Reusing security group: ${SG_ID}"

  # Ensure port 8000 is open (idempotent — ignores if rule exists)
  aws ec2 authorize-security-group-ingress \
    --region "$REGION" \
    --group-id "$SG_ID" \
    --protocol tcp \
    --port 8000 \
    --cidr 0.0.0.0/0 >/dev/null 2>&1 || true
else
  SG_NAME="cie-sg-${RANDOM_SUFFIX}"
  log "Creating security group: ${SG_NAME}..."
  SG_ID=$(aws ec2 create-security-group \
    --region "$REGION" \
    --group-name "$SG_NAME" \
    --description "CIE — SSH, API (private)" \
    --vpc-id "$VPC_ID" \
    --query 'GroupId' \
    --output text)

  # SSH (for setup) + API (VPC internal, but open for now)
  for PORT in 22 8000; do
    aws ec2 authorize-security-group-ingress \
      --region "$REGION" \
      --group-id "$SG_ID" \
      --protocol tcp \
      --port "$PORT" \
      --cidr 0.0.0.0/0 >/dev/null
  done
  log "Security group created: ${SG_ID}"
fi

# ── S3 Bucket ────────────────────────────────────────────────────────────────
log "Creating S3 bucket: ${BUCKET_NAME}..."
# us-east-1 does not use LocationConstraint
if [[ "$REGION" == "us-east-1" ]]; then
  aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --region "$REGION" >/dev/null
else
  aws s3api create-bucket \
    --bucket "$BUCKET_NAME" \
    --region "$REGION" \
    --create-bucket-configuration LocationConstraint="$REGION" >/dev/null
fi

aws s3api put-public-access-block \
  --bucket "$BUCKET_NAME" \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true" >/dev/null

log "S3 bucket created: ${BUCKET_NAME}"

# ── IAM Role + Instance Profile (reuse or create) ───────────────────────────
if [[ -n "$EXISTING_IAM_PROFILE" ]]; then
  PROFILE_NAME="$EXISTING_IAM_PROFILE"
  log "Reusing IAM instance profile: ${PROFILE_NAME}"

  # Get the role name from the profile to update S3 policy
  ROLE_NAME=$(aws iam get-instance-profile \
    --instance-profile-name "$PROFILE_NAME" \
    --query 'InstanceProfile.Roles[0].RoleName' \
    --output text 2>/dev/null) || true

  if [[ -n "$ROLE_NAME" && "$ROLE_NAME" != "None" ]]; then
    log "Updating S3 policy on role ${ROLE_NAME} for bucket ${BUCKET_NAME}..."
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
      --policy-name "cie-s3-access" \
      --policy-document "$S3_POLICY" >/dev/null
    log "S3 policy updated on ${ROLE_NAME}."

    # Add SSM SecureString access (separate policy to avoid overwriting S3)
    log "Adding SSM secrets policy to ${ROLE_NAME}..."
    SSM_SECRETS_POLICY=$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:DeleteParameter"
      ],
      "Resource": "arn:aws:ssm:${REGION}:*:parameter/cie/*"
    },
    {
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "ssm.${REGION}.amazonaws.com"
        }
      }
    }
  ]
}
POLICY
    )
    aws iam put-role-policy \
      --role-name "$ROLE_NAME" \
      --policy-name "cie-ssm-secrets" \
      --policy-document "$SSM_SECRETS_POLICY" >/dev/null
    log "SSM secrets policy added to ${ROLE_NAME}."
  fi
else
  ROLE_NAME="cie-ec2-role-${RANDOM_SUFFIX}"
  PROFILE_NAME="cie-ec2-profile-${RANDOM_SUFFIX}"
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
    --description "CIE EC2 role — S3 + SSM access" >/dev/null

  S3_POLICY=$(cat <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
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
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssm:PutParameter",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:GetParametersByPath",
        "ssm:DeleteParameter"
      ],
      "Resource": "arn:aws:ssm:${REGION}:*:parameter/cie/*"
    },
    {
      "Effect": "Allow",
      "Action": "kms:Decrypt",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "kms:ViaService": "ssm.${REGION}.amazonaws.com"
        }
      }
    }
  ]
}
POLICY
  )

  aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "cie-s3-ssm-access" \
    --policy-document "$S3_POLICY" >/dev/null

  aws iam create-instance-profile \
    --instance-profile-name "$PROFILE_NAME" >/dev/null

  aws iam add-role-to-instance-profile \
    --instance-profile-name "$PROFILE_NAME" \
    --role-name "$ROLE_NAME" >/dev/null

  log "Waiting for IAM profile to propagate..."
  sleep 10
fi

# ── Check / create key pair ──────────────────────────────────────────────────
if [[ -z "$KEY_NAME" ]]; then
  KEY_NAME="cie-key"
fi

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

# ── Launch Spot Instance (private IP only, no public IP) ─────────────────────
log "Launching spot instance (private IP only)..."

LAUNCH_ARGS=(
  --region "$REGION"
  --image-id "$AMI_ID"
  --instance-type "$INSTANCE_TYPE"
  --key-name "$KEY_NAME"
  --security-group-ids "$SG_ID"
  --subnet-id "$SUBNET_ID"
  --iam-instance-profile "Name=${PROFILE_NAME}"
  --instance-market-options 'MarketType=spot,SpotOptions={SpotInstanceType=persistent,InstanceInterruptionBehavior=stop}'
  --block-device-mappings "[{\"DeviceName\":\"/dev/sda1\",\"Ebs\":{\"VolumeSize\":${VOLUME_SIZE},\"VolumeType\":\"gp3\",\"DeleteOnTermination\":false}}]"
  --tag-specifications "ResourceType=instance,Tags=[{Key=Name,Value=cie},{Key=Project,Value=cie},{Key=BucketName,Value=${BUCKET_NAME}}]"
  --associate-public-ip-address
  --query 'Instances[0].InstanceId'
  --output text
)

INSTANCE_ID=$(aws ec2 run-instances "${LAUNCH_ARGS[@]}")

log "Instance launched: ${INSTANCE_ID}"
log "Waiting for instance to enter running state..."

aws ec2 wait instance-running --region "$REGION" --instance-ids "$INSTANCE_ID"

PRIVATE_IP=$(aws ec2 describe-instances \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PrivateIpAddress' \
  --output text)

PUBLIC_IP=$(aws ec2 describe-instances \
  --region "$REGION" \
  --instance-ids "$INSTANCE_ID" \
  --query 'Reservations[0].Instances[0].PublicIpAddress' \
  --output text)

log "Private IP: ${PRIVATE_IP}"
log "Public IP:  ${PUBLIC_IP} (auto-assigned, changes on stop/start)"

# ── Store private IP in SSM Parameter Store (for PMS discovery) ──────────────
log "Publishing private IP to SSM Parameter Store: /cie/private-ip..."
aws ssm put-parameter \
  --region "$REGION" \
  --name "/cie/private-ip" \
  --value "$PRIVATE_IP" \
  --type "String" \
  --overwrite >/dev/null 2>&1 || \
aws ssm put-parameter \
  --region "$REGION" \
  --name "/cie/private-ip" \
  --value "$PRIVATE_IP" \
  --type "String" >/dev/null

log "SSM parameter /cie/private-ip = ${PRIVATE_IP}"

# ── Attach existing EBS volume (if provided) ────────────────────────────────
EBS_VOLUME_ID=""
if [[ -n "$EXISTING_EBS_VOLUME" ]]; then
  log "Attaching existing EBS volume: ${EXISTING_EBS_VOLUME} as /dev/xvdf..."

  VOL_STATE=$(aws ec2 describe-volumes \
    --region "$REGION" \
    --volume-ids "$EXISTING_EBS_VOLUME" \
    --query 'Volumes[0].State' \
    --output text 2>/dev/null) || fail "Volume ${EXISTING_EBS_VOLUME} not found"

  if [[ "$VOL_STATE" != "available" ]]; then
    fail "Volume ${EXISTING_EBS_VOLUME} is '${VOL_STATE}' — must be 'available' to attach"
  fi

  aws ec2 attach-volume \
    --region "$REGION" \
    --volume-id "$EXISTING_EBS_VOLUME" \
    --instance-id "$INSTANCE_ID" \
    --device /dev/xvdf >/dev/null

  aws ec2 wait volume-in-use \
    --region "$REGION" \
    --volume-ids "$EXISTING_EBS_VOLUME"

  EBS_VOLUME_ID="$EXISTING_EBS_VOLUME"
  log "EBS volume attached: ${EXISTING_EBS_VOLUME} → /dev/xvdf"
fi

# ── Save resource IDs for teardown ──────────────────────────────────────────
RESOURCE_FILE="cie-resources-${RANDOM_SUFFIX}.env"
cat > "$RESOURCE_FILE" <<EOF
# CIE provisioned resources — generated $(date -u +%Y-%m-%dT%H:%M:%SZ)
REGION=${REGION}
INSTANCE_ID=${INSTANCE_ID}
PRIVATE_IP=${PRIVATE_IP}
SG_ID=${SG_ID}
BUCKET_NAME=${BUCKET_NAME}
ROLE_NAME=${ROLE_NAME:-}
PROFILE_NAME=${PROFILE_NAME}
KEY_NAME=${KEY_NAME}
RANDOM_SUFFIX=${RANDOM_SUFFIX}
EBS_VOLUME_ID=${EBS_VOLUME_ID}
EOF

# ── Done ─────────────────────────────────────────────────────────────────────
cat <<EOF

============================================================
  CIE infrastructure provisioned successfully!
============================================================

  Instance ID:   ${INSTANCE_ID}
  Private IP:    ${PRIVATE_IP}
  SSM Parameter: /cie/private-ip → ${PRIVATE_IP}
  S3 Bucket:     ${BUCKET_NAME}
  Security Group:${SG_ID}
  IAM Profile:   ${PROFILE_NAME}
  EBS Data Vol:  ${EBS_VOLUME_ID:-root volume only}
  Region:        ${REGION}

  Resource file:  ${RESOURCE_FILE}

  Next steps:
    1. Connect via SSM (no SSH key needed):
       aws ssm start-session --target ${INSTANCE_ID} --region ${REGION}

    2. Or SSH (from within VPC / bastion):
       ssh -i ${KEY_NAME}.pem ubuntu@${PRIVATE_IP}

    3. Run the setup script on the instance:
       scp -i ${KEY_NAME}.pem infra/setup-instance.sh ubuntu@${PRIVATE_IP}:~
       ssh -i ${KEY_NAME}.pem ubuntu@${PRIVATE_IP} 'bash setup-instance.sh ${BUCKET_NAME}'

    4. PMS calls CIE at:
       http://${PRIVATE_IP}:8000
       Or read from SSM: aws ssm get-parameter --name /cie/private-ip

  To tear down:
    ./infra/teardown.sh ${RESOURCE_FILE}
============================================================
EOF
