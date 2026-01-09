// News & Flow Page JavaScript - Revamped

class NewsFlowPage {
    constructor() {
        this.currentFilter = 'all';
        this.flowData = [];
        this.newsData = [];
        this.CACHE_KEY_NEWS = 'options_news_cache';
        this.CACHE_KEY_FLOW = 'options_flow_cache';
        this.init();
    }
    
    init() {
        this.bindEvents();
        // Load cached data on initialization
        this.loadCachedData();
    }
    
    // Cache methods
    getCache(key) {
        try {
            const cache = localStorage.getItem(key);
            return cache ? JSON.parse(cache) : null;
        } catch (e) {
            return null;
        }
    }
    
    saveToCache(key, data, timestamp) {
        try {
            const cacheData = {
                data: data,
                timestamp: timestamp || new Date().toISOString()
            };
            localStorage.setItem(key, JSON.stringify(cacheData));
        } catch (e) {
            console.error('Failed to save to cache:', e);
        }
    }
    
    loadCachedData() {
        try {
            // Load cached flow data
            const cachedFlow = this.getCache(this.CACHE_KEY_FLOW);
            if (cachedFlow && cachedFlow.data && Array.isArray(cachedFlow.data) && cachedFlow.data.length > 0) {
                this.flowData = cachedFlow.data;
                this.renderFlow();
                if (cachedFlow.timestamp) {
                    this.updateTimestamp('flow-timestamp', cachedFlow.timestamp);
                }
                const metaEl = document.getElementById('flow-meta');
                if (metaEl && cachedFlow.timestamp) {
                    const time = new Date(cachedFlow.timestamp).toLocaleTimeString();
                    metaEl.textContent = `Updated: ${time} • ${this.flowData.length} tickers with unusual flow`;
                }
            }
            
            // Load cached news data
            const cachedNews = this.getCache(this.CACHE_KEY_NEWS);
            if (cachedNews && cachedNews.data && Array.isArray(cachedNews.data) && cachedNews.data.length > 0) {
                this.newsData = cachedNews.data;
                this.renderNews(cachedNews.data);
                if (cachedNews.timestamp) {
                    this.updateTimestamp('news-timestamp', cachedNews.timestamp);
                }
                const metaEl = document.getElementById('news-meta');
                if (metaEl && cachedNews.timestamp) {
                    const time = new Date(cachedNews.timestamp).toLocaleTimeString();
                    metaEl.textContent = `Updated: ${time} • ${cachedNews.data.length} articles`;
                }
            }
        } catch (error) {
            console.error('Error loading cached data:', error);
        }
    }
    
    bindEvents() {
        // Refresh all button
        document.getElementById('btn-refresh-all').addEventListener('click', () => {
            this.refreshAll();
        });
        
        // Individual refresh buttons
        document.getElementById('btn-refresh-news').addEventListener('click', () => {
            this.refreshNews();
        });
        
        document.getElementById('btn-refresh-flow').addEventListener('click', () => {
            this.refreshFlow();
        });
        
        // Flow info toggle
        document.getElementById('btn-flow-info').addEventListener('click', () => {
            document.getElementById('flow-info-panel').classList.toggle('active');
        });
        
        document.getElementById('btn-close-info').addEventListener('click', () => {
            document.getElementById('flow-info-panel').classList.remove('active');
        });
        
        // Flow filters
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.currentFilter = e.target.dataset.filter;
                this.renderFlow();
            });
        });
    }
    
    async refreshAll() {
        const btn = document.getElementById('btn-refresh-all');
        btn.disabled = true;
        btn.classList.add('loading');
        
        await Promise.all([
            this.refreshFlow(),
            this.refreshNews(),
        ]);
        
        btn.disabled = false;
        btn.classList.remove('loading');
    }
    
    async refreshNews() {
        const btn = document.getElementById('btn-refresh-news');
        const list = document.getElementById('news-list');
        const meta = document.getElementById('news-meta');
        
        btn.classList.add('loading');
        list.innerHTML = '<div class="loading-state">Loading stock news...</div>';
        
        try {
            const response = await fetch(getApiUrl('/api/news/market'));
            const data = await response.json();
            
            if (data.news && data.news.length > 0) {
                this.newsData = data.news;
                this.renderNews(data.news);
                this.updateTimestamp('news-timestamp', data.timestamp);
                this.saveToCache(this.CACHE_KEY_NEWS, data.news, data.timestamp);
                const time = new Date(data.timestamp).toLocaleTimeString();
                meta.textContent = `Updated: ${time} • ${data.news.length} articles`;
            } else {
                list.innerHTML = '<div class="loading-state">No news found</div>';
            }
        } catch (error) {
            console.error('News error:', error);
            list.innerHTML = '<div class="loading-state">Failed to load news</div>';
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    renderNews(news) {
        const list = document.getElementById('news-list');
        
        list.innerHTML = news.slice(0, 15).map(item => {
            const ticker = item.ticker || 'MARKET';
            const isMarket = ticker === 'MARKET';
            const categories = item.categories || ['general'];
            
            const sentiment = item.sentiment || {};
            const sentimentSignal = sentiment.signal || 'neutral';
            
            let newsClass = '';
            if (sentimentSignal.includes('bullish')) {
                newsClass = 'bullish-news';
            } else if (sentimentSignal.includes('bearish')) {
                newsClass = 'bearish-news';
            } else if (item.impact === 'high') {
                newsClass = 'high-impact';
            }
            
            let sentimentBadge = '';
            if (sentimentSignal !== 'neutral') {
                const badgeClass = sentimentSignal.includes('bullish') ? 'bullish' : 'bearish';
                sentimentBadge = `<span class="sentiment-badge ${badgeClass}">${sentimentSignal}</span>`;
            }
            
            let timeStr = this.formatTime(item.published);
            
            return `
                <div class="news-item ${newsClass}">
                    <div class="news-item-header">
                        <span class="news-ticker ${isMarket ? 'market' : ''}">${ticker}</span>
                        <div class="news-sentiment">
                            ${sentimentBadge}
                            <div class="news-categories">
                                ${categories.slice(0, 2).map(cat => `<span class="news-category ${cat}">${cat}</span>`).join('')}
                            </div>
                        </div>
                    </div>
                    <div class="news-title">
                        <a href="${item.link || '#'}" target="_blank" rel="noopener">${item.title || 'No title'}</a>
                    </div>
                    ${item.summary ? `<div class="news-summary">${this.stripHtml(item.summary)}</div>` : ''}
                    <div class="news-footer">
                        <span>${item.source || 'Unknown'}</span>
                        <span>${timeStr}</span>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    formatTime(published) {
        if (!published) return '';
        try {
            const date = new Date(published);
            if (!isNaN(date)) {
                return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
            }
            return published;
        } catch {
            return published;
        }
    }
    
    stripHtml(html) {
        const tmp = document.createElement('div');
        tmp.innerHTML = html;
        return tmp.textContent || tmp.innerText || '';
    }
    
    async refreshFlow() {
        const btn = document.getElementById('btn-refresh-flow');
        const list = document.getElementById('flow-list');
        const meta = document.getElementById('flow-meta');
        
        btn.classList.add('loading');
        list.innerHTML = '<div class="loading-state">Scanning for unusual options activity...</div>';
        
        try {
            const response = await fetch(getApiUrl('/api/flow'));
            const data = await response.json();
            
            this.flowData = data.unusual_flow || [];
            this.renderFlow();
            this.updateTimestamp('flow-timestamp', data.timestamp);
            this.saveToCache(this.CACHE_KEY_FLOW, this.flowData, data.timestamp);
            
            const time = new Date(data.timestamp).toLocaleTimeString();
            meta.textContent = `Updated: ${time} • ${this.flowData.length} tickers with unusual flow`;
            
        } catch (error) {
            console.error('Flow error:', error);
            list.innerHTML = '<div class="loading-state">Failed to load flow data</div>';
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    renderFlow() {
        const list = document.getElementById('flow-list');
        
        let filtered = this.flowData;
        if (this.currentFilter !== 'all') {
            if (this.currentFilter === 'bullish') {
                filtered = this.flowData.filter(f => f.sentiment && f.sentiment.includes('bullish'));
            } else if (this.currentFilter === 'bearish') {
                filtered = this.flowData.filter(f => f.sentiment && f.sentiment.includes('bearish'));
            } else if (this.currentFilter === 'whale') {
                filtered = this.flowData.filter(f => (f.total_premium || 0) >= 5000000);
            }
        }
        
        if (filtered.length === 0) {
            list.innerHTML = '<div class="loading-state">No matching flow data</div>';
            return;
        }
        
        list.innerHTML = filtered.slice(0, 15).map(item => {
            const sentiment = item.sentiment || 'mixed';
            const isBullish = sentiment.includes('bullish');
            const isBearish = sentiment.includes('bearish');
            const sentimentClass = isBullish ? 'bullish' : (isBearish ? 'bearish' : 'mixed');
            const sentimentIcon = isBullish ? '🟢' : (isBearish ? '🔴' : '⚪');
            
            const totalPremium = this.formatPremium(item.total_premium || 0);
            const callPremium = this.formatPremium(item.call_premium || 0);
            const putPremium = this.formatPremium(item.put_premium || 0);
            const callRatio = item.call_ratio || 50;
            const putRatio = item.put_ratio || 50;
            const maxVolOi = item.max_vol_oi || 0;
            
            const flags = item.flags || [];
            const flagsHtml = flags.slice(0, 3).map(flag => {
                let flagClass = 'unusual';
                if (flag.includes('WHALE') || flag.includes('$5M') || flag.includes('$1M')) {
                    flagClass = 'whale';
                } else if (flag.includes('OTM')) {
                    flagClass = 'otm';
                } else if (flag.includes('Weekly')) {
                    flagClass = 'weekly';
                }
                return `<span class="flow-flag ${flagClass}">${flag}</span>`;
            }).join('');
            
            return `
                <div class="flow-item ${sentimentClass}">
                    <div class="flow-ticker-section">
                        <div class="flow-ticker">${item.ticker || 'N/A'}</div>
                        <div class="flow-sentiment-mini">
                            <span class="flow-sentiment-icon">${sentimentIcon}</span>
                            <span class="flow-sentiment-label ${sentimentClass}">${sentiment}</span>
                        </div>
                    </div>
                    <div class="flow-breakdown">
                        <div class="flow-bar">
                            <div class="flow-bar-calls" style="width: ${callRatio}%"></div>
                            <div class="flow-bar-puts" style="width: ${putRatio}%"></div>
                        </div>
                        <div class="flow-bar-labels">
                            <span class="calls-label">Calls: ${callPremium} (${callRatio}%)</span>
                            <span class="puts-label">Puts: ${putPremium} (${putRatio}%)</span>
                        </div>
                        ${flagsHtml ? `<div class="flow-flags">${flagsHtml}</div>` : ''}
                    </div>
                    <div class="flow-total">
                        <div class="flow-premium">${totalPremium}</div>
                        <div class="flow-detail">Total flow</div>
                        ${maxVolOi > 0 ? `<div class="flow-ratio">Vol/OI: ${maxVolOi}x</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    formatPremium(value) {
        if (value == null || isNaN(value)) return '$0';
        if (value >= 1000000) return '$' + (value / 1000000).toFixed(1) + 'M';
        if (value >= 1000) return '$' + Math.round(value / 1000) + 'K';
        return '$' + Math.round(value);
    }
    
    formatNumber(value) {
        if (value == null || isNaN(value)) return '0';
        if (value >= 1000000) return (value / 1000000).toFixed(1) + 'M';
        if (value >= 1000) return (value / 1000).toFixed(1) + 'K';
        return value.toLocaleString();
    }
    
    updateTimestamp(elementId, timestamp) {
        const el = document.getElementById(elementId);
        if (!el) return;
        
        if (!timestamp) {
            el.querySelector('.timestamp-text').textContent = 'Not yet loaded';
            return;
        }
        
        const date = new Date(timestamp);
        const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        const timeStr = date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        
        el.querySelector('.timestamp-text').textContent = `Last updated: ${dateStr} at ${timeStr}`;
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.newsFlow = new NewsFlowPage();
});
