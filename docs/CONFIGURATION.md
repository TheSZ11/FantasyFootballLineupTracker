# ⚙️ Configuration Guide

Complete guide to configuring LineupTracker for your specific needs.

## 📋 Table of Contents

- [Environment Variables](#environment-variables)
- [Squad File Formats](#squad-file-formats)
- [Notification Setup](#notification-setup)
- [Advanced Configuration](#advanced-configuration)
- [Configuration Examples](#configuration-examples)

---

## 🌍 Environment Variables

LineupTracker uses environment variables for configuration. Create a `.env` file in the project root.

### Core Settings

```bash
# Environment (development, staging, production)
ENVIRONMENT=production

# Enable debug mode for development
DEBUG_MODE=false

# User timezone (affects log timestamps and match times)
USER_TIMEZONE=UTC
```

### API Configuration

```bash
# Sofascore API settings
API_BASE_URL=https://api.sofascore.com
API_TIMEOUT_SECONDS=30
API_MAX_RETRIES=3
API_RATE_LIMIT_PER_MINUTE=60
API_CONNECTION_POOL_SIZE=10
```

### Discord Notifications

```bash
# Enable Discord notifications
DISCORD_ENABLED=true

# Discord webhook URL (get from Discord server settings)
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/123456789/abcdef...

# Discord-specific settings
DISCORD_TIMEOUT_SECONDS=30
DISCORD_RETRY_ATTEMPTS=3
```

#### How to Get Discord Webhook

1. Go to your Discord server
2. **Server Settings** → **Integrations** → **Webhooks**
3. **Create Webhook** or **New Webhook**
4. Choose the channel for notifications
5. Copy the **Webhook URL**

### Email Notifications

```bash
# Enable email notifications
EMAIL_ENABLED=true

# SMTP settings (Gmail example)
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENT=recipient@example.com

# Email behavior
EMAIL_USE_TLS=true
EMAIL_TIMEOUT_SECONDS=30
```

#### Gmail Setup

1. Enable 2-Factor Authentication
2. **Google Account** → **Security** → **App passwords**
3. Generate 16-character app password
4. Use app password (not your regular password) in `EMAIL_PASSWORD`

#### Other Email Providers

**Outlook/Hotmail:**
```bash
EMAIL_SMTP_SERVER=smtp-mail.outlook.com
EMAIL_SMTP_PORT=587
```

**Yahoo:**
```bash
EMAIL_SMTP_SERVER=smtp.mail.yahoo.com
EMAIL_SMTP_PORT=587
```

**Custom SMTP:**
```bash
EMAIL_SMTP_SERVER=mail.yourdomain.com
EMAIL_SMTP_PORT=587  # or 465 for SSL
```

### Monitoring Settings

```bash
# Core monitoring behavior
CHECK_INTERVAL_MINUTES=15
PRE_MATCH_WINDOW_MINUTES=60
FINAL_SPRINT_MINUTES=5
FINAL_SPRINT_INTERVAL_MINUTES=1

# Squad file location
SQUAD_FILE_PATH=my_roster.csv
BACKUP_SQUAD_FILE_PATH=backup_roster.csv

# Analysis settings
MIN_ANALYSIS_INTERVAL_MINUTES=5
CACHE_LINEUP_DATA_MINUTES=10

# Safety limits
MAX_CONCURRENT_REQUESTS=5
MAX_MONITORING_CYCLES_PER_DAY=200
```

### Notification Behavior

```bash
# Control which notifications to send
SEND_STARTUP_NOTIFICATIONS=true
SEND_SHUTDOWN_NOTIFICATIONS=true
SEND_ERROR_NOTIFICATIONS=true
SEND_CONFIRMATION_ALERTS=true
```

### Logging Configuration

```bash
# Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
LOG_LEVEL=INFO

# Log format (structured for JSON, simple for human-readable)
LOG_FORMAT=structured

# Log file settings
LOG_FILE=logs/lineup_tracker.log
LOG_MAX_FILE_SIZE_MB=10
LOG_BACKUP_COUNT=5
LOG_ENABLE_CONSOLE=true
LOG_CORRELATION_TRACKING=true
```

### Security Settings

```bash
# Security configuration
SECURITY_MAX_REQUEST_TIMEOUT=60
SECURITY_ALLOWED_FILE_EXTENSIONS=.csv,.txt
SECURITY_MAX_FILE_SIZE_MB=10
SECURITY_ENABLE_FILE_VALIDATION=true
```

---

## 📊 Squad File Formats

LineupTracker supports multiple squad file formats to accommodate different workflows.

### Fantrax Export Format (Recommended)

The most comprehensive format with all fantasy stats:

1. **Export from Fantrax:**
   - Go to **My Team** → **Roster**
   - Click **Export** button
   - Save as CSV

2. **Configure player status:**
   - Set `Status` column: 
     - `Act` for expected starters
     - `Res` for bench/rotation players

3. **File structure:**
```csv
"","Goalkeeper"
"ID","Pos","Player","Team","Status",...
"*123*","G","Player Name","LIV","Act",...

"","Outfielder"  
"ID","Pos","Player","Team","Status",...
"*456*","D","Player Name","LIV","Act",...
```

### Simple Format

Easy to create and maintain manually:

```csv
player_name,team_name,position,currently_starting,notes
Mohamed Salah,Liverpool,Forward,true,Captain choice
Erling Haaland,Manchester City,Forward,true,Premium striker
Kevin De Bruyne,Manchester City,Midfielder,false,Rotation risk
Virgil van Dijk,Liverpool,Defender,true,Defensive coverage
Alisson,Liverpool,Goalkeeper,true,First choice keeper
```

**Column descriptions:**
- `player_name`: Full player name (must match official names)
- `team_name`: Full team name (Liverpool, Manchester City, etc.)
- `position`: Player position (Goalkeeper, Defender, Midfielder, Forward)
- `currently_starting`: `true` for expected starters, `false` for bench
- `notes`: Optional notes for your reference

### Team Name Mapping

LineupTracker automatically maps common team abbreviations:

```python
TEAM_MAPPINGS = {
    'LIV': 'Liverpool',
    'MCI': 'Manchester City', 
    'ARS': 'Arsenal',
    'CHE': 'Chelsea',
    'MUN': 'Manchester United',
    'TOT': 'Tottenham',
    'NEW': 'Newcastle',
    'AVL': 'Aston Villa',
    'WHU': 'West Ham',
    'BHA': 'Brighton',
    # ... more mappings
}
```

### Custom Format Support

You can also create custom parsers by modifying the squad repository:

```python
# src/lineup_tracker/repositories/csv_squad_repository.py
def _create_player_from_row(self, row_data, headers, section):
    """Create Player object from CSV row data"""
    # Custom parsing logic here
```

---

## 📢 Notification Setup

### Discord Configuration

#### Basic Setup

```bash
# In .env file
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_URL
```

#### Advanced Discord Settings

```bash
# Customize Discord behavior
DISCORD_TIMEOUT_SECONDS=30
DISCORD_RETRY_ATTEMPTS=3
DISCORD_MAX_MESSAGE_LENGTH=2000
DISCORD_EMBED_COLOR_URGENT=16711680    # Red
DISCORD_EMBED_COLOR_IMPORTANT=16753920 # Orange
DISCORD_EMBED_COLOR_INFO=3447003       # Blue
```

#### Multiple Discord Channels

For different types of notifications:

```bash
# Primary channel for urgent alerts
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/urgent/...

# Secondary channel for info updates
DISCORD_INFO_WEBHOOK_URL=https://discord.com/api/webhooks/info/...
```

### Email Configuration

#### Gmail with App Password

```bash
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=abcd-efgh-ijkl-mnop  # 16-character app password
EMAIL_RECIPIENT=your-email@gmail.com
EMAIL_USE_TLS=true
```

#### Multiple Recipients

```bash
# Comma-separated list
EMAIL_RECIPIENT=manager1@email.com,manager2@email.com,manager3@email.com
```

#### Email Templates

Customize email templates by modifying:
```python
# src/lineup_tracker/providers/email_provider.py
def _create_email_content(self, alert):
    """Create email HTML content"""
    # Custom email template here
```

### Notification Types

#### Alert Urgency Levels

- **URGENT**: Expected starter benched, major lineup changes
- **IMPORTANT**: Unexpected starter, significant opportunities
- **WARNING**: Potential issues, configuration problems
- **INFO**: Confirmations, system status, routine updates

#### Notification Routing

```bash
# Send urgent alerts via email + Discord
URGENT_ALERT_CHANNELS=email,discord

# Send info updates via Discord only
INFO_ALERT_CHANNELS=discord

# Send errors via email
ERROR_ALERT_CHANNELS=email
```

---

## 🔧 Advanced Configuration

### Custom Monitoring Schedules

#### Match Day Schedule

```bash
# Start monitoring 90 minutes before kickoff
PRE_MATCH_WINDOW_MINUTES=90

# Check every 10 minutes normally
CHECK_INTERVAL_MINUTES=10

# Check every 2 minutes in final 10 minutes
FINAL_SPRINT_MINUTES=10
FINAL_SPRINT_INTERVAL_MINUTES=2
```

#### Off-Season Configuration

```bash
# Reduce monitoring during off-season
CHECK_INTERVAL_MINUTES=60
PRE_MATCH_WINDOW_MINUTES=120
MAX_MONITORING_CYCLES_PER_DAY=50
```

### API Rate Limiting

```bash
# Conservative API usage
API_RATE_LIMIT_PER_MINUTE=30
API_MAX_RETRIES=5
API_TIMEOUT_SECONDS=45

# Aggressive API usage (use carefully)
API_RATE_LIMIT_PER_MINUTE=100
API_MAX_RETRIES=2
API_TIMEOUT_SECONDS=15
```

### Performance Tuning

```bash
# High-performance settings
MAX_CONCURRENT_REQUESTS=10
API_CONNECTION_POOL_SIZE=20
CACHE_LINEUP_DATA_MINUTES=5

# Conservative settings (slower but safer)
MAX_CONCURRENT_REQUESTS=2
API_CONNECTION_POOL_SIZE=5
CACHE_LINEUP_DATA_MINUTES=15
```

### Development Configuration

```bash
# Development settings
ENVIRONMENT=development
DEBUG_MODE=true
LOG_LEVEL=DEBUG
LOG_FORMAT=simple
SEND_STARTUP_NOTIFICATIONS=false
CHECK_INTERVAL_MINUTES=5  # Faster testing
```

---

## 📝 Configuration Examples

### Example 1: Personal Use (Discord Only)

```bash
# .env for personal Discord notifications
ENVIRONMENT=production
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-url
EMAIL_ENABLED=false

SQUAD_FILE_PATH=my_roster.csv
CHECK_INTERVAL_MINUTES=15
SEND_CONFIRMATION_ALERTS=false
LOG_LEVEL=INFO
```

### Example 2: League Manager (Email + Discord)

```bash
# .env for league manager with multiple notifications
ENVIRONMENT=production

# Discord for quick updates
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/league-channel

# Email for important alerts
EMAIL_ENABLED=true
EMAIL_SMTP_SERVER=smtp.gmail.com
EMAIL_SMTP_PORT=587
EMAIL_USERNAME=league.manager@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENT=manager1@email.com,manager2@email.com

# Conservative monitoring
CHECK_INTERVAL_MINUTES=20
SEND_CONFIRMATION_ALERTS=true
SEND_STARTUP_NOTIFICATIONS=true
```

### Example 3: Development/Testing

```bash
# .env for development and testing
ENVIRONMENT=development
DEBUG_MODE=true
LOG_LEVEL=DEBUG
LOG_FORMAT=simple

# Faster testing cycles
CHECK_INTERVAL_MINUTES=2
PRE_MATCH_WINDOW_MINUTES=10
FINAL_SPRINT_MINUTES=2

# Test notifications
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/test-channel
SEND_STARTUP_NOTIFICATIONS=true
SEND_CONFIRMATION_ALERTS=true

# Test data
SQUAD_FILE_PATH=examples/sample_roster.csv
```

### Example 4: High-Volume Monitoring

```bash
# .env for monitoring multiple leagues/teams
ENVIRONMENT=production

# Optimized for performance
MAX_CONCURRENT_REQUESTS=8
API_RATE_LIMIT_PER_MINUTE=80
CACHE_LINEUP_DATA_MINUTES=3

# Aggressive monitoring
CHECK_INTERVAL_MINUTES=10
PRE_MATCH_WINDOW_MINUTES=120
FINAL_SPRINT_MINUTES=15
FINAL_SPRINT_INTERVAL_MINUTES=1

# Multiple notification channels
DISCORD_ENABLED=true
EMAIL_ENABLED=true
SEND_CONFIRMATION_ALERTS=false  # Reduce noise
```

---

## 🔍 Configuration Validation

### Test Your Configuration

```bash
# Test all components
python test_system.py

# Test specific component
python test_system.py --component config
python test_system.py --component notifications
python test_system.py --component squad
```

### Configuration Checklist

Before going live, verify:

- [ ] **Environment file**: `.env` exists and is properly formatted
- [ ] **Squad file**: Exists and loads correctly
- [ ] **Notifications**: At least one notification method enabled and tested
- [ ] **API access**: Connection to Sofascore API working
- [ ] **Monitoring schedule**: Appropriate intervals configured
- [ ] **Logging**: Log level and output configured
- [ ] **Security**: No sensitive data in version control

### Common Configuration Issues

#### "Configuration Error"
- Check `.env` file syntax
- Verify all required fields are set
- Run `python test_system.py --component config`

#### "Squad File Not Found"
- Check `SQUAD_FILE_PATH` setting
- Verify file exists and is readable
- Ensure proper CSV formatting

#### "Notification Failed"
- Test webhook URLs in browser
- Check email credentials
- Verify network connectivity

#### "API Connection Failed"
- Check internet connection
- Verify API endpoints are accessible
- Check firewall/proxy settings

---

## 🛡️ Security Best Practices

### Environment Variables

- **Never commit** `.env` files to version control
- **Use strong passwords** for email accounts
- **Rotate credentials** periodically
- **Limit webhook permissions** in Discord

### File Permissions

```bash
# Secure .env file
chmod 600 .env

# Secure squad file
chmod 644 my_roster.csv

# Secure log directory
chmod 755 logs/
chmod 644 logs/*.log
```

### Network Security

- **Use HTTPS** for all external communications
- **Validate input** from external sources
- **Rate limit** API calls appropriately
- **Monitor** for unusual activity

---

<div align="center">

**Need help with configuration? We're here to help!**

[GitHub Issues](https://github.com/your-username/LineupTracker/issues) · [Configuration Examples](../examples/) · [Setup Script](../setup.py)

</div>
