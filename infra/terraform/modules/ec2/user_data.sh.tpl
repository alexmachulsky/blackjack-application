#!/bin/bash
# ──────────────────────────────────────────────────────────────────────────────
# EC2 bootstrap — runs as root on first launch (Amazon Linux 2023)
#
# This script:
#   1. Installs Docker + Docker Compose v2
#   2. Clones the application repo
#   3. Fetches secrets from SSM Parameter Store
#   4. Writes .env (no plaintext secrets in this file — fetched at runtime)
#   5. Pulls Docker images from GHCR
#   6. Starts backend + frontend via Docker Compose (RDS replaces local postgres)
#   7. Registers a systemd service for auto-restart
# ──────────────────────────────────────────────────────────────────────────────
set -euo pipefail
exec > >(tee /var/log/user-data.log | logger -t user-data) 2>&1

echo "=== Starting user-data bootstrap ==="

# ── 1. Install Docker ─────────────────────────────────────────────────────────
dnf install -y docker git
systemctl enable docker
systemctl start docker
usermod -aG docker ec2-user

# ── 2. Install Docker Compose v2 plugin ───────────────────────────────────────
COMPOSE_VERSION="v2.24.7"
mkdir -p /usr/local/lib/docker/cli-plugins
curl -SL \
  "https://github.com/docker/compose/releases/download/$${COMPOSE_VERSION}/docker-compose-linux-x86_64" \
  -o /usr/local/lib/docker/cli-plugins/docker-compose
chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
ln -sf /usr/local/lib/docker/cli-plugins/docker-compose /usr/local/bin/docker-compose

echo "Docker Compose version: $$(docker compose version)"

# ── 3. Clone application ──────────────────────────────────────────────────────
APP_DIR="/opt/${app_name}"
mkdir -p "$$APP_DIR"
git clone --depth 1 https://github.com/${ghcr_owner}/${app_name}.git "$$APP_DIR"
cd "$$APP_DIR"

# ── 4. Fetch secrets from SSM ─────────────────────────────────────────────────
AWS_REGION="${aws_region}"

echo "Fetching secrets from SSM..."
DB_PASSWORD=$$(
  aws ssm get-parameter \
    --name "${db_password_ssm_path}" \
    --with-decryption \
    --query Parameter.Value \
    --output text \
    --region "$$AWS_REGION"
)

SECRET_KEY=$$(
  aws ssm get-parameter \
    --name "${secret_key_ssm_path}" \
    --with-decryption \
    --query Parameter.Value \
    --output text \
    --region "$$AWS_REGION"
)

echo "Secrets fetched successfully."

# ── 5. Write .env ─────────────────────────────────────────────────────────────
# DATABASE_URL points to RDS — not the Compose postgres container
cat > "$$APP_DIR/.env" <<EOF
DATABASE_URL=postgresql://${db_username}:$${DB_PASSWORD}@${db_host}:${db_port}/${db_name}
POSTGRES_USER=${db_username}
POSTGRES_PASSWORD=$${DB_PASSWORD}
POSTGRES_DB=${db_name}
SECRET_KEY=$${SECRET_KEY}
ACCESS_TOKEN_EXPIRE_MINUTES=60
INITIAL_BALANCE=1000.0
LOG_LEVEL=WARNING
ENVIRONMENT=production
CORS_ORIGINS=http://localhost
EOF

chmod 600 "$$APP_DIR/.env"

# ── 6. Pull images ────────────────────────────────────────────────────────────
# GHCR packages for this public repo are publicly pullable — no auth needed
docker pull ${backend_image}:${image_tag}
docker pull ${frontend_image}:${image_tag}

# Tag as :current so the Compose files reference a stable local tag
docker tag ${backend_image}:${image_tag} blackjack-application_backend:latest
docker tag ${frontend_image}:${image_tag} blackjack-application_frontend:latest

# ── 7. Start application ──────────────────────────────────────────────────────
# Use the AWS override to:
#   - Remove the backend→postgres depends_on (we use RDS, not the Compose service)
#   - Prevent the postgres container from starting
cd "$$APP_DIR"
docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f infra/docker-compose.aws.yml \
  up -d backend frontend

echo "Application started."

# ── 8. Systemd service for auto-restart on reboot ─────────────────────────────
cat > /etc/systemd/system/blackjack.service <<'UNIT'
[Unit]
Description=Blackjack Application
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/${app_name}
ExecStart=/usr/local/bin/docker-compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f infra/docker-compose.aws.yml \
  up -d backend frontend
ExecStop=/usr/local/bin/docker-compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f infra/docker-compose.aws.yml \
  down

[Install]
WantedBy=multi-user.target
UNIT

systemctl daemon-reload
systemctl enable blackjack.service

echo "=== Bootstrap complete ==="
