# Local Development Guide

This guide shows you how to run the Options Scanner locally for development.

## Quick Start

### Option 1: Run Everything Locally (Recommended)

The backend serves both the API and the frontend templates, so you can run everything with one command:

```bash
python app.py
```

Then open: http://localhost:5000

**That's it!** The frontend will automatically use relative paths to connect to the local backend.

---

## Detailed Setup

### Prerequisites

1. **Python 3.8+** installed
2. **Dependencies** installed:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Backend

1. **Start the Flask server:**
   ```bash
   python app.py
   ```

2. **The app will:**
   - Start on `http://localhost:5000`
   - Serve the frontend templates
   - Serve the API endpoints
   - Enable debug mode (auto-reload on code changes)

3. **You should see:**
   ```
   ==================================================
     OPTIONS EDGE SCANNER
     Running on port 5000
   ==================================================
   ```

### Accessing the App

- **Main Scanner**: http://localhost:5000
- **News & Flow**: http://localhost:5000/news
- **Current Market**: http://localhost:5000/market
- **Tools**: http://localhost:5000/tools

### API Endpoints (for testing)

- **Strategies**: http://localhost:5000/api/strategies
- **Start Scan**: `POST http://localhost:5000/api/scan/start`
- **Scan Status**: http://localhost:5000/api/scan/status
- **Scan Results**: http://localhost:5000/api/scan/results

---

## Local Development Configuration

### Environment Variables (Optional)

Create a `.env` file in the project root (optional):

```env
FLASK_DEBUG=True
SCAN_TIMEOUT=300
CORS_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
```

The app will work without this file - these are just defaults.

### How API URL Detection Works Locally

The `api-config.js` file checks for the API URL in this order:

1. `window.API_URL` (if set in HTML)
2. Meta tag `<meta name="api-url" content="...">`
3. Falls back to **relative paths** (empty string)

When running locally with `python app.py`, the frontend and backend are on the same origin (`localhost:5000`), so relative paths work perfectly - no configuration needed!

---

## Development Workflow

### Making Backend Changes

1. Edit Python files (`app.py`, `src/**/*.py`)
2. Flask auto-reloads (if `debug=True`)
3. Refresh browser to see changes

### Making Frontend Changes

1. Edit HTML/CSS/JS files (`web/templates/*.html`, `web/static/**/*`)
2. Refresh browser to see changes
3. No build step needed (static files)

### Testing API Changes

Use browser DevTools or curl:

```bash
# Test strategies endpoint
curl http://localhost:5000/api/strategies

# Test scan start
curl -X POST http://localhost:5000/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{"strategy": "1", "type": "quick"}'

# Check scan status
curl http://localhost:5000/api/scan/status
```

---

## Troubleshooting

### Port Already in Use

If port 5000 is taken:

1. **Option A**: Kill the process using port 5000
   ```bash
   # Windows
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   
   # Mac/Linux
   lsof -ti:5000 | xargs kill
   ```

2. **Option B**: Change the port in `app.py`:
   ```python
   port = int(os.getenv('PORT', 8080))  # Use 8080 instead
   ```

### API Calls Failing

1. **Check browser console** (F12) for errors
2. **Verify backend is running**: http://localhost:5000/api/strategies
3. **Check CORS**: Should work locally (same origin)

### Scans Not Working

1. **Check internet connection** (yfinance needs internet)
2. **Check Railway logs** if testing against Railway backend
3. **Try quick scan first** (fewer tickers = faster)

---

## Testing Against Railway Backend (Optional)

If you want to test the frontend locally but use the Railway backend:

1. **Start a local web server** (just for frontend):
   ```bash
   # Python 3
   cd web
   python -m http.server 3000
   ```

2. **Set API URL** in `web/templates/index.html` (temporarily):
   ```html
   <meta name="api-url" content="https://your-railway-app.up.railway.app">
   ```

3. **Open**: http://localhost:3000

4. **Note**: You'll need to configure CORS in Railway to allow `http://localhost:3000`

This is useful for testing frontend changes without running the full backend locally.

---

## Development Tips

### Faster Iteration

- Use **quick scans** (30 tickers) instead of full scans (100+ tickers)
- **Caching** is enabled - repeated scans within 5 min are instant
- **Debug mode** shows detailed error messages

### Testing Different Strategies

Change the strategy in the UI or test directly:
```bash
curl -X POST http://localhost:5000/api/scan/start \
  -H "Content-Type: application/json" \
  -d '{"strategy": "2", "type": "quick"}'
```

### Monitoring Performance

- Check Flask console output for scan progress
- Use browser DevTools Network tab to see API calls
- Check timing in browser console

---

## Common Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python app.py

# Run with custom port
PORT=8080 python app.py

# Run with debug off
FLASK_DEBUG=False python app.py

# Test API endpoint
curl http://localhost:5000/api/strategies
```

---

## Next Steps

- ✅ Run locally: `python app.py`
- ✅ Open: http://localhost:5000
- ✅ Test scans
- 🔄 Make changes
- 🔄 Refresh to see updates

That's all you need for local development!

