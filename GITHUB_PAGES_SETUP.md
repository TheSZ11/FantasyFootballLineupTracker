# 🌐 GitHub Pages Deployment Guide

> **Complete step-by-step guide to deploy your LineupTracker Dashboard to GitHub Pages**

This guide will walk you through deploying your dashboard to GitHub Pages, making it accessible online for free at `https://your-username.github.io/LineupTracker/`.

---

## 📋 Prerequisites

- [x] LineupTracker project working locally
- [x] Dashboard set up and tested locally (`npm run dev` works)
- [x] GitHub account
- [x] Git installed on your computer

---

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Your Repository

#### 1.1 Check Your Current Status

```bash
# Navigate to your project directory
cd /path/to/your/LineupTracker

# Check git status
git status
```

#### 1.2 Commit All Changes

```bash
# Add all your new files
git add .

# Commit with a descriptive message
git commit -m "Add dashboard and GitHub Pages setup"

# Push to GitHub
git push origin main
```

If you don't have a GitHub repository yet, create one:

1. Go to [GitHub.com](https://github.com)
2. Click **"New repository"**
3. Name it **"LineupTracker"** (or your preferred name)
4. Make it **Public** (required for free GitHub Pages)
5. Click **"Create repository"**

Then connect your local project:

```bash
# Add GitHub as remote origin (replace with your username)
git remote add origin https://github.com/YOUR-USERNAME/LineupTracker.git

# Push your code
git branch -M main
git push -u origin main
```

### Step 2: Configure Dashboard for Your Repository

#### 2.1 Update Repository Name in Config

If your repository has a different name than "LineupTracker", update the config:

```javascript
// dashboard/vite.config.js
export default defineConfig({
  base: '/YourRepositoryName/', // Replace with your actual repo name
  // ... rest of config
})
```

#### 2.2 Test the Build Process

```bash
# Navigate to dashboard directory
cd dashboard

# Make sure dependencies are installed
npm install

# Test the build process
npm run build-with-data
```

This should create a `dist/` folder with your built dashboard.

### Step 3: Enable GitHub Pages

#### 3.1 Go to Repository Settings

1. Open your repository on GitHub
2. Click the **"Settings"** tab (at the top of the repository)
3. Scroll down to **"Pages"** in the left sidebar

#### 3.2 Configure Pages Settings

1. Under **"Source"**, select **"GitHub Actions"**
2. This will use the automated workflow we created
3. Click **"Save"** if prompted

### Step 4: Automatic Deployment

#### 4.1 Trigger the Workflow

The GitHub Actions workflow will run automatically when you push to the `main` branch:

```bash
# Make a small change to trigger deployment
git add .
git commit -m "Trigger GitHub Pages deployment"
git push origin main
```

#### 4.2 Monitor the Deployment

1. Go to your repository on GitHub
2. Click the **"Actions"** tab
3. You should see a workflow running called **"Deploy Dashboard to GitHub Pages"**
4. Click on it to see the progress

### Step 5: Access Your Live Dashboard

#### 5.1 Find Your Dashboard URL

Once deployment is complete (green checkmark), your dashboard will be live at:

```
https://YOUR-USERNAME.github.io/LineupTracker/
```

Replace `YOUR-USERNAME` with your GitHub username.

#### 5.2 Test Your Live Dashboard

1. Open the URL in your browser
2. You should see your roster with player cards
3. Test the filter tabs and refresh button

---

## 🔧 Manual Deployment (Alternative)

If you prefer manual deployment or the automated workflow isn't working:

### Option 1: Using npm script

```bash
cd dashboard

# This will export data, build, and deploy
npm run deploy
```

### Option 2: Manual build and push

```bash
cd dashboard

# Build with latest data
npm run build-with-data

# Install gh-pages if not already installed
npm install -g gh-pages

# Deploy to gh-pages branch
npx gh-pages -d dist
```

---

## 🔄 Updating Your Dashboard

### For Roster Changes

1. **Update your roster**:
   ```bash
   # Edit my_roster.csv with your changes
   # Then export fresh data
   python export_squad_only.py
   ```

2. **Commit and push**:
   ```bash
   git add .
   git commit -m "Update roster data"
   git push origin main
   ```

3. **Automatic redeploy**: GitHub Actions will automatically rebuild and redeploy!

### For Dashboard Code Changes

1. **Make your changes** to dashboard components
2. **Test locally**:
   ```bash
   cd dashboard
   npm run dev
   # Test your changes at http://localhost:5173/
   ```

3. **Deploy**:
   ```bash
   git add .
   git commit -m "Update dashboard features"
   git push origin main
   ```

---

## 🐛 Troubleshooting

### Deployment Fails

#### Check GitHub Actions Logs

1. Go to repository → **Actions** tab
2. Click on the failed workflow (red X)
3. Click on the failed job to see error details

#### Common Issues and Fixes

**❌ "Python dependencies failed"**
```yaml
# Make sure requirements.txt is in your repository root
# Check if requirements.txt has all necessary packages
```

**❌ "npm install failed"**
```bash
# Delete package-lock.json and try again
cd dashboard
rm package-lock.json
npm install
git add .
git commit -m "Fix npm dependencies"
git push origin main
```

**❌ "Build failed"**
```bash
# Test build locally first
cd dashboard
npm run build-with-data

# Check for any errors and fix them
# Then commit and push
```

### Dashboard Loads But Shows Errors

#### Check Browser Console

1. Open your dashboard in browser
2. Right-click → **"Inspect"** → **"Console"** tab
3. Look for red error messages

#### Common Issues

**❌ "404 error loading data files"**
- Check if `dashboard/public/data/` folder exists
- Run `python export_squad_only.py` to recreate data files
- Rebuild and redeploy

**❌ "Base path incorrect"**
- Check `base` setting in `dashboard/vite.config.js`
- Should match your repository name exactly

### Pages Not Updating

#### Force Redeploy

```bash
# Make an empty commit to trigger redeploy
git commit --allow-empty -m "Force redeploy"
git push origin main
```

#### Clear Browser Cache

- Hard refresh: `Ctrl+F5` (Windows) or `Cmd+Shift+R` (Mac)
- Or open in private/incognito browser window

---

## 🔐 Security and Privacy

### Public Repository Considerations

Since GitHub Pages requires a public repository for free accounts:

- **✅ Safe to include**: 
  - Player names (public information)
  - Team names (public information)
  - Fantasy points (personal stats)

- **❌ Never include**:
  - API keys or passwords
  - Personal email addresses
  - Discord webhook URLs

### Making Repository Private

If you have GitHub Pro, you can use private repositories with GitHub Pages:

1. Repository → **Settings** → **General**
2. Scroll to **"Danger Zone"**
3. Click **"Change repository visibility"**
4. Select **"Make private"**

---

## 🎯 Advanced Configuration

### Custom Domain (Optional)

To use your own domain instead of `github.io`:

1. **Buy a domain** from any registrar
2. **Add CNAME file**:
   ```bash
   # In dashboard/public/ directory
   echo "your-domain.com" > CNAME
   git add .
   git commit -m "Add custom domain"
   git push origin main
   ```

3. **Configure DNS** at your registrar:
   - Add CNAME record pointing to `your-username.github.io`

### Workflow Customization

Edit `.github/workflows/deploy-dashboard.yml` to:

- Change Python version
- Add environment variables
- Modify build steps
- Add testing steps

---

## 📊 Monitoring and Analytics

### GitHub Pages Analytics

GitHub provides basic analytics:

1. Repository → **Insights** → **Traffic**
2. View page views and visitor counts

### Google Analytics (Optional)

To add Google Analytics:

1. **Create Google Analytics account**
2. **Add tracking code** to `dashboard/index.html`:
   ```html
   <!-- Add before closing </head> tag -->
   <script async src="https://www.googletagmanager.com/gtag/js?id=GA_MEASUREMENT_ID"></script>
   <script>
     window.dataLayer = window.dataLayer || [];
     function gtag(){dataLayer.push(arguments);}
     gtag('js', new Date());
     gtag('config', 'GA_MEASUREMENT_ID');
   </script>
   ```

---

## ✅ Deployment Checklist

Before going live, verify:

- [ ] Dashboard works locally (`npm run dev`)
- [ ] Data export works (`python export_squad_only.py`)
- [ ] Build process works (`npm run build-with-data`)
- [ ] Repository is public (for free GitHub Pages)
- [ ] GitHub Pages is enabled with "GitHub Actions" source
- [ ] Base path in `vite.config.js` matches repository name
- [ ] All changes are committed and pushed
- [ ] GitHub Actions workflow completes successfully
- [ ] Live dashboard loads without errors
- [ ] Player data displays correctly
- [ ] Mobile layout works properly

---

## 🆘 Getting Help

### Official Documentation

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [Vite Deployment Guide](https://vitejs.dev/guide/static-deploy.html)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

### Community Support

- [LineupTracker Issues](https://github.com/your-username/LineupTracker/issues)
- [GitHub Community Forum](https://github.community/)
- [Stack Overflow](https://stackoverflow.com/questions/tagged/github-pages)

### Common Commands Reference

```bash
# Local development
cd dashboard && npm run dev

# Export data and build
cd dashboard && npm run build-with-data

# Manual deployment
cd dashboard && npm run deploy

# Check deployment status
git log --oneline -10

# Force redeploy
git commit --allow-empty -m "Redeploy" && git push origin main
```

---

🎉 **Congratulations!** Your LineupTracker Dashboard is now live on GitHub Pages!

Share your dashboard URL with friends and fellow fantasy football managers to show off your beautiful lineup tracking setup! 🚀⚽
