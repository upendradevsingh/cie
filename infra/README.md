# CIE — Infrastructure

Deploy CIE on a single AWS spot instance in us-east-1. Private-IP only — PMS discovers CIE via SSM Parameter Store.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  EC2 Spot Instance (t3.medium, us-east-1d)                  │
│  Private IP only — no public internet exposure              │
│                                                             │
│  ┌──────────┐  ┌───────────────┐                            │
│  │ CIE API  │  │ Celery Worker │   ← Docker containers      │
│  │  :8000   │  │  (4 workers)  │                            │
│  └────┬─────┘  └───────┬───────┘                            │
│       │                │                                    │
│  ┌────┴────┐     ┌─────┴─────┐                              │
│  │Postgres │     │   Redis   │   ← Docker containers        │
│  └─────────┘     └───────────┘                              │
│                                                             │
│  systemd: cie.service + cie-update-ip.service               │
│  Credentials: /etc/cie/env (root:root, mode 600)            │
├─────────────────────────────────────────────────────────────┤
│  EBS Volume (30GB gp3) — persistent across spot stop/start  │
│  /opt/cie-data/{postgres,redis,uploads}                     │
└──────────────┬──────────────────────────────────────────────┘
               │ VPC internal
               ▼
┌──────────────────────┐     ┌─────────────────┐
│  pms-backend-prod    │     │   S3 Bucket     │
│  (reads /cie/private │     │  cie-recordings │
│   -ip from SSM)      │     └─────────────────┘
└──────────────────────┘
```

## Service Discovery

PMS finds CIE via **SSM Parameter Store** (free, no ALB/EIP needed):

```bash
# PMS reads CIE address at startup or on-demand
CIE_URL="http://$(aws ssm get-parameter --name /cie/private-ip --query Parameter.Value --output text):8000"
```

On spot resume, `cie-update-ip.service` automatically updates the SSM parameter with the new private IP before CIE starts.

## Credential Management

Secrets stored in `/etc/cie/env` on the instance (root:root, mode 600). Loaded by systemd `EnvironmentFile`. Never in the repo.

```bash
sudo nano /etc/cie/env       # edit
sudo systemctl restart cie   # apply
```

## Quick Start

### Reusing existing resources

```bash
cd infra

# Use existing EBS, security group, key pair, and IAM profile
./provision-spot.sh \
  --ebs-volume vol-023714ea3f5af0da5 \
  --sg sg-0dde867d87ef01a77 \
  --key pms-backend-key-1752795223 \
  --iam-profile saleslens-ec2-profile-b96d39df

# Connect via SSM (no SSH key needed)
aws ssm start-session --target <INSTANCE_ID>

# Or SSH from within VPC
ssh -i ~/.ssh/pms-backend-key-1752795223.pem ubuntu@<PRIVATE_IP>

# Run setup on the instance
bash setup-instance.sh <S3_BUCKET>
```

### Fresh provision

```bash
./provision-spot.sh   # creates everything from scratch
```

## Scripts

### `provision-spot.sh`

| Flag | Description | Example |
|------|-------------|---------|
| `--ebs-volume` | Attach existing EBS (must be in same AZ) | `vol-023714ea3f5af0da5` |
| `--sg` | Reuse existing security group | `sg-0dde867d87ef01a77` |
| `--key` | Reuse existing key pair | `pms-backend-key-1752795223` |
| `--iam-profile` | Reuse existing IAM instance profile | `saleslens-ec2-profile-b96d39df` |
| `--subnet` | Specific subnet | `subnet-abc123` |
| `--region` | Override region (default: us-east-1) | `ap-south-1` |
| `--dry-run` | Print plan, create nothing | |

### `setup-instance.sh`

Run ON the instance. Installs Docker, clones repo, collects API keys, stores in `/etc/cie/env`, mounts EBS, sets up systemd, starts services.

### `deploy-to-ec2.sh`

Pull latest code and redeploy. Reads CIE IP from SSM or argument.

```bash
./deploy-to-ec2.sh --ssm ~/.ssh/key.pem          # auto-discover IP
./deploy-to-ec2.sh 10.0.1.42 ~/.ssh/key.pem      # explicit IP
```

### `teardown.sh`

```bash
./teardown.sh cie-resources-xxx.env               # instance + SSM only (preserves SG, IAM, EBS, S3)
./teardown.sh cie-resources-xxx.env --delete-all  # everything
```

## Cost (monthly, us-east-1)

| Resource | Cost |
|----------|------|
| t3.medium spot | ~$6-8 |
| EBS 30GB gp3 | ~$2.40 |
| S3 (10 GB) | ~$0.23 |
| SSM Parameter Store | Free |
| Data transfer (VPC internal) | Free |
| **Infra total** | **~$9-11/mo** |
| Deepgram (1K calls) | ~$43 |
| OpenAI gpt-4o-mini | ~$2-10 |
| **All-in total** | **~$54-64/mo** |

## Troubleshooting

```bash
# Service status
sudo systemctl status cie
sudo systemctl status cie-update-ip

# Container logs
cd /opt/cie
sudo docker compose -f docker-compose.prod.yml logs -f
sudo docker compose -f docker-compose.prod.yml ps

# Check SSM parameter
aws ssm get-parameter --name /cie/private-ip --region us-east-1

# Verify credentials
sudo stat /etc/cie/env
```
