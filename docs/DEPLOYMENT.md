# 🚀 Deployment Guide

> **Complete guide for deploying LineupTracker in different environments**

This guide covers deployment options from simple local setups to production cloud environments.

---

## 📋 Deployment Options Overview

| Option | Difficulty | Cost | Best For |
|--------|------------|------|----------|
| **Local Development** | Easy | Free | Testing, personal use |
| **GitHub Pages (Dashboard)** | Easy | Free | Sharing dashboard publicly |
| **VPS/Cloud VM** | Medium | $5-20/month | Always-on monitoring |
| **Cloud Container** | Medium | $10-30/month | Scalable, managed |
| **Raspberry Pi** | Medium | $35+ one-time | Home automation, low power |
| **Docker** | Medium | Free+ | Portable, consistent environments |

---

## 🏠 Local Development Setup

Perfect for testing and personal use on your own computer.

### Prerequisites
- Python 3.8+ installed
- Node.js 18+ (for dashboard)
- Git

### Quick Setup
```bash
# Clone repository
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker

# Set up Python environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure
python setup.py

# Run
python main.py
```

### Pros & Cons
✅ **Pros**: Free, easy setup, full control  
❌ **Cons**: Computer must stay on, no remote access

---

## 🌐 GitHub Pages (Dashboard Only)

Deploy the dashboard for free public access while running monitoring locally.

### Setup Steps

1. **Enable GitHub Pages**
   ```bash
   # Push your repository to GitHub
   git add .
   git commit -m "Initial commit"
   git push origin main
   
   # Go to: Settings → Pages → Source: "GitHub Actions"
   ```

2. **Configure Dashboard**
   ```bash
   # Update repository name in vite.config.js if needed
   cd dashboard
   # Edit vite.config.js:
   # base: '/YourRepositoryName/'
   ```

3. **Deploy**
   ```bash
   # Export data and deploy
   python export_squad_only.py
   cd dashboard
   npm install
   npm run build
   npm run deploy
   ```

### Automatic Deployment
The included GitHub Actions workflow automatically deploys when you push to main:
```yaml
# .github/workflows/deploy-dashboard.yml already included
```

### Custom Domain (Optional)
1. Add `CNAME` file to dashboard/public: `yourdomain.com`
2. Configure DNS CNAME record: `www → your-username.github.io`
3. GitHub Settings → Pages → Custom domain

### Pros & Cons
✅ **Pros**: Free, automatic deployment, global CDN  
❌ **Cons**: Dashboard only, static data, manual refresh needed

---

## 💾 VPS/Cloud VM Deployment

Run LineupTracker 24/7 on a virtual private server.

### Recommended Providers
- **DigitalOcean**: $6/month droplet
- **Linode**: $5/month nanode
- **Vultr**: $6/month regular instance
- **AWS EC2**: t3.micro (~$10/month)
- **Google Cloud**: e2-micro (~$7/month)

### Ubuntu Server Setup

1. **Create and Access Server**
   ```bash
   # SSH into your server
   ssh root@your-server-ip
   
   # Update system
   apt update && apt upgrade -y
   ```

2. **Install Dependencies**
   ```bash
   # Install Python and Node.js
   apt install python3 python3-pip python3-venv nodejs npm git -y
   
   # Install specific Node.js version (if needed)
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   apt-get install -y nodejs
   ```

3. **Deploy Application**
   ```bash
   # Clone repository
   git clone https://github.com/your-username/LineupTracker.git
   cd LineupTracker
   
   # Set up Python environment
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   
   # Configure
   cp env.example .env
   nano .env  # Edit configuration
   cp examples/sample_roster.csv my_roster.csv
   nano my_roster.csv  # Add your players
   ```

4. **Set Up as Service**
   ```bash
   # Create systemd service
   sudo nano /etc/systemd/system/lineup-tracker.service
   ```
   
   ```ini
   [Unit]
   Description=LineupTracker Fantasy Football Monitor
   After=network.target
   
   [Service]
   Type=simple
   User=lineuptracker
   WorkingDirectory=/home/lineuptracker/LineupTracker
   Environment=PATH=/home/lineuptracker/LineupTracker/venv/bin
   ExecStart=/home/lineuptracker/LineupTracker/venv/bin/python main.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```
   
   ```bash
   # Enable and start service
   sudo systemctl enable lineup-tracker
   sudo systemctl start lineup-tracker
   sudo systemctl status lineup-tracker
   ```

5. **Deploy Dashboard (Optional)**
   ```bash
   # Set up Nginx for dashboard
   sudo apt install nginx -y
   
   # Build dashboard
   cd dashboard
   npm install
   npm run build
   
   # Copy to web directory
   sudo cp -r dist/* /var/www/html/
   
   # Configure Nginx
   sudo nano /etc/nginx/sites-available/default
   ```

### Monitoring and Maintenance
```bash
# View logs
sudo journalctl -u lineup-tracker -f

# Update application
cd LineupTracker
git pull origin main
pip install -r requirements.txt --upgrade
sudo systemctl restart lineup-tracker

# Check system resources
htop
df -h
```

### Pros & Cons
✅ **Pros**: 24/7 operation, remote access, full control  
❌ **Cons**: Monthly cost, requires server management

---

## 🐳 Docker Deployment

Containerized deployment for consistency and portability.

### Dockerfile
```dockerfile
# Create Dockerfile in project root
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY main.py .
COPY export_squad_only.py .

# Create non-root user
RUN useradd -m -u 1000 lineuptracker && \
    chown -R lineuptracker:lineuptracker /app
USER lineuptracker

# Health check
HEALTHCHECK --interval=5m --timeout=10s --start-period=30s \
    CMD python -c "import sys; sys.exit(0)"

# Run application
CMD ["python", "main.py"]
```

### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  lineup-tracker:
    build: .
    container_name: lineup-tracker
    restart: unless-stopped
    environment:
      - ENVIRONMENT=production
      - LOG_LEVEL=INFO
    env_file:
      - .env
    volumes:
      - ./my_roster.csv:/app/my_roster.csv:ro
      - ./logs:/app/logs
      - ./dashboard/public/data:/app/dashboard/public/data
    networks:
      - lineup-tracker-net

  # Optional: Nginx for dashboard
  nginx:
    image: nginx:alpine
    container_name: lineup-tracker-dashboard
    restart: unless-stopped
    ports:
      - "80:80"
    volumes:
      - ./dashboard/dist:/usr/share/nginx/html:ro
    depends_on:
      - lineup-tracker
    networks:
      - lineup-tracker-net

networks:
  lineup-tracker-net:
    driver: bridge
```

### Deployment Commands
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f lineup-tracker

# Update
git pull origin main
docker-compose down
docker-compose build --no-cache
docker-compose up -d

# Cleanup
docker-compose down -v
docker system prune -af
```

### Pros & Cons
✅ **Pros**: Consistent environment, easy deployment, portable  
❌ **Cons**: Docker overhead, more complex setup

---

## 🍓 Raspberry Pi Deployment

Perfect for home automation and low-power 24/7 monitoring.

### Hardware Requirements
- **Raspberry Pi 4** (2GB+ RAM recommended)
- **MicroSD Card** (32GB+ Class 10)
- **Power Supply** (Official USB-C recommended)
- **Network Connection** (Ethernet or WiFi)

### Setup Process

1. **Install Raspberry Pi OS**
   ```bash
   # Flash Raspberry Pi OS Lite to SD card
   # Enable SSH in boot partition: touch ssh
   # Configure WiFi in boot partition if needed
   ```

2. **Initial Configuration**
   ```bash
   # SSH into Pi
   ssh pi@raspberrypi.local  # Default password: raspberry
   
   # Change password and update
   passwd
   sudo apt update && sudo apt upgrade -y
   
   # Install dependencies
   sudo apt install python3 python3-pip python3-venv nodejs npm git -y
   ```

3. **Deploy Application**
   ```bash
   # Clone and setup (same as VPS steps above)
   git clone https://github.com/your-username/LineupTracker.git
   cd LineupTracker
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Optimize for Pi**
   ```bash
   # Reduce memory usage in .env
   echo "API_CONNECTION_POOL_SIZE=2" >> .env
   echo "MAX_CONCURRENT_REQUESTS=2" >> .env
   echo "LOG_LEVEL=WARNING" >> .env
   
   # Set up swap if needed
   sudo dphys-swapfile swapoff
   sudo nano /etc/dphys-swapfile  # CONF_SWAPSIZE=1024
   sudo dphys-swapfile setup
   sudo dphys-swapfile swapon
   ```

### Performance Optimization
```bash
# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable wifi-country

# GPU memory split (headless)
echo "gpu_mem=16" | sudo tee -a /boot/config.txt

# Overclock (optional, monitor temperature)
echo "arm_freq=1750" | sudo tee -a /boot/config.txt
echo "over_voltage=2" | sudo tee -a /boot/config.txt
```

### Monitoring
```bash
# Temperature monitoring
vcgencmd measure_temp

# Resource usage
htop
free -h

# Add temperature logging
echo "*/5 * * * * /usr/bin/vcgencmd measure_temp >> /home/pi/temp.log" | crontab -
```

### Pros & Cons
✅ **Pros**: Low power, one-time cost, home automation ready  
❌ **Cons**: Limited performance, SD card reliability, setup complexity

---

## ☁️ Cloud Container Services

Managed container deployment without server management.

### Google Cloud Run
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT-ID/lineup-tracker
gcloud run deploy --image gcr.io/PROJECT-ID/lineup-tracker --platform managed
```

### AWS Fargate
```bash
# Push to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker build -t lineup-tracker .
docker tag lineup-tracker:latest ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/lineup-tracker:latest
docker push ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/lineup-tracker:latest

# Deploy with ECS/Fargate (use AWS Console or CLI)
```

### Azure Container Instances
```bash
# Deploy to ACI
az container create \
  --resource-group myResourceGroup \
  --name lineup-tracker \
  --image yourdockerhub/lineup-tracker:latest \
  --environment-variables ENVIRONMENT=production
```

### Pros & Cons
✅ **Pros**: Managed infrastructure, auto-scaling, high availability  
❌ **Cons**: Higher cost, vendor lock-in, complexity

---

## 🔧 Environment-Specific Configuration

### Development
```bash
ENVIRONMENT=development
LOG_LEVEL=DEBUG
CHECK_INTERVAL_MINUTES=5  # Faster for testing
SEND_STARTUP_NOTIFICATIONS=true
```

### Staging
```bash
ENVIRONMENT=staging
LOG_LEVEL=INFO
CHECK_INTERVAL_MINUTES=10
SEND_STARTUP_NOTIFICATIONS=false
```

### Production
```bash
ENVIRONMENT=production
LOG_LEVEL=WARNING
CHECK_INTERVAL_MINUTES=15
SEND_STARTUP_NOTIFICATIONS=false
MAX_MONITORING_CYCLES_PER_DAY=100
```

---

## 📊 Monitoring and Observability

### Log Management
```bash
# Centralized logging with rsyslog
echo "*.* @@logs.example.com:514" | sudo tee -a /etc/rsyslog.conf

# Log rotation
sudo nano /etc/logrotate.d/lineup-tracker
```

### Health Checks
```bash
# Simple health check script
#!/bin/bash
if pgrep -f "python main.py" > /dev/null; then
    echo "LineupTracker is running"
    exit 0
else
    echo "LineupTracker is not running"
    exit 1
fi
```

### Monitoring Tools
- **Uptime monitoring**: UptimeRobot, Pingdom
- **Log analysis**: ELK Stack, Grafana Loki
- **Metrics**: Prometheus + Grafana
- **Error tracking**: Sentry

---

## 🔒 Security Considerations

### Network Security
```bash
# Firewall rules (UFW example)
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 80/tcp  # If running dashboard
sudo ufw allow 443/tcp  # If using HTTPS
```

### SSL/TLS
```bash
# Let's Encrypt with Certbot
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d yourdomain.com
```

### Secrets Management
```bash
# Use environment-specific secret management
# Development: .env files
# Production: HashiCorp Vault, AWS Secrets Manager, etc.
```

---

## 🚨 Troubleshooting

### Common Issues

**Memory Issues**
```bash
# Check memory usage
free -h
# Add swap space
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Network Connectivity**
```bash
# Test API connectivity
curl -I https://api.sofascore.com
# Check DNS resolution
nslookup api.sofascore.com
```

**Permission Issues**
```bash
# Fix file permissions
chmod 600 .env
chmod 644 my_roster.csv
chown -R $USER:$USER .
```

**Service Issues**
```bash
# Check service status
sudo systemctl status lineup-tracker
# View recent logs
sudo journalctl -u lineup-tracker --since "10 minutes ago"
```

---

## 📈 Scaling Considerations

### Performance Tuning
- Increase `MAX_CONCURRENT_REQUESTS` for faster API calls
- Tune `CHECK_INTERVAL_MINUTES` based on needs
- Use caching to reduce API calls
- Optimize database queries (if using database)

### High Availability
- Deploy to multiple regions
- Use load balancers
- Implement health checks
- Set up automatic failover

### Cost Optimization
- Use spot instances for non-critical workloads
- Implement auto-scaling based on usage
- Use reserved instances for predictable workloads
- Monitor and optimize resource usage

---

## 🎯 Deployment Checklist

Before deploying to production:

- [ ] **Security**: All secrets in environment variables
- [ ] **Testing**: Full test suite passes
- [ ] **Monitoring**: Health checks and logging configured
- [ ] **Backup**: Configuration and data backup strategy
- [ ] **Documentation**: Deployment process documented
- [ ] **Recovery**: Disaster recovery plan in place
- [ ] **Performance**: Load tested for expected usage
- [ ] **Compliance**: Meets security and privacy requirements

---

**Ready to deploy? Choose the option that best fits your needs and follow the detailed steps above! 🚀**