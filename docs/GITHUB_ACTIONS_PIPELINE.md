# GitHub Actions Pipeline Guide

## Overview

The LineupTracker dashboard uses a **two-workflow architecture** for automated data management and deployment:

1. **Data Update Workflow** (`update-data.yml`) - Scheduled data generation and commits
2. **Dashboard Deployment Workflow** (`deploy-dashboard.yml`) - Static site building and deployment

This approach provides reliable automation while maintaining data freshness and deployment efficiency.

## Workflows

### 1. Data Update Workflow (`update-data.yml`)

**Purpose**: Automatically generates fresh dashboard data and commits it to the repository.

**Triggers**:
- **Scheduled**: Every Thursday at 8:00 AM UTC
- **Manual**: Via workflow dispatch with optional force update

**What it does**:
1. ✅ Checks if data update is needed (skips if data < 6 hours old)
2. 🔄 Runs `python -m src.lineup_tracker.async_main export` to generate fresh data
3. ✅ Validates all required JSON files exist and are valid
4. 📝 Commits changes with descriptive metadata
5. 🚀 Pushes to main branch 
6. 🔄 Triggers dashboard deployment automatically

**Smart Features**:
- Avoids unnecessary updates (respects 6-hour cooldown)
- Comprehensive data validation 
- Rich commit messages with metadata
- Automatic deployment triggering
- Force update option for manual runs

### 2. Dashboard Deployment Workflow (`deploy-dashboard.yml`)

**Purpose**: Builds and deploys the React dashboard to GitHub Pages.

**Triggers**:
- **Code pushes**: When non-data files change on main branch
- **Manual**: Via workflow dispatch with optional fresh data generation
- **Automatic**: Triggered by successful data updates

**Enhanced Features**:
- ⚡ **Smart Data Handling**: Uses existing data if fresh, generates if stale/missing
- 🛡️ **Fallback Strategy**: Gracefully handles data generation failures
- ⏰ **Staleness Detection**: Automatically refreshes data older than 24 hours
- 🔄 **Force Refresh**: Manual option to regenerate data during deployment

**What it does**:
1. 🔍 Checks data freshness (< 24 hours)
2. 🔄 Generates fresh data if needed/requested  
3. ✅ Validates all required data files
4. 📦 Builds React application
5. 🚀 Deploys to GitHub Pages

## Configuration

### Required GitHub Secrets

Before the workflows can run, you need to set up the required secrets in your GitHub repository:

1. **Go to your GitHub repository**
2. **Navigate to Settings → Secrets and variables → Actions**  
3. **Add the following Repository Secrets:**

| Secret Name | Description | Example Value |
|-------------|-------------|---------------|
| `FANTRAX_LEAGUE_ID` | Your Fantrax league identifier | `ABC123DEF` |
| `FANTRAX_TEAM_ID` | Your specific team ID within the league | `456789` |

**To find your Fantrax IDs:**
- Go to your Fantrax league page
- Check the URL: `https://www.fantrax.com/fantasy/league/ABC123DEF/team/roster;teamId=456789`
- `ABC123DEF` = League ID, `456789` = Team ID

### Scheduling

The data update runs **every Thursday at 8:00 AM UTC**. To change this:

```yaml
schedule:
  # Cron format: minute hour day-of-month month day-of-week
  - cron: '0 8 * * 4'  # Thursday 8 AM UTC
```

Common alternatives:
```yaml
- cron: '0 6 * * 1'    # Monday 6 AM UTC  
- cron: '0 12 * * 3,6' # Wednesday & Saturday 12 PM UTC
- cron: '0 */6 * * *'  # Every 6 hours
```

### Data Freshness Thresholds

**Update Workflow**: 6-hour cooldown (prevents excessive updates)
**Deploy Workflow**: 24-hour staleness threshold (ensures reasonable freshness)

To modify these thresholds, update the Python time comparison logic in the respective workflow files.

## Usage

### Automatic Operation

1. **Weekly Updates**: Data refreshes every Thursday automatically
2. **Smart Deployment**: Dashboard redeploys when code or data changes
3. **Validation**: All data is validated before deployment

### Manual Control

#### Force Data Update
```bash
# Via GitHub UI
Actions → Update Dashboard Data → Run workflow
✅ Check "Force update even if recent data exists"
```

#### Force Deployment with Fresh Data
```bash  
# Via GitHub UI
Actions → Deploy Dashboard → Run workflow
✅ Check "Force fresh data generation during deployment"
```

#### Local Data Generation (for testing)
```bash
python -m src.lineup_tracker.async_main export --export-dir dashboard/public/data
```

## Monitoring

### Success Indicators

**Data Update Success**:
- ✅ New commit with "🤖 Automated data update" message
- ✅ All JSON files updated with current timestamp
- ✅ Dashboard deployment triggered automatically

**Deployment Success**:
- ✅ Green checkmark on GitHub Actions
- ✅ Dashboard accessible at GitHub Pages URL
- ✅ Fresh data visible in dashboard

### Common Issues & Solutions

#### Data Generation Fails
- **Symptom**: Workflow fails on data generation step
- **Solution**: Check if external APIs (Sofascore, Fantrax) are accessible
- **Fallback**: Use manual `workflow_dispatch` with existing data

#### Deployment Uses Stale Data
- **Symptom**: Dashboard shows old information
- **Solution**: Manually trigger data update workflow
- **Prevention**: Check that scheduled workflow is running correctly

#### Rate Limiting Issues
- **Symptom**: API timeout errors in logs
- **Solution**: Data workflow has built-in retry logic and rate limiting
- **Manual**: Wait and retry, or use existing data

## Architecture Benefits

### 🎯 **Separation of Concerns**
- Data management independent of deployment
- Each workflow can be modified/debugged separately

### ⚡ **Performance**  
- Deployment doesn't wait for data generation
- Can deploy code changes immediately
- Data updates don't trigger unnecessary rebuilds

### 🛡️ **Reliability**
- Multiple fallback strategies
- Comprehensive validation at each step
- Graceful degradation on API failures  

### 🔍 **Visibility**
- Clear commit history for data changes
- Detailed workflow logs for debugging
- Rich status reporting

## Advanced Configuration

### Custom Environment Variables

The workflows support all LineupTracker configuration via environment variables:

```yaml
env:
  FANTRAX_LEAGUE_ID: ${{ secrets.FANTRAX_LEAGUE_ID }}
  FANTRAX_TEAM_ID: ${{ secrets.FANTRAX_TEAM_ID }}
  # Add other config as needed
```

### Notification Integration

To add Discord/email notifications on workflow completion:

```yaml
- name: Send notification
  if: success()
  run: |
    # Your notification logic here
    curl -X POST $DISCORD_WEBHOOK -d '{"content":"✅ Dashboard updated!"}'
```

### Multi-Environment Support

For staging/production deployments:

```yaml
strategy:
  matrix:
    environment: [staging, production]
env:
  DEPLOY_ENV: ${{ matrix.environment }}
```

## Migration from Old System

### Before (Manual Process)
1. 👨‍💻 Developer runs export locally
2. 📝 Developer commits data files  
3. 🚀 Push triggers deployment
4. ❌ Easy to forget or get stale data

### After (Automated System)
1. ⏰ GitHub runs export automatically
2. 🤖 Commits fresh data with metadata
3. 🚀 Auto-triggers deployment  
4. ✅ Always fresh, never forgotten

### Transition Steps

1. ✅ New workflows are already in place
2. ✅ Existing data files will be respected
3. ✅ First scheduled run will update data
4. 📝 Remove manual export reminders from documentation
5. 🎉 Enjoy automated freshness!

## Troubleshooting

### Workflow Not Running

Check:
- ✅ Cron syntax is correct
- ✅ Repository has Actions enabled
- ✅ Workflow file is on main branch

### Data Generation Timeouts

The workflow has a 5-minute timeout for data generation. If this isn't sufficient:

```yaml
timeout 600 python -m src.lineup_tracker.async_main export  # 10 minutes
```

### Large Data Files

GitHub has file size limits. If data files become too large:
- Use Git LFS for large files
- Implement data compression
- Split into multiple smaller files

---

**🎉 Result**: Your dashboard now maintains fresh data automatically while providing manual control when needed!
