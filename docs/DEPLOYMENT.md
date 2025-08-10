# 🚀 Deployment Guide

This guide covers different ways to deploy and run LineupTracker in production environments.

## 📋 Table of Contents

- [Local Deployment](#local-deployment)
- [Server Deployment](#server-deployment)
- [Docker Deployment](#docker-deployment)
- [Cloud Deployment](#cloud-deployment)
- [Monitoring & Maintenance](#monitoring--maintenance)

---

## 🏠 Local Deployment

### Basic Setup

For personal use on your local machine:

```bash
# 1. Clone and setup
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
python setup.py

# 4. Test
python test_system.py

# 5. Run
python main.py
```

### Running as Background Service

#### Linux/macOS with systemd

Create service file `/etc/systemd/system/lineuptracker.service`:

```ini
[Unit]
Description=LineupTracker Fantasy Football Monitor
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/LineupTracker
Environment=PATH=/path/to/LineupTracker/venv/bin
ExecStart=/path/to/LineupTracker/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable lineuptracker
sudo systemctl start lineuptracker
sudo systemctl status lineuptracker
```

#### Windows with Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Set trigger to "At startup"
4. Action: Start a program
5. Program: `C:\path\to\LineupTracker\venv\Scripts\python.exe`
6. Arguments: `main.py`
7. Start in: `C:\path\to\LineupTracker`

#### macOS with launchd

Create `~/Library/LaunchAgents/com.lineuptracker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.lineuptracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/LineupTracker/venv/bin/python</string>
        <string>/path/to/LineupTracker/main.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/LineupTracker</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Load and start:
```bash
launchctl load ~/Library/LaunchAgents/com.lineuptracker.plist
launchctl start com.lineuptracker
```

---

## 🖥️ Server Deployment

### VPS/Dedicated Server

#### Requirements

- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **RAM**: 512MB minimum, 1GB recommended
- **Storage**: 1GB minimum
- **Python**: 3.8+
- **Network**: Stable internet connection

#### Setup Steps

```bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install Python and dependencies
sudo apt install python3 python3-pip python3-venv git -y

# 3. Create user (optional but recommended)
sudo useradd -m -s /bin/bash lineuptracker
sudo su - lineuptracker

# 4. Clone repository
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker

# 5. Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# 6. Install dependencies
pip install -r requirements.txt

# 7. Configure
python setup.py

# 8. Test
python test_system.py

# 9. Setup systemd service (as root)
exit  # Exit lineuptracker user
sudo cp deployment/lineuptracker.service /etc/systemd/system/
sudo systemctl enable lineuptracker
sudo systemctl start lineuptracker
```

#### Nginx Reverse Proxy (Optional)

If you plan to add a web interface later:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 🐳 Docker Deployment

### Dockerfile

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 lineuptracker && \
    chown -R lineuptracker:lineuptracker /app
USER lineuptracker

# Health check
HEALTHCHECK --interval=5m --timeout=30s --start-period=30s --retries=3 \
    CMD python test_system.py --component api || exit 1

# Run the application
CMD ["python", "main.py"]
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  lineuptracker:
    build: .
    container_name: lineuptracker
    restart: unless-stopped
    environment:
      - LOG_LEVEL=INFO
    env_file:
      - .env
    volumes:
      - ./my_roster.csv:/app/my_roster.csv:ro
      - ./logs:/app/logs
    networks:
      - lineuptracker-network
    healthcheck:
      test: ["CMD", "python", "test_system.py", "--component", "api"]
      interval: 5m
      timeout: 30s
      retries: 3
      start_period: 30s

networks:
  lineuptracker-network:
    driver: bridge

volumes:
  logs:
```

### Build and Run

```bash
# Build image
docker build -t lineuptracker .

# Run with docker-compose
docker-compose up -d

# Check logs
docker-compose logs -f

# Stop
docker-compose down
```

---

## ☁️ Cloud Deployment

### AWS EC2

#### Launch Instance

1. **AMI**: Ubuntu Server 22.04 LTS
2. **Instance Type**: t3.micro (free tier eligible)
3. **Security Group**: Allow SSH (22)
4. **Storage**: 8GB gp3

#### Setup Script

```bash
#!/bin/bash
# AWS EC2 user data script

# Update system
apt update && apt upgrade -y

# Install dependencies
apt install python3 python3-pip python3-venv git -y

# Clone repository
cd /home/ubuntu
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker

# Setup
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set ownership
chown -R ubuntu:ubuntu /home/ubuntu/LineupTracker

# Install systemd service
cp deployment/lineuptracker.service /etc/systemd/system/
systemctl enable lineuptracker
```

### Google Cloud Platform

#### Compute Engine

```bash
# Create instance
gcloud compute instances create lineuptracker \
    --zone=us-central1-a \
    --machine-type=e2-micro \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --metadata-from-file startup-script=startup.sh

# SSH to instance
gcloud compute ssh lineuptracker --zone=us-central1-a
```

#### Cloud Run (Serverless)

For scheduled execution:

```yaml
# cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/lineuptracker', '.']
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/lineuptracker']
  - name: 'gcr.io/cloud-builders/gcloud'
    args: ['run', 'deploy', 'lineuptracker', 
           '--image', 'gcr.io/$PROJECT_ID/lineuptracker',
           '--region', 'us-central1',
           '--no-allow-unauthenticated']
```

### Digital Ocean

#### Droplet

```bash
# Create droplet with doctl
doctl compute droplet create lineuptracker \
    --size s-1vcpu-1gb \
    --image ubuntu-22-04-x64 \
    --region nyc1 \
    --ssh-keys YOUR_SSH_KEY_ID
```

### Azure

#### Virtual Machine

```bash
# Create VM with Azure CLI
az vm create \
    --resource-group LineupTracker \
    --name lineuptracker-vm \
    --image UbuntuLTS \
    --size Standard_B1s \
    --admin-username azureuser \
    --ssh-key-values ~/.ssh/id_rsa.pub
```

---

## 📊 Monitoring & Maintenance

### Health Monitoring

#### Basic Health Check Script

Create `health_check.py`:

```python
#!/usr/bin/env python3
import subprocess
import sys
import time
from datetime import datetime

def check_process():
    """Check if LineupTracker process is running."""
    try:
        result = subprocess.run(['pgrep', '-f', 'main.py'], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def check_logs():
    """Check for recent errors in logs."""
    try:
        result = subprocess.run(['tail', '-100', 'lineup_monitor.log'], 
                              capture_output=True, text=True)
        return 'ERROR' not in result.stdout
    except:
        return True

def main():
    print(f"Health check - {datetime.now()}")
    
    if not check_process():
        print("❌ Process not running")
        sys.exit(1)
    
    if not check_logs():
        print("⚠️ Errors detected in logs")
        sys.exit(1)
    
    print("✅ System healthy")

if __name__ == "__main__":
    main()
```

Add to crontab:
```bash
# Check every 5 minutes
*/5 * * * * /path/to/LineupTracker/venv/bin/python /path/to/health_check.py
```

### Log Rotation

#### Using logrotate

Create `/etc/logrotate.d/lineuptracker`:

```
/path/to/LineupTracker/lineup_monitor.log {
    daily
    rotate 7
    compress
    missingok
    notifempty
    create 644 lineuptracker lineuptracker
    postrotate
        systemctl reload lineuptracker
    endscript
}
```

### Backup Strategy

#### Configuration Backup

```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/lineuptracker"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
cp .env $BACKUP_DIR/env_$DATE
cp my_roster.csv $BACKUP_DIR/roster_$DATE.csv

# Backup logs (last 7 days)
find . -name "*.log" -mtime -7 -exec cp {} $BACKUP_DIR/ \;

echo "Backup completed: $BACKUP_DIR"
```

### Update Process

#### Automated Updates

```bash
#!/bin/bash
# update.sh

echo "Updating LineupTracker..."

# Stop service
sudo systemctl stop lineuptracker

# Backup current version
cp -r /path/to/LineupTracker /backup/lineuptracker_$(date +%Y%m%d)

# Pull updates
cd /path/to/LineupTracker
git pull origin main

# Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# Test system
python test_system.py

# Restart service
sudo systemctl start lineuptracker

echo "Update completed"
```

### Performance Monitoring

#### Resource Usage

Monitor with:
```bash
# CPU and Memory usage
ps aux | grep python

# System resources
htop

# Disk usage
df -h

# Network connections
netstat -tuln
```

#### Application Metrics

Add to your monitoring dashboard:
- API response times
- Notification success rates
- Error frequency
- Memory usage
- CPU usage

---

## 🔧 Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check logs
sudo journalctl -u lineuptracker -f

# Check configuration
python test_system.py

# Check permissions
ls -la /path/to/LineupTracker
```

#### High Memory Usage

```bash
# Check for memory leaks
python -m memory_profiler main.py

# Monitor over time
watch -n 5 'ps aux | grep python'
```

#### Network Issues

```bash
# Test API connectivity
curl -I https://api.sofascore.com

# Check DNS resolution
nslookup api.sofascore.com

# Test Discord webhook
curl -X POST $DISCORD_WEBHOOK_URL -d '{"content":"test"}'
```

### Getting Help

- 📖 Check the main README.md
- 🐛 Create an issue on GitHub
- 💬 Join the Discord community
- 📧 Contact maintainers

---

## 📜 Security Considerations

### Environment Variables

- Never commit `.env` files
- Use secure methods to transfer credentials
- Rotate webhook URLs periodically
- Use app passwords for email

### Server Security

- Keep system updated
- Use SSH keys (not passwords)
- Configure firewall
- Enable fail2ban
- Regular security audits

### Network Security

- Use HTTPS where possible
- Validate webhook URLs
- Monitor unusual network activity
- Rate limit API calls

---

<div align="center">

**Need help with deployment? Create an issue or join our community!**

[GitHub Issues](https://github.com/your-username/LineupTracker/issues) · [Discord Community](https://discord.gg/your-invite)

</div>
