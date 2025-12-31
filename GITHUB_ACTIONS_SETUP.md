# GitHub Actions Setup for Daily NBA Updates

This guide will help you set up automatic daily updates that run on GitHub's servers (no computer needed!).

## Setup Steps

### 1. Push Code to GitHub

Make sure all your code is committed and pushed to GitHub:

```bash
cd /Users/noaha/smartertips
git add .
git commit -m "Add daily update scripts and GitHub Actions workflow"
git push origin main
```

### 2. Add Database Secret to GitHub

Your database connection string needs to be stored securely as a GitHub Secret:

1. Go to your GitHub repository: https://github.com/NoahAizen44/SmarterTips
2. Click **Settings** (top right)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **New repository secret**
5. Name: `NEON_DSN`
6. Value: `postgresql://neondb_owner:npg_b5ncGCKrBX2k@ep-sweet-scene-a7et4vn2-pooler.ap-southeast-2.aws.neon.tech/neondb?sslmode=require`
7. Click **Add secret**

### 3. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. If prompted, click **I understand my workflows, go ahead and enable them**

### 4. Test the Workflow

You can manually trigger the workflow to test it:

1. Go to **Actions** tab
2. Click **Daily NBA Data Update** in the left sidebar
3. Click **Run workflow** dropdown (right side)
4. Click the green **Run workflow** button
5. Wait 2-3 minutes and check the results

### 5. Check the Schedule

The workflow is set to run automatically at:
- **2:00 AM EST (7:00 AM UTC)** every day
- This ensures all NBA games from the previous day are complete

To change the schedule, edit `.github/workflows/daily_update.yml` and modify the cron line:
```yaml
- cron: '0 7 * * *'  # Minute Hour Day Month DayOfWeek (UTC timezone)
```

Examples:
- `0 7 * * *` = 2:00 AM EST (7:00 AM UTC) - Current setting
- `0 12 * * *` = 7:00 AM EST (12:00 PM UTC)
- `0 3 * * *` = 10:00 PM EST previous day (3:00 AM UTC)

## How It Works

1. **GitHub Actions runs automatically** at 2 AM EST every day
2. **Step 1**: Updates team schedules with game results and player participation
3. **Step 2**: Updates player usage tables with stats and DNP entries
4. **All data is updated** without your computer being on!

## Monitoring

To check if updates are working:

1. Go to **Actions** tab
2. See the latest workflow run
3. Green checkmark ✅ = Success
4. Red X ❌ = Failed (click to see error logs)

## Cost

**100% FREE** for public repositories! GitHub provides:
- 2,000 minutes/month of Actions runtime (way more than needed)
- This workflow takes ~3-5 minutes per day
- That's ~150 minutes/month = well under the limit

## Troubleshooting

**If workflow fails:**
1. Click on the failed run in Actions tab
2. Click on the failed job to see error logs
3. Common issues:
   - Database secret not set correctly
   - NBA API rate limiting (rare)
   - Temporary network issues (will succeed next day)

**To disable:**
- Go to Actions tab → Click workflow → Click "..." → Disable workflow

**To re-enable:**
- Go to Actions tab → Click workflow → Click "Enable workflow"
