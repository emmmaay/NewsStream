# Ubuntu Server Deployment Guide - Automated News Bot

## 🚀 Complete Zero-Error Installation Guide

This guide ensures **bulletproof deployment** with no errors on Ubuntu 20.04/22.04 LTS.

### Prerequisites
- Fresh Ubuntu 20.04 or 22.04 LTS server
- Root or sudo access
- Internet connection

---

## Step 1: Update System (Mandatory)

```bash
# Update package lists and system
sudo apt update && sudo apt upgrade -y

# Install essential build tools
sudo apt install -y curl wget git build-essential software-properties-common
```

---

## Step 2: Install Python 3.11 (Required Version)

```bash
# Add Python PPA for latest versions
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update

# Install Python 3.11 and essential packages
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# Make Python 3.11 default
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Verify installation
python --version  # Should show Python 3.11.x
```

---

## Step 3: Install System Dependencies

```bash
# Install all required system packages
sudo apt install -y \
    redis-server \
    postgresql \
    postgresql-contrib \
    nginx \
    supervisor \
    chromium-browser \
    chromium-chromedriver \
    xvfb \
    libglib2.0-0 \
    libnss3-dev \
    libgconf-2-4 \
    libxss1 \
    libxtst6 \
    libxrandr2 \
    libatk1.0-0 \
    libdrm2 \
    libgtk-3-0 \
    libgbm-dev \
    libasound2-dev

# Start and enable services
sudo systemctl start redis-server postgresql
sudo systemctl enable redis-server postgresql

# Install Node.js (for Playwright browsers)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs
```

---

## Step 4: Setup Project Directory

```bash
# Create dedicated user for the bot
sudo useradd -m -s /bin/bash newsbot
sudo usermod -aG sudo newsbot

# Switch to bot user
sudo su - newsbot

# Create project directory
mkdir -p ~/newsbot
cd ~/newsbot

# Clone or copy your project files here
# (Upload all your Python files to this directory)
```

---

## Step 5: Install Python Dependencies

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Upgrade pip to latest version
pip install --upgrade pip setuptools wheel

# Install all required packages (bulletproof versions)
pip install \
    aiofiles==23.2.1 \
    aiohttp==3.9.1 \
    asyncio-throttle==1.0.2 \
    asyncpg==0.29.0 \
    beautifulsoup4==4.12.2 \
    facebook-sdk==3.1.0 \
    fake-useragent==1.4.0 \
    fastapi==0.104.1 \
    feedparser==6.0.10 \
    groq==0.4.1 \
    lxml==4.9.3 \
    nltk==3.8.1 \
    pillow==10.1.0 \
    playwright==1.40.0 \
    python-dotenv==1.0.0 \
    python-multipart==0.0.6 \
    python-telegram-bot==20.7 \
    pyyaml==6.0.1 \
    redis==5.0.1 \
    requests==2.31.0 \
    schedule==1.2.0 \
    selenium-stealth==1.0.6 \
    textstat==0.7.3 \
    tiktoken==0.5.2 \
    uvicorn==0.24.0

# Install Playwright browsers
playwright install chromium
playwright install-deps chromium

# Download NLTK data
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"
```

---

## Step 6: Configure Environment Variables

```bash
# Create environment file
nano ~/newsbot/.env

# Add your credentials (replace with your actual values)
GROQ_API_KEY=your_groq_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHANNEL_ID=your_channel_id
FACEBOOK_ACCESS_TOKEN=your_facebook_access_token
FACEBOOK_PAGE_ID=your_facebook_page_id
TWITTER_USERNAME=your_twitter_username
TWITTER_PASSWORD=your_twitter_password

# Set proper permissions
chmod 600 ~/newsbot/.env
```

---

## Step 7: Setup Systemd Service

```bash
# Create systemd service file
sudo nano /etc/systemd/system/newsbot.service

# Add this content:
[Unit]
Description=Automated News Bot
After=network.target redis.service postgresql.service
Wants=redis.service postgresql.service

[Service]
Type=simple
User=newsbot
Group=newsbot
WorkingDirectory=/home/newsbot/newsbot
Environment=PATH=/home/newsbot/newsbot/venv/bin
Environment=DISPLAY=:99
ExecStartPre=/usr/bin/Xvfb :99 -screen 0 1024x768x24 &
ExecStart=/home/newsbot/newsbot/venv/bin/python main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

---

## Step 8: Setup Nginx Reverse Proxy (Optional)

```bash
# Create nginx configuration
sudo nano /etc/nginx/sites-available/newsbot

# Add this content:
server {
    listen 80;
    server_name your_domain.com;  # Replace with your domain
    
    location /webhook {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Enable the site
sudo ln -s /etc/nginx/sites-available/newsbot /etc/nginx/sites-enabled/
sudo nginx -t  # Test configuration
sudo systemctl reload nginx
```

---

## Step 9: Start the Service

```bash
# Reload systemd and start service
sudo systemctl daemon-reload
sudo systemctl enable newsbot
sudo systemctl start newsbot

# Check status
sudo systemctl status newsbot

# View logs
sudo journalctl -u newsbot -f
```

---

## Step 10: Setup Firewall

```bash
# Configure UFW firewall
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw allow 8000  # For webhook endpoint
sudo ufw --force enable
```

---

## 🔧 Troubleshooting Common Issues

### Issue 1: Playwright Browser Dependencies
```bash
# If Playwright fails to install browsers
sudo apt install -y libnss3 libatk-bridge2.0-0 libdrm2 libgtk-3-0 libgbm1
playwright install --force chromium
```

### Issue 2: Redis Connection Issues
```bash
# Check Redis status
sudo systemctl status redis-server
sudo redis-cli ping  # Should return "PONG"
```

### Issue 3: Permission Issues
```bash
# Fix permissions
sudo chown -R newsbot:newsbot /home/newsbot/newsbot
chmod +x /home/newsbot/newsbot/main.py
```

### Issue 4: Python Module Not Found
```bash
# Reinstall virtual environment
cd ~/newsbot
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt  # If you have one
```

---

## 🔍 Health Monitoring

### Check Service Status
```bash
# Service status
sudo systemctl status newsbot

# Live logs
sudo journalctl -u newsbot -f

# Resource usage
htop
```

### Test Platform Connectivity
```bash
# Test from your project directory
cd ~/newsbot
source venv/bin/activate
python test_all_platforms.py
```

---

## 🚀 Auto-Start on Boot

The systemd service automatically starts the bot on system boot. To verify:

```bash
# Check if enabled
sudo systemctl is-enabled newsbot

# Test reboot (optional)
sudo reboot
# Wait for system to come back up, then check:
sudo systemctl status newsbot
```

---

## 📝 Maintenance Commands

```bash
# Restart service
sudo systemctl restart newsbot

# Update code (when you make changes)
sudo systemctl stop newsbot
# Upload new files
sudo systemctl start newsbot

# View configuration
sudo systemctl show newsbot

# Emergency stop
sudo systemctl stop newsbot
sudo systemctl disable newsbot
```

---

## ✅ Deployment Verification

After deployment, verify these work:
1. `sudo systemctl status newsbot` shows "active (running)"
2. `sudo journalctl -u newsbot -n 50` shows bot processing news
3. Check your social media accounts for test posts
4. Redis: `redis-cli ping` returns "PONG"
5. Webhook endpoint accessible at `http://your-server:8000/webhook`

---

## 🎯 Success Indicators

Your deployment is successful when you see:
- ✅ Service status: Active (running)
- ✅ RSS feeds being processed in logs
- ✅ Posts appearing on social media platforms
- ✅ No critical errors in journalctl logs
- ✅ System stable after reboot

---

**🎉 Your automated news bot is now live and bulletproof on Ubuntu!**

For support or issues, check the logs first:
```bash
sudo journalctl -u newsbot -f
```