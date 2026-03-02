# SalesLens — One-Command Deployment

Deploy SalesLens to EC2 in 60 seconds.

## Quick Deploy

```bash
# Make script executable
chmod +x infra/deploy-to-ec2.sh

# Deploy (replace with your EC2 IP and SSH key path)
./infra/deploy-to-ec2.sh <EC2_IP> ~/.ssh/your-key.pem
```

**Tip:** Create a local `deploy.sh` for quick deployments (already in `.gitignore`):

```bash
#!/usr/bin/env bash
./infra/deploy-to-ec2.sh YOUR_EC2_IP ~/.ssh/your-key.pem
```

Then just run `./deploy.sh` for one-command deploys without typing IPs/paths.

That's it! The script will:
- ✅ Pull `feat/enhanced-analysis` branch
- ✅ Run database migrations (including `sales_audit_keywords` column)
- ✅ Generate self-signed SSL certificate
- ✅ Configure nginx (port 443 only)
- ✅ Rebuild backend + worker containers
- ✅ Deploy frontend
- ✅ Route `/api/` → backend, `/` → frontend

## Access

After deployment:

```
🌐 https://<YOUR_EC2_IP>
```

**Note:** Browser will warn about self-signed certificate — click "Advanced" → "Proceed" to accept.

## Update Deployment

Same command updates code and restarts services:

```bash
./infra/deploy-to-ec2.sh <EC2_IP> ~/.ssh/your-key.pem
```

## View Logs

```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP> \
  'cd /opt/saleslens && sudo docker compose logs -f'
```

## Troubleshooting

**Services not starting?**
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP> \
  'cd /opt/saleslens && sudo docker compose ps'
```

**Restart services:**
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP> \
  'cd /opt/saleslens && sudo docker compose restart'
```

**Full rebuild:**
```bash
ssh -i ~/.ssh/your-key.pem ubuntu@<EC2_IP> \
  'cd /opt/saleslens && sudo docker compose down && sudo docker compose up -d --build'
```

**Check backend health:**
```bash
curl -k https://<EC2_IP>/health
```

## What's New in feat/enhanced-analysis

This deployment includes:
- 🔍 **Sales Audit Keywords** — 8-category keyword extraction (compliance violations, missed opportunities, pricing, competitors, pain points, commitment, objections, negative reactions)
- 🚨 **Escalation Detection** — Automatic flagging of legal threats, complaints, escalation language
- 💭 **Sentiment Analysis** — Positive/negative keyword extraction + overall call sentiment
- 🏷️ **Auto-tagging** — Topic tags like pricing_discussion, competitor_comparison, etc.
- ⚙️ **Prompt Templates** — Tenant-configurable LLM prompts (CRUD API + UI)
- 📊 **Enhanced UI** — New "Keywords" tab on call detail with collapsible categories

All features active after this deployment — upload a call to see them in action!
