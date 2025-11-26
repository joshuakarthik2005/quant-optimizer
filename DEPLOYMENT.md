# Deployment Guide

This guide explains how to deploy your Quantitative Trading application with:
- **Frontend**: Vercel (Static files: HTML, CSS, JS)
- **Backend**: Render (Flask API + Python scripts)

---

## 🚀 Part 1: Deploy Backend to Render

### Step 1: Create Render Account
1. Go to [render.com](https://render.com)
2. Sign up with GitHub (recommended)

### Step 2: Push Code to GitHub
```powershell
# Initialize git repository (if not done)
git init
git add .
git commit -m "Initial commit: Sharpe Ratio Optimizer"

# Create new GitHub repository and push
git remote add origin https://github.com/YOUR_USERNAME/quant-optimizer.git
git branch -M main
git push -u origin main
```

### Step 3: Create Web Service on Render
1. Go to [Render Dashboard](https://dashboard.render.com/)
2. Click **"New +"** → **"Web Service"**
3. Connect your GitHub repository
4. Configure:
   - **Name**: `quant-optimizer-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
   - **Instance Type**: `Free`

### Step 4: Set Environment Variables (Optional)
- `PYTHON_VERSION`: `3.14.0`
- `FLASK_ENV`: `production`

### Step 5: Deploy
1. Click **"Create Web Service"**
2. Wait 3-5 minutes for deployment
3. Copy your backend URL: `https://quant-optimizer-api.onrender.com`

**⚠️ Important**: Render free tier sleeps after 15 minutes of inactivity. First request may take 30-60 seconds to wake up.

---

## 🌐 Part 2: Deploy Frontend to Vercel

### Step 1: Update Backend URL
Open `static/js/app.js` and replace the placeholder:

```javascript
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : 'https://quant-optimizer-api.onrender.com'; // ← Replace with your Render URL
```

### Step 2: Commit Changes
```powershell
git add static/js/app.js
git commit -m "Update API URL for production"
git push
```

### Step 3: Create Vercel Account
1. Go to [vercel.com](https://vercel.com)
2. Sign up with GitHub

### Step 4: Import Project
1. Click **"Add New..."** → **"Project"**
2. Import your GitHub repository
3. Vercel auto-detects configuration from `vercel.json`

### Step 5: Configure Build Settings
- **Framework Preset**: `Other`
- **Root Directory**: `./`
- **Build Command**: (leave empty)
- **Output Directory**: `./`

### Step 6: Deploy
1. Click **"Deploy"**
2. Wait 1-2 minutes
3. Your app is live at: `https://your-project.vercel.app`

---

## 🔧 Part 3: Update CORS Settings

After deploying to Vercel, update your backend CORS configuration:

1. Open `app.py` on your local machine
2. Replace the CORS origins:

```python
CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5000",
            "https://your-project.vercel.app"  # ← Replace with your Vercel URL
        ],
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})
```

3. Commit and push:
```powershell
git add app.py
git commit -m "Update CORS for Vercel domain"
git push
```

Render will automatically redeploy with the new settings.

---

## ✅ Testing Your Deployment

1. Visit your Vercel URL: `https://your-project.vercel.app`
2. Test Portfolio Optimizer:
   - Symbols: `AAPL,MSFT,GOOGL,AMZN`
   - Date Range: `2020-01-01` to `2024-01-01`
   - Click **Optimize Portfolio**
   - Wait 30-60 seconds for first request (Render cold start)
3. Verify charts load correctly
4. Test Static Backtest and Rolling Backtest tabs

---

## 🐛 Troubleshooting

### Issue: "Failed to fetch" error
**Solution**: Check browser console for CORS errors. Ensure:
- Backend URL in `app.js` matches your Render URL
- Vercel domain is added to CORS origins in `app.py`

### Issue: Backend timeout
**Solution**: Render free tier has 30-second timeout. For large date ranges:
- Reduce number of portfolios (default: 10,000 → try 5,000)
- Use shorter date ranges
- Upgrade to Render paid plan ($7/month for longer timeouts)

### Issue: Charts not showing
**Solution**: 
- Open browser DevTools → Network tab
- Check if API requests return 200 status
- Verify response JSON structure matches expected format

### Issue: "Application Error" on Render
**Solution**:
- Check Render logs: Dashboard → Your Service → Logs
- Common fixes:
  - Ensure `gunicorn` is in `requirements.txt`
  - Verify Python version compatibility
  - Check for missing dependencies

---

## 📊 Architecture

```
User Browser
    ↓
Vercel (Frontend)
    ├── index.html
    ├── style.css
    └── app.js → API calls
         ↓
Render (Backend)
    ├── Flask API
    ├── Optimizer
    ├── Backtester
    └── yfinance data
```

---

## 💡 Tips

1. **Custom Domain**: Add custom domain in Vercel settings for professional URL
2. **Environment Variables**: Use Vercel environment variables for API URLs instead of hardcoding
3. **Monitoring**: Enable Render metrics to track API performance
4. **Caching**: Add Redis on Render to cache yfinance data (reduces API calls)
5. **Analytics**: Add Vercel Analytics to track user engagement

---

## 🔄 Updating Your App

### Update Frontend
```powershell
# Make changes to HTML/CSS/JS
git add templates/ static/
git commit -m "Update frontend"
git push
```
Vercel auto-deploys on every push to `main` branch.

### Update Backend
```powershell
# Make changes to Python code
git add app.py scripts/
git commit -m "Update backend logic"
git push
```
Render auto-deploys on every push to `main` branch.

---

## 📝 Cost Breakdown

| Service | Plan | Cost | Limits |
|---------|------|------|--------|
| Vercel | Hobby | Free | 100GB bandwidth/month, unlimited deployments |
| Render | Free | Free | 750 hours/month, sleeps after 15min inactivity |

**Total**: $0/month for hobby projects

**Production Upgrade**:
- Render Standard: $7/month (no sleep, faster, better uptime)
- Vercel Pro: $20/month (more bandwidth, team features)

---

## 🎉 You're Done!

Your quantitative trading application is now live and accessible worldwide!

- **Frontend URL**: `https://your-project.vercel.app`
- **Backend URL**: `https://quant-optimizer-api.onrender.com`
- **GitHub Repo**: `https://github.com/YOUR_USERNAME/quant-optimizer`

Share your project and add it to your resume! 🚀
