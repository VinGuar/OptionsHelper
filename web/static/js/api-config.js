// API Configuration
// This allows the frontend to connect to the Railway backend
// Set via environment variable in Vercel or via meta tag

(function() {
    // Check for API URL from various sources (in order of priority):
    // 1. window.API_URL (set by Vercel build or script tag)
    // 2. Meta tag with name="api-url"
    // 3. Environment variable (for build-time injection)
    // 4. Default to relative paths (same origin)
    
    let apiBaseUrl = '';
    
    // Check window variable (can be set in index.html)
    if (typeof window !== 'undefined' && window.API_URL) {
        apiBaseUrl = window.API_URL;
    }
    // Check meta tag
    else if (typeof document !== 'undefined') {
        const metaTag = document.querySelector('meta[name="api-url"]');
        if (metaTag) {
            apiBaseUrl = metaTag.getAttribute('content') || '';
        }
    }
    
    // Remove trailing slash
    if (apiBaseUrl.endsWith('/')) {
        apiBaseUrl = apiBaseUrl.slice(0, -1);
    }
    
    // Export API helper function
    window.getApiUrl = function(path) {
        // Ensure path starts with /
        if (!path.startsWith('/')) {
            path = '/' + path;
        }
        return apiBaseUrl + path;
    };
    
    // Log API base URL for debugging (only in development)
    if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        console.log('API Base URL:', apiBaseUrl || '(using relative paths)');
    }
})();

