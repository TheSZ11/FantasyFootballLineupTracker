# 📋 LineupTracker

> **Automated Fantasy Football Lineup Monitoring for Premier League**

Never miss when your expected starters are benched! LineupTracker monitors official Premier League lineups and sends instant notifications when they don't match your fantasy expectations.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

---

## 🎯 Key Features

- **🧠 Smart Scheduling**: Only monitors 60 minutes before matches (no 24/7 polling)
- **⚽ Premier League Focused**: Efficient API usage for PL matches only
- **📢 Multi-Platform Notifications**: Discord webhooks + Email alerts
- **📊 CSV Squad Management**: Simple file-based roster updates
- **🔓 No API Key Required**: Uses free Sofascore data source
- **⚡ Real-time Monitoring**: Checks every minute in final 5 minutes before kickoff
- **🎨 Rich Notifications**: Beautiful Discord embeds with player stats

---

## 🚀 Quick Start

### Automated Setup (Recommended)

```bash
# 1. Clone the repository
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run interactive setup
python setup.py
```

The setup script will guide you through:
- ✅ Dependency verification
- ⚙️ Environment configuration  
- 📧 Notification setup (Discord/Email)
- 📋 Squad file creation
- 🧪 System testing

### Manual Setup

<details>
<summary>Click to expand manual setup instructions</summary>

#### 1. Environment Setup

```bash
# Clone repository
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### 2. Configuration

Create your `.env` file:
```bash
cp env.example .env
```

Edit `.env` with your settings:
```bash
# Discord Notifications (recommended)
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your-webhook-url

# Email Notifications (optional)
EMAIL_ENABLED=false
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENT=recipient@example.com

# Squad Configuration
SQUAD_FILE_PATH=my_roster.csv
CHECK_INTERVAL_MINUTES=15
```

#### 3. Squad Setup

Choose one option:

**Option A: Fantrax Export (Recommended)**
1. Export your roster from Fantrax as CSV
2. Save as `my_roster.csv`
3. Set `Status` column: `Act` for starters, `Res` for bench

**Option B: Simple Format**
```csv
player_name,team_name,position,currently_starting,notes
Mohamed Salah,Liverpool,Forward,true,Captain choice
Erling Haaland,Manchester City,Forward,true,Premium striker
Kevin De Bruyne,Manchester City,Midfielder,false,Rotation risk
```

**Option C: Use Example**
```bash
cp examples/sample_roster.csv my_roster.csv
# Edit to match your actual team
```

</details>

---

## 🎮 Usage

### Start Monitoring
```bash
python main.py
```

### Test Your Setup
```bash
# Test all components
python test_system.py

# Test notifications only
python -c "from src.lineup_tracker.providers.discord_provider import DiscordProvider; provider = DiscordProvider('your-webhook'); provider.test_connection()"
```

### Monitor Logs
```bash
# View real-time logs
tail -f lineup_monitor.log

# Check for errors
grep "ERROR" lineup_monitor.log
```

---

## 📧 How It Works

### 🔍 Smart Monitoring Schedule

1. **📅 Daily Check (9 AM)**: Scans for matches in next 24 hours
2. **⏰ Pre-Match (60 min before)**: Starts active monitoring  
3. **🔄 Active Phase**: Checks every 15 minutes
4. **🏃 Final Sprint (5 min before)**: Checks every minute
5. **✅ Post-Match**: Stops monitoring completed matches

**Result**: Only ~6-10 API calls per match day instead of 100+

### 📱 Notification Types

#### 🚨 Urgent Alerts (Email + Discord)
- **Player Benched**: Expected starter is on the bench
- **Unexpected Starter**: Bench player is starting

#### ℹ️ Info Updates (Discord Only)  
- Lineup confirmations
- System status messages
- Connection tests

### 📋 Example Alert

```
🚨 Mohamed Salah BENCHED!

Team: Liverpool
Position: Forward  
Match: Liverpool vs Arsenal
Kickoff: 15:00
Avg Points: 18.4 per game

⚠️ You may want to update your lineup!
```

---

## 📁 Project Structure

```
LineupTracker/
├── 🚀 main.py                    # Application entry point
├── 📋 setup.py                   # Interactive setup script
├── 🧪 test_system.py            # System testing
├── ⚙️ requirements.txt           # Dependencies
├── 📄 .env                       # Your configuration
├── 📊 my_roster.csv             # Your squad data
│
├── 📂 src/lineup_tracker/        # Core application
│   ├── 🔧 config/               # Configuration management
│   ├── 🏗️ domain/               # Data models & interfaces  
│   ├── 🔄 services/             # Business logic
│   ├── 📡 providers/            # External integrations
│   ├── 💾 repositories/         # Data access
│   └── 🛠️ utils/                # Utilities
│
├── 📂 examples/                  # Example configurations
│   ├── sample_roster.csv        # Fantrax format example
│   └── simple_roster.csv        # Simple format example
│
└── 📂 tests/                     # Test suite
    ├── unit/                     # Unit tests
    └── integration/              # Integration tests
```

---

## 🔧 Configuration Options

<details>
<summary>📧 Discord Setup</summary>

1. Go to your Discord server
2. **Server Settings** → **Integrations** → **Create Webhook**
3. Copy webhook URL
4. Add to `.env`: `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...`

</details>

<details>
<summary>📨 Email Setup (Gmail)</summary>

1. Enable 2-Factor Authentication on Gmail
2. **Google Account** → **Security** → **App passwords**
3. Generate 16-character app password
4. Add to `.env`:
   ```
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-16-char-app-password
   EMAIL_RECIPIENT=recipient@example.com
   ```

</details>

<details>
<summary>📊 Squad File Formats</summary>

**Fantrax Export Format** (Recommended)
- Export from Fantrax with all stats
- Rich player data for enhanced notifications
- Set `Status`: `Act` for starters, `Res` for bench

**Simple Format**
- Just the essential columns
- Easy to create and edit manually
- Perfect for quick setup

</details>

---

## 🐛 Troubleshooting

<details>
<summary>🔴 Common Issues</summary>

### "No squad loaded"
- ✅ Check `my_roster.csv` exists in project directory
- ✅ Verify CSV has required columns
- ✅ Run `python test_system.py` to diagnose

### "API connection failed"  
- ✅ Check internet connection
- ✅ Verify Sofascore API is accessible
- ✅ Check firewall/proxy settings

### "Notification failed"
- **Discord**: Verify webhook URL is correct and channel exists
- **Email**: Check app password (not regular password) 
- ✅ Test with: `python test_system.py`

### "No matches detected"
- ✅ System only monitors Premier League matches
- ✅ Check if there are PL matches today
- ✅ Verify squad has players from teams playing

</details>

<details>
<summary>🔧 Advanced Configuration</summary>

Customize monitoring behavior in `.env`:

```bash
# Timing
CHECK_INTERVAL_MINUTES=15           # Normal check frequency
PRE_MATCH_WINDOW_MINUTES=60        # When to start monitoring
FINAL_SPRINT_MINUTES=5             # Minute-by-minute monitoring

# Notifications  
SEND_CONFIRMATION_ALERTS=true      # Confirm expected lineups
SEND_STARTUP_NOTIFICATIONS=true    # System start/stop messages

# Logging
LOG_LEVEL=INFO                      # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT=structured              # structured or simple
```

</details>

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### 🎯 Areas for Contribution

- 🌍 **Multi-League Support**: Add support for other leagues
- 📱 **New Notification Providers**: Slack, Telegram, SMS
- 🤖 **AI Features**: Lineup prediction, transfer suggestions  
- 🎨 **UI/Dashboard**: Web interface for monitoring
- 📊 **Analytics**: Player performance tracking
- 🧪 **Testing**: Improve test coverage

### 🚀 Quick Development Setup

```bash
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
pytest  # Run tests
```

---

## 📋 Roadmap

### 🎯 Future Enhancements
- [ ] 🌍 Multi-league support (La Liga, Serie A, etc.)
- [ ] 🤖 AI-powered lineup recommendations
- [ ] 📈 Historical performance analytics
- [ ] 🎮 Integration with popular fantasy platforms

---

## 📊 Performance & Limits

- **📡 API Calls**: ~6-10 per match day (well within free limits)
- **⚡ Response Time**: Real-time notifications within 30 seconds
- **💾 Memory Usage**: <50MB typical usage
- **🔋 CPU Usage**: Minimal background processing
- **📱 Supported Platforms**: Windows, macOS, Linux

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- **Sofascore** for providing free football data
- **Discord** for webhook notifications
- **Fantasy Premier League** community for inspiration
- All contributors who help improve the project
