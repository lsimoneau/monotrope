#!/usr/bin/env bash
set -euo pipefail

# setup.sh — Provision a fresh Ubuntu 24.04 droplet for monotrope.au
# Run as root via: ssh root@<DROPLET_IP> 'bash -s' < infra/setup.sh

DEPLOY_USER="deploy"
SITE_DIR="/var/www/monotrope"
DEPLOY_PUBKEY="${DEPLOY_PUBKEY:-}" # Set this env var before running, or edit below

echo "==> Updating packages"
apt-get update -y
apt-get upgrade -y

# ── Caddy ─────────────────────────────────────────────────────────────────
echo "==> Installing Caddy"
apt-get install -y debian-keyring debian-archive-keyring apt-transport-https curl

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg

curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | tee /etc/apt/sources.list.d/caddy-stable.list

apt-get update -y
apt-get install -y caddy

# ── Site directory ─────────────────────────────────────────────────────────
echo "==> Creating www user and site directory"
id -u www &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin www
mkdir -p "$SITE_DIR"
chown www:www "$SITE_DIR"
chmod 755 "$SITE_DIR"

# ── Caddyfile ──────────────────────────────────────────────────────────────
echo "==> Installing Caddyfile"
cp "$(dirname "$0")/Caddyfile" /etc/caddy/Caddyfile
chown root:caddy /etc/caddy/Caddyfile
chmod 640 /etc/caddy/Caddyfile

systemctl enable caddy
systemctl restart caddy

# ── UFW ────────────────────────────────────────────────────────────────────
echo "==> Configuring UFW"
apt-get install -y ufw
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow http
ufw allow https
ufw --force enable

# ── Docker ────────────────────────────────────────────────────────────────
echo "==> Installing Docker"
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | tee /etc/apt/sources.list.d/docker.list

apt-get update -y
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable docker

# ── Deploy user ───────────────────────────────────────────────────────────
echo "==> Creating deploy user"
id -u "$DEPLOY_USER" &>/dev/null || useradd --create-home --shell /bin/bash "$DEPLOY_USER"

# Give deploy user write access to the site directory
chown -R "$DEPLOY_USER":www "$SITE_DIR"
chmod 775 "$SITE_DIR"

# Set up SSH key auth
DEPLOY_HOME="/home/$DEPLOY_USER"
mkdir -p "$DEPLOY_HOME/.ssh"
chmod 700 "$DEPLOY_HOME/.ssh"
touch "$DEPLOY_HOME/.ssh/authorized_keys"
chmod 600 "$DEPLOY_HOME/.ssh/authorized_keys"
chown -R "$DEPLOY_USER":"$DEPLOY_USER" "$DEPLOY_HOME/.ssh"

if [[ -n "$DEPLOY_PUBKEY" ]]; then
  echo "$DEPLOY_PUBKEY" >> "$DEPLOY_HOME/.ssh/authorized_keys"
  echo "==> Deploy public key installed"
else
  echo "WARNING: DEPLOY_PUBKEY not set. Add your public key to $DEPLOY_HOME/.ssh/authorized_keys manually."
fi

echo ""
echo "==> Done. Checklist:"
echo "    - Point DNS A records for monotrope.au and www.monotrope.au to this server's IP"
echo "    - If DEPLOY_PUBKEY was not set, add your key to $DEPLOY_HOME/.ssh/authorized_keys"
echo "    - Run 'make deploy' from your local machine to push the site"
