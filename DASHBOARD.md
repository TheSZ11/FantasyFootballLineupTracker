# 📊 LineupTracker Dashboard

> **Beautiful, responsive web dashboard for monitoring your fantasy football lineup status**

The LineupTracker Dashboard provides a clean, mobile-friendly interface to view your roster and player lineup statuses at a glance.

---

## 🌟 Features

- **🎯 Real-time Status**: Color-coded player cards showing lineup status
- **⚽ Match Overview**: Today's matches involving your players
- **📱 Mobile Responsive**: Perfect on desktop, tablet, and mobile
- **🔄 Manual Refresh**: Click to update with latest data
- **🎨 Clean Design**: Simple, focused interface
- **🆓 Free Hosting**: Deploy to GitHub Pages for free

---

## 🚀 Quick Start

### Prerequisites

- Node.js 18+ installed
- Your LineupTracker project set up with `my_roster.csv`

### 1. Set Up Dashboard Locally

```bash
# From your LineupTracker directory
cd dashboard

# Install dependencies (first time only)
npm install

# Export your roster data
npm run export-data

# Start development server
npm run dev

# Open in browser: http://localhost:5173/
```

### 2. Deploy to GitHub Pages

#### Option A: Automatic Deployment (Recommended)

1. **Commit and push your changes**:
   ```bash
   git add .
   git commit -m "Add dashboard setup"
   git push origin main
   ```

2. **Enable GitHub Pages**:
   - Go to your GitHub repository
   - Click **Settings** → **Pages**
   - Under **Source**, select **"GitHub Actions"**
   - The deployment will run automatically!

3. **Access your live dashboard**:
   - Your dashboard will be available at: `https://your-username.github.io/LineupTracker/`

#### Option B: Manual Deployment

```bash
cd dashboard

# Update data and build for production
npm run build-with-data

# Deploy to GitHub Pages
npm run deploy
```

---

## 📱 Dashboard Interface

### Player Status Cards

Each player is displayed as a card with color-coded status:

- **🟢 Starting (Green)**: Player is confirmed in the starting XI
- **🔴 Benched (Red)**: Player is confirmed on the bench
- **🟡 Pending (Yellow)**: Lineup not yet announced
- **⚪ No Match (Gray)**: Player's team has no match today

### Filter Tabs

Use the filter tabs to focus on specific players:

- **All Players**: Your complete roster
- **Starters**: Only players expected to start (Status = "Act" in CSV)
- **Playing Today**: Players whose teams have matches today
- **Pending**: Players with lineups not yet confirmed

### Header Information

The header shows:
- **System Status**: Whether monitoring is active
- **Last Updated**: When data was last refreshed
- **Refresh Button**: Click to reload data from server

---

## 🔧 Configuration

### Update Repository Name

If your GitHub repository has a different name than "LineupTracker":

```javascript
// dashboard/vite.config.js
export default defineConfig({
  base: '/YourRepositoryName/', // Change this line
  // ... rest of config
})
```

### Customize Team Colors

To customize team colors in the dashboard:

```javascript
// dashboard/src/components/PlayerCard.jsx
const getTeamColor = (teamName) => {
  const colors = {
    'Liverpool': 'border-red-500',
    'Manchester City': 'border-sky-500',
    'Arsenal': 'border-red-600',
    // Add your team colors here
  };
  return colors[teamName] || 'border-gray-300';
};
```

---

## 📊 Data Export

The dashboard reads data from JSON files exported by your Python application.

### Manual Export

```bash
# Quick export (bypasses API issues)
python export_squad_only.py

# Full export (requires working API connection)
python -m src.lineup_tracker.async_main export --export-dir dashboard/public/data
```

### Automatic Export

The dashboard npm scripts handle data export automatically:

```bash
# Export data only
npm run export-data

# Export data and build dashboard
npm run build-with-data
```

### Data Files

The exported data includes:

- **`squad.json`**: Your complete roster information
- **`lineup_status.json`**: Current lineup status for each player
- **`status.json`**: System monitoring status
- **`metadata.json`**: Dashboard metadata and refresh info

---

## 🔄 Updating Your Roster

### 1. Update CSV File

Edit your `my_roster.csv` file:
- Add/remove players
- Update player status (`Act` for starters, `Res` for bench)
- Modify any player information

### 2. Export Fresh Data

```bash
python export_squad_only.py
```

### 3. Rebuild Dashboard

```bash
cd dashboard
npm run build
```

### 4. Deploy Updates

```bash
git add .
git commit -m "Update roster"
git push origin main
```

The GitHub Actions workflow will automatically deploy your changes!

---

## 🐛 Troubleshooting

### Dashboard Won't Load

**Check browser console for errors:**
- Right-click → "Inspect" → "Console" tab
- Look for red error messages

**Common fixes:**
```bash
# Clear npm cache and reinstall
cd dashboard
rm -rf node_modules package-lock.json
npm install

# Rebuild data and dashboard
npm run build-with-data
```

### Data Not Updating

**Ensure data export is working:**
```bash
# Test data export
python export_squad_only.py

# Check if files were created
ls -la dashboard/public/data/
```

**Force refresh in browser:**
- Hard refresh: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
- Clear browser cache for the site

### GitHub Pages Not Working

**Check GitHub Actions:**
- Go to your repository → "Actions" tab
- Look for failed workflows (red X icons)
- Click on a failed workflow to see error details

**Common issues:**
- **Repository name mismatch**: Update `base` in `vite.config.js`
- **GitHub Pages not enabled**: Settings → Pages → Source: "GitHub Actions"
- **Missing files**: Ensure all dashboard files are committed and pushed

### Mobile Layout Issues

**Test responsive design:**
- Open browser dev tools (`F12`)
- Click the mobile/tablet icon
- Test different screen sizes

**Common fixes:**
- Check Tailwind CSS classes in components
- Ensure proper viewport meta tag in `index.html`

---

## 🔄 NPM Scripts Reference

```bash
# Development
npm run dev                 # Start development server

# Data Export
npm run export-data         # Export roster data only
npm run build-with-data     # Export data + build for production

# Building
npm run build              # Build for production (no data export)
npm run preview           # Preview production build locally

# Deployment
npm run deploy            # Deploy to GitHub Pages (manual)

# Maintenance
npm run lint              # Check code quality
```

---

## 📁 File Structure

```
dashboard/
├── 📦 public/                    # Static assets
│   ├── 📊 data/                  # Exported JSON data
│   │   ├── squad.json           # Your roster
│   │   ├── lineup_status.json   # Player statuses
│   │   ├── status.json          # System status
│   │   └── metadata.json        # Dashboard metadata
│   └── 🖼️ favicon.ico            # Site icon
│
├── 🎨 src/                       # Source code
│   ├── 🧩 components/            # React components
│   │   ├── Dashboard.jsx        # Main dashboard logic
│   │   ├── Header.jsx           # Status header + refresh
│   │   ├── PlayerCard.jsx       # Individual player cards
│   │   └── MatchOverview.jsx    # Today's matches
│   ├── 📄 App.jsx               # Main app component
│   ├── 🎨 App.css               # Global styles
│   ├── 🔧 index.css             # Tailwind directives
│   └── 🚀 main.jsx              # App entry point
│
├── ⚙️ package.json               # Dependencies and scripts
├── 🔧 vite.config.js             # Build configuration
├── 🎨 tailwind.config.js         # Tailwind CSS config
├── 📝 postcss.config.js          # PostCSS config
└── 📋 index.html                 # HTML template
```

---

## 🤝 Contributing

Want to improve the dashboard? Here are some ideas:

### 🎯 Feature Ideas

- **📈 Player Performance Graphs**: Historical points/minutes
- **🔔 Browser Notifications**: Alert when lineups change
- **⚙️ Settings Panel**: Customize colors, filters, refresh intervals
- **📊 Team Analysis**: Squad depth, upcoming fixtures
- **🎮 Fantasy Integration**: Direct platform connections

### 🛠️ Development Setup

```bash
# Clone and set up the project
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker/dashboard

# Install dependencies
npm install

# Start development server
npm run dev

# Make your changes and test
# Submit a pull request!
```

---

## 📜 License

This dashboard is part of the LineupTracker project and is licensed under the MIT License.

---

## 🙏 Acknowledgments

- **React + Vite**: Modern, fast development experience
- **Tailwind CSS**: Beautiful, responsive styling
- **GitHub Pages**: Free, reliable hosting
- **LineupTracker Community**: Ideas and feedback for improvements
