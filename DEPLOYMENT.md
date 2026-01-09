# Deployment Guide: Railway Backend + Vercel Frontend

This guide walks you through deploying your Options Scanner with the backend on Railway and frontend on Vercel.

## Architecture Overview

- **Backend (Railway)**: Flask API that handles scanning, market data, news, etc.
- **Frontend (Vercel)**: Static HTML/JS/CSS that calls the Railway backend API

## Prerequisites

1. GitHub account (your code should be in a GitHub repo)
2. Railway account (sign up at https://railway.app)
3. Vercel account (sign up at https://vercel.com)

---

## Part 1: Deploy Backend to Railway

### Step 1: Create Railway Project

1. Go to https://railway.app and sign in with GitHub
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Choose your repository
5. Railway will auto-detect it's a Python project

### Step 2: Configure Environment Variables

In your Railway project dashboard:

1. Go to **Variables** tab
2. Add these environment variables (if needed):

```
PORT=5000
FLASK_DEBUG=False
SCAN_TIMEOUT=300
CORS_ORIGINS=https://your-vercel-app.vercel.app,https://your-custom-domain.com
```

**Important**: Replace `your-vercel-app.vercel.app` with your actual Vercel domain (you'll get this after deploying to Vercel).

### Step 3: Deploy

Railway will automatically:
- Detect Python from `requirements.txt`
- Install dependencies
- Run `python app.py` (from Procfile)
- Expose your app on a public URL

### Step 4: Get Your Railway URL

1. After deployment, go to **Settings** → **Networking**
2. Click **Generate Domain** (or use the auto-generated one)
3. Copy the URL (e.g., `https://your-app.up.railway.app`)
4. **Save this URL** - you'll need it for Vercel!

### Step 5: Test Your Backend

Open in browser:
- `https://your-app.up.railway.app/api/strategies`

You should see JSON with strategy data. If you see an error, check Railway logs.

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Create Vercel Project

1. Go to https://vercel.com and sign in with GitHub
2. Click "Add New..." → "Project"
3. Import your GitHub repository
4. Vercel will auto-detect it's a static site

### Step 2: Configure Build Settings

**Root Directory**: Leave empty (or set to project root)

**Build Command**: Leave empty (static site, no build needed)

**Output Directory**: Leave empty (or set to `web` if you want)

**Install Command**: Leave empty (no dependencies for frontend)

### Step 3: Add Environment Variable for API URL

1. In Vercel project settings, go to **Environment Variables**
2. Add:

```
NEXT_PUBLIC_API_URL=https://your-app.up.railway.app
```

**Important**: Replace with your actual Railway URL from Part 1, Step 4.

### Step 4: Update HTML Templates (One-Time Setup)

You need to inject the API URL into your HTML. Two options:

#### Option A: Meta Tag (Recommended)

Add this to the `<head>` of all HTML templates (`index.html`, `news.html`, `market.html`, `tools.html`):

```html
<meta name="api-url" content="https://your-app.up.railway.app">
```

Or use a build-time script to inject it from the environment variable.

#### Option B: Script Tag (Alternative)

Add this before `api-config.js` in all HTML templates:

```html
<script>
    window.API_URL = 'https://your-app.up.railway.app';
</script>
<script src="/static/js/api-config.js"></script>
```

**For Vercel**: You can use a build script to inject the environment variable. Create `vercel.json`:

```json
{
  "buildCommand": "node inject-api-url.js"
}
```

And create `inject-api-url.js`:

```javascript
const fs = require('fs');
const path = require('path');

const apiUrl = process.env.NEXT_PUBLIC_API_URL || '';
const htmlFiles = [
  'web/templates/index.html',
  'web/templates/news.html',
  'web/templates/market.html',
  'web/templates/tools.html'
];

htmlFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Inject meta tag if not present
  if (!content.includes('name="api-url"')) {
    content = content.replace(
      '<head>',
      `<head>\n    <meta name="api-url" content="${apiUrl}">`
    );
  }
  
  fs.writeFileSync(filePath, content);
});
```

### Step 5: Deploy

1. Click **Deploy**
2. Vercel will build and deploy your frontend
3. You'll get a URL like `https://your-app.vercel.app`

### Step 6: Update Railway CORS

Go back to Railway and update the `CORS_ORIGINS` variable:

```
CORS_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

Railway will automatically redeploy.

---

## Part 3: Testing & Verification

### Test Frontend → Backend Connection

1. Open your Vercel URL
2. Open browser DevTools (F12) → Console
3. You should see: `API Base URL: https://your-app.up.railway.app`
4. Try running a scan
5. Check Network tab - API calls should go to Railway URL

### Common Issues

**CORS Errors**:
- Make sure `CORS_ORIGINS` in Railway includes your Vercel domain
- Check that the domain matches exactly (including `https://`)

**404 on API calls**:
- Verify the Railway URL is correct in your HTML meta tag
- Check browser console for the actual API URL being used

**Scan timeouts**:
- Check Railway logs for errors
- Verify `SCAN_TIMEOUT` is set appropriately (default 300s)

---

## Part 4: Custom Domain (Optional)

### Vercel Custom Domain

1. In Vercel project → **Settings** → **Domains**
2. Add your domain
3. Follow DNS instructions

### Railway Custom Domain

1. In Railway project → **Settings** → **Networking**
2. Add custom domain
3. Update `CORS_ORIGINS` to include your custom domain

---

## Part 5: Monitoring & Updates

### Railway Logs

- View logs in Railway dashboard
- Check for errors, timeouts, or rate limiting

### Vercel Logs

- View deployment logs in Vercel dashboard
- Check for build errors

### Updating Code

1. Push changes to GitHub
2. Railway auto-deploys (if connected to GitHub)
3. Vercel auto-deploys (if connected to GitHub)
4. Both will rebuild automatically

---

## Environment Variables Summary

### Railway (Backend)

```
PORT=5000
FLASK_DEBUG=False
SCAN_TIMEOUT=300
CORS_ORIGINS=https://your-vercel-app.vercel.app
```

### Vercel (Frontend)

```
NEXT_PUBLIC_API_URL=https://your-railway-app.up.railway.app
```

---

## Performance Tips

1. **Caching**: The backend now caches scan results for 5 minutes. Repeated scans within 5 min return cached data.

2. **Scan Timeout**: Default is 300s (5 min). Adjust `SCAN_TIMEOUT` if scans take longer.

3. **Rate Limiting**: yfinance may throttle. Consider upgrading to a paid API (Polygon/Tradier) for production.

4. **Monitoring**: Set up Railway alerts for failed deployments or high error rates.

---

## Troubleshooting

### Backend won't start on Railway

- Check `Procfile` exists and has `web: python app.py`
- Verify `requirements.txt` has all dependencies
- Check Railway logs for Python errors

### Frontend can't connect to backend

- Verify Railway URL is correct in Vercel env var
- Check CORS settings in Railway
- Test Railway URL directly in browser

### Scans are slow

- This is expected with yfinance from cloud IPs
- Consider caching (already implemented)
- Consider upgrading to paid API

---

## Next Steps

1. ✅ Deploy backend to Railway
2. ✅ Deploy frontend to Vercel
3. ✅ Connect them together
4. 🔄 Monitor performance
5. 🔄 Consider upgrading to paid market data API
6. 🔄 Add Redis for better caching (optional)

---

## Support

- Railway docs: https://docs.railway.app
- Vercel docs: https://vercel.com/docs
- Check logs in both platforms for errors

