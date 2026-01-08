// News & Flow Page JavaScript - Revamped

class NewsFlowPage {
    constructor() {
        this.currentFilter = 'all';
        this.flowData = [];
        this.marketData = null;
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
        
        document.getElementById('btn-refresh-market').addEventListener('click', () => {
            this.refreshMarket();
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
            this.refreshMarket(),
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
            const response = await fetch('/api/flow');
            const data = await response.json();
            
            this.flowData = data.unusual_flow || [];
            this.renderFlow();
            
            const time = new Date(data.timestamp).toLocaleTimeString();
            meta.textContent = `Updated: ${time} • ${this.flowData.length} tickers with unusual flow`;
            
            // Update market summary with flow data
            this.updateFlowSummary();
            
        } catch (error) {
            console.error('Flow error:', error);
            list.innerHTML = '<div class="loading-state">Failed to load flow data</div>';
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    async refreshMarket() {
        const btn = document.getElementById('btn-refresh-market');
        btn.classList.add('loading');
        
        try {
            const response = await fetch('/api/market');
            const data = await response.json();
            
            this.marketData = data;
            
            // Render all market sections
            this.renderSentiment(data.sentiment);
            this.renderIndices(data.indices);
            this.renderMostActive(data.most_active);
            this.renderMovers(data.movers);
            this.renderSectors(data.sectors);
            this.renderEvents(data.events);
            this.generateMarketSummary(data);
            
        } catch (error) {
            console.error('Market error:', error);
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    updateFlowSummary() {
        // Update just the flow part of market summary
        if (this.flowData.length > 0 && this.marketData) {
            this.generateMarketSummary(this.marketData);
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
    
    renderSentiment(sentiment) {
        if (!sentiment) return;
        
        const needle = document.getElementById('gauge-needle');
        const valueEl = document.getElementById('fg-value');
        const labelEl = document.getElementById('fg-label');
        const sourceEl = document.getElementById('fg-source');
        const histNow = document.getElementById('hist-now');
        
        const value = sentiment.value || 50;
        
        // Rotate needle: 0 = -90deg (left), 100 = 90deg (right)
        const rotation = (value / 100) * 180 - 90;
        needle.style.transform = `translateX(-50%) rotate(${rotation}deg)`;
        
        valueEl.textContent = value;
        labelEl.textContent = sentiment.label || 'Neutral';
        
        // Color based on sentiment
        if (value >= 55) {
            labelEl.style.color = 'var(--accent-green)';
        } else if (value <= 45) {
            labelEl.style.color = 'var(--accent-red)';
        } else {
            labelEl.style.color = 'var(--accent-yellow)';
        }
        
        if (sentiment.source) {
            sourceEl.textContent = `Source: ${sentiment.source}${sentiment.vix ? ' • VIX: ' + sentiment.vix : ''}`;
        }
        
        // Update history (simulated - in production you'd track this)
        histNow.textContent = value;
        histNow.className = 'history-value ' + this.getSentimentClass(value);
        
        // Simulated history values (would be stored/fetched in production)
        document.getElementById('hist-yesterday').textContent = '--';
        document.getElementById('hist-week').textContent = '--';
        document.getElementById('hist-month').textContent = '--';
        
        // Sentiment change text
        const changeEl = document.getElementById('sentiment-change');
        changeEl.innerHTML = `<span style="color: var(--text-muted)">Historical data requires tracking over time</span>`;
    }
    
    getSentimentClass(value) {
        if (value >= 55) return 'greed';
        if (value <= 45) return 'fear';
        return 'neutral';
    }
    
    renderIndices(indices) {
        if (!indices) return;
        
        const indexMap = {
            'spy': 'index-spy',
            'dow': 'index-dow',
            'nasdaq': 'index-nasdaq',
            'vix': 'index-vix',
        };
        
        for (const [key, elementId] of Object.entries(indexMap)) {
            const data = indices[key];
            const el = document.getElementById(elementId);
            
            if (data && el) {
                el.querySelector('.index-price').textContent = '$' + this.formatNumber(data.price);
                
                const changeEl = el.querySelector('.index-change');
                const isPositive = data.change_pct >= 0;
                changeEl.textContent = (isPositive ? '+' : '') + data.change_pct.toFixed(2) + '%';
                changeEl.className = 'index-change ' + (isPositive ? 'positive' : 'negative');
            }
        }
    }
    
    renderMostActive(active) {
        const list = document.getElementById('active-list');
        
        if (!active || active.length === 0) {
            list.innerHTML = '<div class="loading-state small">No data</div>';
            return;
        }
        
        list.innerHTML = active.slice(0, 6).map(item => `
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
            gainersList.innerHTML = movers.gainers.slice(0, 5).map(item => `
                <div class="mover-item">
                    <span class="mover-ticker">${item.ticker}</span>
                    <span class="mover-change positive">+${item.change_pct.toFixed(2)}%</span>
                </div>
            `).join('');
        } else {
            gainersList.innerHTML = '<div class="loading-state small">No data</div>';
        }
        
        if (movers.losers && movers.losers.length > 0) {
            losersList.innerHTML = movers.losers.slice(0, 5).map(item => `
                <div class="mover-item">
                    <span class="mover-ticker">${item.ticker}</span>
                    <span class="mover-change negative">${item.change_pct.toFixed(2)}%</span>
                </div>
            `).join('');
        } else {
            losersList.innerHTML = '<div class="loading-state small">No data</div>';
        }
    }
    
    renderSectors(sectors) {
        const list = document.getElementById('sector-list');
        
        if (!sectors || sectors.length === 0) {
            list.innerHTML = '<div class="loading-state small">No data</div>';
            return;
        }
        
        list.innerHTML = sectors.slice(0, 8).map(item => {
            const isPositive = item.change_pct >= 0;
            return `
                <div class="sector-item">
                    <span class="sector-name">${item.name}</span>
                    <span class="sector-change ${isPositive ? 'positive' : 'negative'}">
                        ${isPositive ? '+' : ''}${item.change_pct.toFixed(2)}%
                    </span>
                </div>
            `;
        }).join('');
    }
    
    renderEvents(events) {
        const list = document.getElementById('events-list');
        
        if (!events || events.length === 0) {
            list.innerHTML = '<div class="loading-state small">No upcoming events</div>';
            return;
        }
        
        list.innerHTML = events.slice(0, 5).map(item => {
            const date = new Date(item.date);
            const dateStr = date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
            
            return `
                <div class="event-item">
                    <span class="event-date">📅 ${dateStr}</span>
                    <span class="event-name">${item.name}</span>
                </div>
            `;
        }).join('');
    }
    
    generateMarketSummary(data) {
        const summaryEl = document.getElementById('market-summary');
        
        const sentiment = data.sentiment || {};
        const indices = data.indices || {};
        const spy = indices.spy || {};
        
        let summary = '';
        
        // Sentiment summary
        const fgValue = sentiment.value || 50;
        const fgLabel = sentiment.label || 'Neutral';
        
        if (fgValue >= 75) {
            summary += `<p>Market sentiment is at <span class="summary-highlight">Extreme Greed (${fgValue})</span>. Caution advised - markets may be overbought.</p>`;
        } else if (fgValue >= 55) {
            summary += `<p>Market sentiment shows <span class="summary-highlight">Greed (${fgValue})</span>. Bullish conditions but watch for reversals.</p>`;
        } else if (fgValue <= 25) {
            summary += `<p>Market sentiment at <span class="summary-highlight">Extreme Fear (${fgValue})</span>. Potential buying opportunity for contrarians.</p>`;
        } else if (fgValue <= 45) {
            summary += `<p>Market sentiment shows <span class="summary-highlight">Fear (${fgValue})</span>. Markets are cautious.</p>`;
        } else {
            summary += `<p>Market sentiment is <span class="summary-highlight">Neutral (${fgValue})</span>. No strong directional bias.</p>`;
        }
        
        // Market direction
        if (spy.change_pct !== undefined) {
            const direction = spy.change_pct >= 0 ? 'up' : 'down';
            const color = spy.change_pct >= 0 ? 'var(--accent-green)' : 'var(--accent-red)';
            summary += `<p>S&P 500 is <span style="color: ${color}">${direction} ${Math.abs(spy.change_pct).toFixed(2)}%</span> today.</p>`;
        }
        
        // Flow summary
        if (this.flowData.length > 0) {
            const bullishCount = this.flowData.filter(f => f.sentiment && f.sentiment.includes('bullish')).length;
            const bearishCount = this.flowData.filter(f => f.sentiment && f.sentiment.includes('bearish')).length;
            
            if (bullishCount > bearishCount * 1.5) {
                summary += `<p>Options flow is <span style="color: var(--accent-green)">bullish</span> (${bullishCount} bullish vs ${bearishCount} bearish tickers).</p>`;
            } else if (bearishCount > bullishCount * 1.5) {
                summary += `<p>Options flow is <span style="color: var(--accent-red)">bearish</span> (${bearishCount} bearish vs ${bullishCount} bullish tickers).</p>`;
            } else {
                summary += `<p>Options flow is <span style="color: var(--accent-yellow)">mixed</span> (${bullishCount} bullish, ${bearishCount} bearish).</p>`;
            }
        }
        
        summaryEl.innerHTML = summary || 'Click refresh to load market data...';
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
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.newsFlow = new NewsFlowPage();
});
