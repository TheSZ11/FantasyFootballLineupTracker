# 📊 LineupTracker Dashboard

> **Beautiful, responsive React dashboard for monitoring your fantasy football lineup status**

A modern web interface for the LineupTracker fantasy football monitoring system, built with React, Vite, and Tailwind CSS.

---

## 🎯 Overview

The LineupTracker Dashboard provides a clean, intuitive interface to monitor your fantasy football players' lineup status in real-time. It consumes data from the LineupTracker Python backend and displays it in an easy-to-read format with color-coded status indicators and team logos.

### Key Features

- **🎨 Modern UI**: Clean, responsive design with Tailwind CSS
- **⚡ Real-time Data**: Displays live data from Fantrax API
- **📱 Mobile Responsive**: Perfect on desktop, tablet, and mobile devices
- **🏈 Team Logos**: Official Premier League team logos for all players
- **🔄 Manual Refresh**: Click to update with latest data
- **🎯 Smart Filtering**: Filter by player status, matches today, etc.

---

## 🚀 Quick Start

### Development

```bash
# From the main LineupTracker directory
cd dashboard

# Install dependencies
npm install

# Export latest data from Fantrax API
python -m src.lineup_tracker.async_main export

# Start development server
npm run dev

# Open browser: http://localhost:5173/
```

### Production Build

```bash
# Export fresh data
python -m src.lineup_tracker.async_main export

# Build for production
npm run build

# Files will be in dist/ directory
```

---

## 📊 Data Integration

### Data Sources

The dashboard reads JSON files exported by the LineupTracker Python backend:

- **`squad.json`**: Complete roster with player names from Fantrax
- **`lineup_status.json`**: Real-time lineup status for each player
- **`matches.json`**: Today's Premier League matches
- **`status.json`**: System monitoring status
- **`metadata.json`**: Dashboard metadata and timestamps

### Data Flow

```
Fantrax API → Python Backend → JSON Export → React Dashboard
```

1. **Fantrax Integration**: Python backend fetches live roster data
2. **Player Mapping**: Uses `playerMapping.csv` for real player names
3. **SofaScore API**: Gets live lineup data for Premier League matches
4. **JSON Export**: Combines data into dashboard-friendly format
5. **React Display**: Dashboard renders the data with real-time status

---

## 🎨 User Interface

### Player Status Colors

- **🟢 Green (Starting)**: Player confirmed in starting XI
- **🔴 Red (Benched)**: Player confirmed on bench
- **🔮 Blue (Predicted)**: Predicted lineup available
- **⚪ Gray (No Match)**: Player's team has no match today

### Filter Options

- **All Players**: Complete roster view
- **Starters**: Only active players in your Fantrax team
- **Playing Today**: Players with matches today
- **With Predictions**: Players with lineup predictions available

### Header Information

- **System Status**: Current monitoring state
- **Last Updated**: Data freshness timestamp
- **Refresh Button**: Manual data reload
- **Player Counts**: Quick summary statistics

---

## 🔧 Configuration

### Repository Settings

If your GitHub repository name differs from "LineupTracker":

```javascript
// vite.config.js
export default defineConfig({
  base: '/YourRepositoryName/', // Update this line
  // ... other config
})
```

### Team Logo Customization

Team logos are automatically mapped using abbreviations (EVE, LIV, NEW, etc.). The mapping is defined in:

```javascript
// src/utils/teamLogos.js
const teamLogoMapping = {
  "EVE": "Everton FC.png",
  "LIV": "Liverpool FC.png",
  // ... other mappings
}
```

---

## 🚀 Deployment

### GitHub Pages (Recommended)

1. **Enable GitHub Pages**:
   - Repository Settings → Pages
   - Source: "GitHub Actions"

2. **Automatic Deployment**:
   - Push changes to main branch
   - GitHub Actions will build and deploy automatically

3. **Manual Deployment**:
   ```bash
   # Export data and build
   python -m src.lineup_tracker.async_main export
   npm run build
   
   # Deploy
   npm run deploy
   ```

### Other Hosting Options

The dashboard is a static React app and can be deployed to:
- **Netlify**: Drag and drop `dist/` folder
- **Vercel**: Connect GitHub repository
- **AWS S3**: Upload `dist/` contents
- **GitHub Pages**: Built-in GitHub hosting

---

## 🔄 Data Updates

### Updating Player Data

1. **Modify Fantrax Team**: Add/remove players in your fantasy league
2. **Export Fresh Data**: `python -m src.lineup_tracker.async_main export`
3. **Rebuild Dashboard**: `npm run build`
4. **Deploy**: Push changes or redeploy

### Automatic Updates

The dashboard data updates when:
- You export new data from the Python backend
- GitHub Actions workflow runs (on code changes)
- You manually refresh the browser

---

## 🛠️ Development

### Tech Stack

- **React 18**: Modern React with hooks
- **Vite**: Fast build tool and dev server
- **Tailwind CSS**: Utility-first CSS framework
- **ESLint**: Code quality and consistency

### Project Structure

```
dashboard/
├── public/
│   ├── data/              # JSON data files from Python backend
│   └── team-logos/        # Premier League team logo images
├── src/
│   ├── components/        # React components
│   │   ├── Dashboard.jsx  # Main dashboard component
│   │   ├── Header.jsx     # Status header with refresh
│   │   ├── PlayerCard.jsx # Individual player display
│   │   └── MatchOverview.jsx # Match information
│   ├── utils/
│   │   ├── teamLogos.js   # Team logo mapping utilities
│   │   └── matchUtils.js  # Match data processing
│   ├── App.jsx            # Main application component
│   └── main.jsx           # Application entry point
├── package.json           # Dependencies and scripts
├── vite.config.js         # Vite configuration
└── tailwind.config.js     # Tailwind CSS configuration
```

### Adding Features

**Common enhancement areas:**
- **Player Performance**: Historical stats and trends
- **Push Notifications**: Browser alerts for lineup changes
- **Advanced Filtering**: By position, team, form, etc.
- **Data Visualization**: Charts and graphs
- **Settings Panel**: User preferences and customization

---

## 🐛 Troubleshooting

### Dashboard Not Loading

1. **Check Data Files**: Ensure JSON files exist in `public/data/`
2. **Verify Export**: Run `python -m src.lineup_tracker.async_main export`
3. **Browser Console**: Look for JavaScript errors (F12 → Console)
4. **Clear Cache**: Hard refresh with Ctrl+F5 or Cmd+Shift+R

### Data Not Updating

1. **Re-export Data**: `python -m src.lineup_tracker.async_main export`
2. **Check File Timestamps**: Verify JSON files are recent
3. **Force Refresh**: Clear browser cache for the site
4. **Rebuild**: `npm run build` after data export

### GitHub Pages Issues

1. **Check Actions**: Repository → Actions tab for failed workflows
2. **Repository Name**: Verify `base` path in `vite.config.js`
3. **File Paths**: Ensure all assets are properly referenced
4. **Cache**: GitHub Pages has caching; changes may take a few minutes

---

## 📜 License

This dashboard is part of the LineupTracker project and is licensed under the MIT License.

---

## 🤝 Contributing

Contributions are welcome! Areas for improvement:

- **UI/UX Enhancements**: Better mobile experience, animations
- **Performance**: Optimize rendering for large rosters
- **Features**: New filtering options, data visualizations
- **Accessibility**: Screen reader support, keyboard navigation

### Development Setup

```bash
git clone https://github.com/your-username/LineupTracker.git
cd LineupTracker/dashboard
npm install
npm run dev
```

Submit pull requests with your improvements!

---

*Built with ❤️ for fantasy football managers who never want to miss a lineup change.*