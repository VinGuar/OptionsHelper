// News & Flow Page JavaScript

class NewsFlowPage {
    constructor() {
        this.currentFilter = 'all';
        this.flowData = [];
        this.init();
    }
    
    init() {
        this.bindEvents();
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
            this.refreshNews(),
            this.refreshFlow(),
        ]);
        
        btn.disabled = false;
        btn.classList.remove('loading');
    }
    
    async refreshNews() {
        const btn = document.getElementById('btn-refresh-news');
        const list = document.getElementById('news-list');
        const meta = document.getElementById('news-meta');
        
        btn.classList.add('loading');
        list.innerHTML = '<div class="loading-state">Loading stock news with sentiment analysis...</div>';
        
        try {
            const response = await fetch('/api/news/market');
            const data = await response.json();
            
            if (data.news && data.news.length > 0) {
                this.renderNews(data.news);
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
        
        list.innerHTML = news.map(item => {
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
            
            let timeStr = '';
            if (item.published) {
                try {
                    const date = new Date(item.published);
                    if (!isNaN(date)) {
                        timeStr = date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    } else {
                        timeStr = item.published;
                    }
                } catch {
                    timeStr = item.published;
                }
            }
            
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
            const response = await fetch('/api/flow');
            const data = await response.json();
            
            this.flowData = data.unusual_flow || [];
            this.renderFlow();
            
            const time = new Date(data.timestamp).toLocaleTimeString();
            meta.textContent = `Updated: ${time} • ${this.flowData.length} tickers with unusual flow`;
            
            this.renderSentiment(data.sentiment);
            this.renderMostActive(data.most_active);
            this.renderMovers(data.movers);
            
        } catch (error) {
            console.error('Flow error:', error);
            list.innerHTML = '<div class="loading-state">Failed to load flow data</div>';
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    renderFlow() {
        const list = document.getElementById('flow-list');
        
        // Filter data
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
            list.innerHTML = '<div class="loading-state">No matching flow data. Try refreshing or changing filters.</div>';
            return;
        }
        
        list.innerHTML = filtered.map(item => {
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
            
            // Build flags
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
                        <div class="flow-detail">Total unusual flow</div>
                        ${maxVolOi > 0 ? `<div class="flow-ratio">Max Vol/OI: ${maxVolOi}x</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    renderSentiment(sentiment) {
        if (!sentiment) return;
        
        const bar = document.getElementById('sentiment-bar');
        const value = document.getElementById('sentiment-value');
        const indicatorsEl = document.getElementById('sentiment-indicators');
        
        bar.style.left = `${sentiment.value}%`;
        
        let html = `${sentiment.value} - ${sentiment.label}`;
        
        // Show source and VIX
        let subInfo = [];
        if (sentiment.source) {
            subInfo.push(`Source: ${sentiment.source}`);
        }
        if (sentiment.vix) {
            subInfo.push(`VIX: ${sentiment.vix}`);
        }
        if (subInfo.length > 0) {
            html += `<div class="sentiment-vix">${subInfo.join(' • ')}</div>`;
        }
        
        value.innerHTML = html;
        
        if (sentiment.value >= 55) {
            value.style.color = 'var(--accent-green)';
        } else if (sentiment.value <= 45) {
            value.style.color = 'var(--accent-red)';
        } else {
            value.style.color = 'var(--text-primary)';
        }
        
        // Clear indicators section (not needed when scraping real data)
        if (indicatorsEl) {
            indicatorsEl.innerHTML = '';
        }
    }
    
    renderMostActive(active) {
        const list = document.getElementById('active-list');
        
        if (!active || active.length === 0) {
            list.innerHTML = '<div class="loading-state small">No data</div>';
            return;
        }
        
        list.innerHTML = active.map(item => `
            <div class="active-item">
                <span class="active-ticker">${item.ticker}</span>
                <span class="active-volume">${this.formatNumber(item.volume)}</span>
            </div>
        `).join('');
    }
    
    renderMovers(movers) {
        if (!movers) return;
        
        const gainersList = document.getElementById('gainers-list');
        const losersList = document.getElementById('losers-list');
        
        if (movers.gainers && movers.gainers.length > 0) {
            gainersList.innerHTML = movers.gainers.map(item => `
                <div class="mover-item">
                    <span class="mover-ticker">${item.ticker}</span>
                    <span class="mover-change positive">+${item.change_pct.toFixed(2)}%</span>
                </div>
            `).join('');
        } else {
            gainersList.innerHTML = '<div class="loading-state small">No data</div>';
        }
        
        if (movers.losers && movers.losers.length > 0) {
            losersList.innerHTML = movers.losers.map(item => `
                <div class="mover-item">
                    <span class="mover-ticker">${item.ticker}</span>
                    <span class="mover-change negative">${item.change_pct.toFixed(2)}%</span>
                </div>
            `).join('');
        } else {
            losersList.innerHTML = '<div class="loading-state small">No data</div>';
        }
    }
    
    formatPremium(value) {
        // Handle null, undefined, NaN
        if (value == null || isNaN(value)) {
            return '$0';
        }
        if (value >= 1000000) {
            return '$' + (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return '$' + Math.round(value / 1000) + 'K';
        }
        return '$' + Math.round(value);
    }
    
    formatNumber(value) {
        // Handle null, undefined, NaN
        if (value == null || isNaN(value)) {
            return '0';
        }
        if (value >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (value >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        }
        return value.toString();
    }
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.newsFlow = new NewsFlowPage();
});
