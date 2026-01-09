/**
 * Build script to inject Railway API URL into HTML templates
 * Run this during Vercel build to inject the API URL from environment variable
 */

const fs = require('fs');
const path = require('path');

const apiUrl = process.env.NEXT_PUBLIC_API_URL || process.env.API_URL || '';
const htmlFiles = [
  'web/templates/index.html',
  'web/templates/news.html',
  'web/templates/market.html',
  'web/templates/tools.html'
];

console.log(`Injecting API URL: ${apiUrl || '(empty - using relative paths)'}`);

htmlFiles.forEach(file => {
  const filePath = path.join(__dirname, file);
  
  if (!fs.existsSync(filePath)) {
    console.warn(`Warning: ${filePath} not found, skipping...`);
    return;
  }
  
  let content = fs.readFileSync(filePath, 'utf8');
  
  // Remove existing api-url meta tag if present
  content = content.replace(/<meta\s+name=["']api-url["'][^>]*>/gi, '');
  
  // Inject new meta tag right after <head>
  if (apiUrl) {
    const metaTag = `    <meta name="api-url" content="${apiUrl}">`;
    content = content.replace('<head>', `<head>\n${metaTag}`);
    console.log(`✓ Injected API URL into ${file}`);
  } else {
    console.warn(`⚠ No API URL provided for ${file} - will use relative paths`);
  }
  
  fs.writeFileSync(filePath, content, 'utf8');
});

console.log('Done!');

