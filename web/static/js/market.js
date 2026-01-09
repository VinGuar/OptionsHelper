// Current Market Page JavaScript

class MarketPage {
    constructor() {
        this.marketData = null;
        this.CACHE_KEY_MARKET = 'options_market_cache';
        this.init();
    }
    
    init() {
        this.bindEvents();
        // Load cached data only - no auto-refresh
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
        const cached = this.getCache(this.CACHE_KEY_MARKET);
        if (cached && cached.data && cached.timestamp) {
            this.marketData = cached.data;
            
            // Render all cached market sections
            this.renderSentiment(cached.data.sentiment);
            this.renderIndices(cached.data.indices);
            this.renderMostActive(cached.data.most_active);
            this.renderMovers(cached.data.movers);
            this.renderSectors(cached.data.sectors);
            this.renderEvents(cached.data.events);
            this.generateMarketSummary(cached.data);
            
            // Update all timestamps with cached timestamp
            this.updateTimestamp('sentiment-timestamp', cached.timestamp);
            this.updateTimestamp('sentiment-history-timestamp', cached.timestamp);
            this.updateTimestamp('market-summary-timestamp', cached.timestamp);
            this.updateTimestamp('gainers-timestamp', cached.timestamp);
            this.updateTimestamp('losers-timestamp', cached.timestamp);
            this.updateTimestamp('active-timestamp', cached.timestamp);
            this.updateTimestamp('sector-timestamp', cached.timestamp);
            this.updateTimestamp('events-timestamp', cached.timestamp);
        }
    }
    
    bindEvents() {
        // Refresh all button
        document.getElementById('btn-refresh-all').addEventListener('click', () => {
            this.refreshMarket();
        });
        
        // Individual refresh buttons
        document.getElementById('btn-refresh-market').addEventListener('click', () => {
            this.refreshMarket();
        });
        
        // Section-specific refresh buttons
        document.getElementById('btn-refresh-gainers').addEventListener('click', () => {
            this.refreshMovers();
        });
        
        document.getElementById('btn-refresh-losers').addEventListener('click', () => {
            this.refreshMovers();
        });
        
        document.getElementById('btn-refresh-active').addEventListener('click', () => {
            this.refreshMostActive();
        });
        
        document.getElementById('btn-refresh-sectors').addEventListener('click', () => {
            this.refreshSectors();
        });
        
        document.getElementById('btn-refresh-events').addEventListener('click', () => {
            this.refreshEvents();
        });
    }
    
    async refreshMarket() {
        const btn = document.getElementById('btn-refresh-market');
        const btnAll = document.getElementById('btn-refresh-all');
        
        btn.classList.add('loading');
        btnAll.classList.add('loading');
        btnAll.disabled = true;
        
        try {
            const response = await fetch(getApiUrl('/api/market'));
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
            
            // Save to cache
            this.saveToCache(this.CACHE_KEY_MARKET, data, data.timestamp);
            
            // Update all timestamps
            this.updateTimestamp('sentiment-timestamp', data.timestamp);
            this.updateTimestamp('sentiment-history-timestamp', data.timestamp);
            this.updateTimestamp('market-summary-timestamp', data.timestamp);
            this.updateTimestamp('gainers-timestamp', data.timestamp);
            this.updateTimestamp('losers-timestamp', data.timestamp);
            this.updateTimestamp('active-timestamp', data.timestamp);
            this.updateTimestamp('sector-timestamp', data.timestamp);
            this.updateTimestamp('events-timestamp', data.timestamp);
            
        } catch (error) {
            console.error('Market error:', error);
        } finally {
            btn.classList.remove('loading');
            btnAll.classList.remove('loading');
            btnAll.disabled = false;
        }
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
        
        list.innerHTML = active.slice(0, 10).map(item => `
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
            gainersList.innerHTML = movers.gainers.slice(0, 10).map(item => `
                <div class="mover-item">
                    <span class="mover-ticker">${item.ticker}</span>
                    <span class="mover-change positive">+${item.change_pct.toFixed(2)}%</span>
                </div>
            `).join('');
        } else {
            gainersList.innerHTML = '<div class="loading-state small">No data</div>';
        }
        
        if (movers.losers && movers.losers.length > 0) {
            losersList.innerHTML = movers.losers.slice(0, 10).map(item => `
                <div class="mover-item">
                    <span class="mover-ticker">${item.ticker}</span>
                    <span class="mover-change negative">${item.change_pct.toFixed(2)}%</span>
                </div>
            `).join('');
        } else {
            losersList.innerHTML = '<div class="loading-state small">No data</div>';
        }
    }
    
    async refreshMovers() {
        const btnGainers = document.getElementById('btn-refresh-gainers');
        const btnLosers = document.getElementById('btn-refresh-losers');
        
        btnGainers.classList.add('loading');
        btnLosers.classList.add('loading');
        
        try {
            const response = await fetch(getApiUrl('/api/market'));
            const data = await response.json();
            
            this.renderMovers(data.movers);
            const timestamp = data.timestamp || new Date().toISOString();
            this.updateTimestamp('gainers-timestamp', timestamp);
            this.updateTimestamp('losers-timestamp', timestamp);
            
            // Update cache if we have full market data
            if (this.marketData) {
                this.marketData.movers = data.movers;
                this.saveToCache(this.CACHE_KEY_MARKET, this.marketData, timestamp);
            }
        } catch (error) {
            console.error('Error refreshing movers:', error);
        } finally {
            btnGainers.classList.remove('loading');
            btnLosers.classList.remove('loading');
        }
    }
    
    async refreshMostActive() {
        const btn = document.getElementById('btn-refresh-active');
        btn.classList.add('loading');
        
        try {
            const response = await fetch(getApiUrl('/api/market'));
            const data = await response.json();
            
            this.renderMostActive(data.most_active);
            const timestamp = data.timestamp || new Date().toISOString();
            this.updateTimestamp('active-timestamp', timestamp);
            
            // Update cache if we have full market data
            if (this.marketData) {
                this.marketData.most_active = data.most_active;
                this.saveToCache(this.CACHE_KEY_MARKET, this.marketData, timestamp);
            }
        } catch (error) {
            console.error('Error refreshing most active:', error);
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    async refreshSectors() {
        const btn = document.getElementById('btn-refresh-sectors');
        btn.classList.add('loading');
        
        try {
            const response = await fetch(getApiUrl('/api/market'));
            const data = await response.json();
            
            this.renderSectors(data.sectors);
            const timestamp = data.timestamp || new Date().toISOString();
            this.updateTimestamp('sector-timestamp', timestamp);
            
            // Update cache if we have full market data
            if (this.marketData) {
                this.marketData.sectors = data.sectors;
                this.saveToCache(this.CACHE_KEY_MARKET, this.marketData, timestamp);
            }
        } catch (error) {
            console.error('Error refreshing sectors:', error);
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    async refreshEvents() {
        const btn = document.getElementById('btn-refresh-events');
        btn.classList.add('loading');
        
        try {
            const response = await fetch(getApiUrl('/api/market'));
            const data = await response.json();
            
            this.renderEvents(data.events);
            const timestamp = data.timestamp || new Date().toISOString();
            this.updateTimestamp('events-timestamp', timestamp);
            
            // Update cache if we have full market data
            if (this.marketData) {
                this.marketData.events = data.events;
                this.saveToCache(this.CACHE_KEY_MARKET, this.marketData, timestamp);
            }
        } catch (error) {
            console.error('Error refreshing events:', error);
        } finally {
            btn.classList.remove('loading');
        }
    }
    
    renderSectors(sectors) {
        const list = document.getElementById('sector-list');
        
        if (!sectors || sectors.length === 0) {
            list.innerHTML = '<div class="loading-state small">No data</div>';
            return;
        }
        
        list.innerHTML = sectors.slice(0, 12).map(item => {
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
        
        list.innerHTML = events.slice(0, 8).map(item => {
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
        
        // Sector performance summary
        const sectors = data.sectors || [];
        if (sectors.length > 0) {
            const topSector = sectors[0];
            const worstSector = sectors[sectors.length - 1];
            if (topSector && worstSector) {
                summary += `<p>Leading sector: <span style="color: var(--accent-green)">${topSector.name} (+${topSector.change_pct.toFixed(2)}%)</span>. Lagging: <span style="color: var(--accent-red)">${worstSector.name} (${worstSector.change_pct.toFixed(2)}%)</span>.</p>`;
            }
        }
        
        summaryEl.innerHTML = summary || 'Click refresh to load market data...';
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
    window.marketPage = new MarketPage();
});

