# Quick Deployment Checklist

## Railway Backend (5 minutes)

1. **Sign up**: https://railway.app → Sign in with GitHub
2. **New Project** → Deploy from GitHub repo → Select your repo
3. **Add Environment Variables**:
   ```
   PORT=5000
   FLASK_DEBUG=False
   SCAN_TIMEOUT=300
   CORS_ORIGINS=https://your-vercel-app.vercel.app
   ```
   (Update CORS_ORIGINS after you get your Vercel URL)
4. **Get Railway URL**: Settings → Networking → Copy the URL
5. **Test**: Open `https://your-railway-url.up.railway.app/api/strategies` in browser

## Vercel Frontend (5 minutes)

1. **Sign up**: https://vercel.com → Sign in with GitHub
2. **Add New Project** → Import your GitHub repo
3. **Add Environment Variable**:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-url.up.railway.app
   ```
   (Use the Railway URL from step above)
4. **Deploy** → Vercel auto-deploys
5. **Get Vercel URL**: Copy the deployment URL
6. **Update Railway CORS**: Go back to Railway, update `CORS_ORIGINS` with your Vercel URL

## Test It

1. Open your Vercel URL
2. Open browser console (F12)
3. Should see: `API Base URL: https://your-railway-url...`
4. Run a scan - it should work!

## That's It! 🎉

Your app is now:
- ✅ Backend on Railway (persistent, no timeouts)
- ✅ Frontend on Vercel (fast CDN)
- ✅ Connected and working

## Troubleshooting

**CORS errors?**
- Make sure Railway `CORS_ORIGINS` includes your exact Vercel URL (with https://)

**API calls failing?**
- Check Railway URL is correct in Vercel env var
- Check browser console for actual API URL being used

**Need help?**
- See `DEPLOYMENT.md` for detailed guide

