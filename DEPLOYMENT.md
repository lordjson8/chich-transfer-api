# Chic Transfer API — Production Deployment Guide

## Part 1: VPS Initial Setup

SSH into your LWS VPS and run:

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Install Docker Compose plugin
sudo apt install docker-compose-plugin -y

# Install Certbot
sudo apt install certbot -y

# Set up firewall
sudo ufw allow 22
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable

# Create project directory
sudo mkdir -p /opt/chic-transfer-api
sudo chown $USER:$USER /opt/chic-transfer-api
```

Log out and back in for Docker group to take effect.

## Part 2: SSL Certificate

### Point DNS
Create an A record for your subdomain (e.g., `api.yourdomain.com`) pointing to the VPS IP address.

### Generate Certificate
```bash
# Stop anything on port 80 first
sudo certbot certonly --standalone -d api.yourdomain.com

# Certificates will be in /etc/letsencrypt/live/api.yourdomain.com/
```

### Copy certs to Docker volume
```bash
# Create the SSL volume directory and copy certs
docker volume create chic-transfer-api_ssl_certs
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem /var/lib/docker/volumes/chic-transfer-api_ssl_certs/_data/fullchain.pem
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem /var/lib/docker/volumes/chic-transfer-api_ssl_certs/_data/privkey.pem
```

### Auto-renewal cron
```bash
# Add to crontab (runs twice daily)
(crontab -l 2>/dev/null; echo "0 0,12 * * * certbot renew --quiet --post-hook 'cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem /var/lib/docker/volumes/chic-transfer-api_ssl_certs/_data/fullchain.pem && cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem /var/lib/docker/volumes/chic-transfer-api_ssl_certs/_data/privkey.pem && docker restart chic_transfer_nginx'") | crontab -
```

## Part 3: First Deployment

```bash
cd /opt/chic-transfer-api

# Clone the repo
git clone https://github.com/YOUR_USERNAME/chic-transfer-api.git .

# Create .env.prod from template and fill in real values
cp .env.prod.example .env.prod   # or copy from your local machine
nano .env.prod                   # edit with real credentials

# Build and start all services
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Check all services are running
docker compose -f docker-compose.prod.yml ps

# Create Django superuser
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser

# Verify
curl https://api.yourdomain.com/api/
```

## Part 4: CI/CD Setup

### Generate SSH key for deployment
```bash
# On your local machine
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/deploy_key

# Copy public key to VPS
ssh-copy-id -i ~/.ssh/deploy_key.pub user@your-vps-ip
```

### Add GitHub Secrets
In your GitHub repo, go to **Settings > Secrets and variables > Actions** and add:

| Secret      | Value                              |
|-------------|-------------------------------------|
| `SSH_HOST`  | Your VPS IP address                |
| `SSH_USER`  | Your VPS username                  |
| `SSH_KEY`   | Contents of `~/.ssh/deploy_key` (private key) |

Now every push to `master` will automatically deploy.

## Part 5: Maintenance

### View logs
```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f nginx
docker compose -f docker-compose.prod.yml logs -f db
```

### Restart services
```bash
docker compose -f docker-compose.prod.yml restart web
docker compose -f docker-compose.prod.yml restart nginx
```

### Database backup
```bash
# Backup
docker compose -f docker-compose.prod.yml exec db mysqldump -u root -p$MYSQL_ROOT_PASSWORD chic_transfer_prod > backup_$(date +%Y%m%d).sql

# Restore
docker compose -f docker-compose.prod.yml exec -T db mysql -u root -p$MYSQL_ROOT_PASSWORD chic_transfer_prod < backup.sql
```

### Run Django management commands
```bash
docker compose -f docker-compose.prod.yml exec web python manage.py shell
docker compose -f docker-compose.prod.yml exec web python manage.py migrate
```
