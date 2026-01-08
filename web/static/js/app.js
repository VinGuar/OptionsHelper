// Options Edge Scanner - Frontend Application

class OptionsScanner {
    constructor() {
        this.selectedStrategy = '1';
        this.scanType = 'quick';
        this.results = null;
        this.selectedCandidate = null;
        this.pollInterval = null;
        this.strategiesData = [];
        this.CACHE_KEY = 'options_scanner_cache';
        
        this.init();
    }
    
    async init() {
        await this.loadStrategies();
        this.bindEvents();
        // Load cached results for initial strategy
        this.loadCachedResults(this.selectedStrategy);
    }
    
    // LocalStorage cache methods
    getCache() {
        try {
            const cache = localStorage.getItem(this.CACHE_KEY);
            return cache ? JSON.parse(cache) : {};
        } catch (e) {
            return {};
        }
    }
    
    saveToCache(strategyKey, results) {
        try {
            const cache = this.getCache();
            cache[strategyKey] = {
                results: results,
                timestamp: new Date().toISOString()
            };
            localStorage.setItem(this.CACHE_KEY, JSON.stringify(cache));
        } catch (e) {
            console.error('Failed to save to cache:', e);
        }
    }
    
    loadCachedResults(strategyKey) {
        const cache = this.getCache();
        const cached = cache[strategyKey];
        
        if (cached && cached.results) {
            this.results = cached.results;
            this.renderResults(cached.results, cached.timestamp);
            this.setStatus('Ready', false);
            document.getElementById('btn-export').disabled = false;
            
            // Select first passed candidate
            const firstPassed = cached.results.candidates?.find(c => c.passed);
            if (firstPassed) {
                this.selectCandidate(firstPassed.ticker);
            }
        } else {
            // No cached results - show empty state
            this.showEmptyState(strategyKey);
        }
    }
    
    showEmptyState(strategyKey) {
        this.results = null;
        document.getElementById('empty-state').style.display = 'flex';
        document.getElementById('results-table').style.display = 'none';
        document.getElementById('results-meta').innerHTML = '';
        document.getElementById('results-timestamp').innerHTML = '';
        document.getElementById('details-content').innerHTML = `
            <div class="empty-details">
                Click a candidate to view details
            </div>
        `;
        document.getElementById('btn-export').disabled = true;
    }
    
    async loadStrategies() {
        try {
            const response = await fetch('/api/strategies');
            const strategies = await response.json();
            this.strategiesData = strategies;
            this.renderStrategies(strategies);
        } catch (error) {
            console.error('Failed to load strategies:', error);
        }
    }
    
    renderStrategies(strategies) {
        const container = document.getElementById('strategies-list');
        container.innerHTML = strategies.map(s => `
            <div class="strategy-card ${s.key === this.selectedStrategy ? 'selected' : ''}" 
                 data-key="${s.key}">
                <div class="strategy-name">
                    <span class="num">${s.key}</span>
                    ${s.name}
                </div>
                <div class="strategy-desc">${s.description}</div>
                <div class="strategy-meta">
                    <span class="win-rate">${Math.round(s.expected_win_rate * 100)}% win</span>
                    <span class="risk-${s.risk_level.includes('high') ? 'high' : 'medium'}">
                        ${s.risk_level.toUpperCase()}
                    </span>
                    <span>${s.typical_hold_days}D hold</span>
                </div>
            </div>
        `).join('');
    }
    
    bindEvents() {
        // Strategy selection
        document.getElementById('strategies-list').addEventListener('click', (e) => {
            const card = e.target.closest('.strategy-card');
            if (card) {
                this.selectStrategy(card.dataset.key);
            }
        });
        
        // Scan type selection
        document.querySelectorAll('input[name="scan-type"]').forEach(radio => {
            radio.addEventListener('change', (e) => {
                this.scanType = e.target.value;
            });
        });
        
        // Scan button
        document.getElementById('btn-scan').addEventListener('click', () => {
            this.startScan();
        });
        
        // Results row click
        document.getElementById('results-body').addEventListener('click', (e) => {
            const row = e.target.closest('tr');
            if (row && row.dataset.ticker) {
                this.selectCandidate(row.dataset.ticker);
            }
        });
        
        // Help modal
        document.getElementById('btn-help').addEventListener('click', () => {
            document.getElementById('help-modal').style.display = 'flex';
        });
        
        document.getElementById('help-modal-close').addEventListener('click', () => {
            document.getElementById('help-modal').style.display = 'none';
        });
        
        document.getElementById('help-modal').addEventListener('click', (e) => {
            if (e.target.id === 'help-modal') {
                document.getElementById('help-modal').style.display = 'none';
            }
        });
        
        // Export button
        document.getElementById('btn-export').addEventListener('click', () => {
            this.exportResults();
        });
    }
    
    selectStrategy(key) {
        this.selectedStrategy = key;
        document.querySelectorAll('.strategy-card').forEach(card => {
            card.classList.toggle('selected', card.dataset.key === key);
        });
        
        // Load cached results for this strategy
        this.loadCachedResults(key);
    }
    
    async startScan() {
        const btn = document.getElementById('btn-scan');
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-icon">◌</span><span>SCANNING...</span>';
        
        // Disable export during scan
        document.getElementById('btn-export').disabled = true;
        
        // Update status
        this.setStatus('Scanning...', true);
        
        // Show progress
        const progressContainer = document.getElementById('progress-container');
        progressContainer.style.display = 'block';
        
        // Hide empty state, show table
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('results-table').style.display = 'table';
        document.getElementById('results-body').innerHTML = '';
        
        try {
            const response = await fetch('/api/scan/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    strategy: this.selectedStrategy,
                    type: this.scanType
                })
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Scan failed');
            }
            
            // Start polling for progress
            this.pollProgress();
            
        } catch (error) {
            console.error('Scan error:', error);
            this.setStatus('Error: ' + error.message, false);
            btn.disabled = false;
            btn.innerHTML = '<span class="btn-icon">▶</span><span>RUN SCAN</span>';
            progressContainer.style.display = 'none';
        }
    }
    
    async pollProgress() {
        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/scan/status');
                const status = await response.json();
                
                // Update progress bar
                const pct = status.total > 0 ? (status.progress / status.total * 100) : 0;
                document.getElementById('progress-fill').style.width = `${pct}%`;
                document.getElementById('progress-text').textContent = 
                    `Scanning ${status.current_ticker}... (${status.progress}/${status.total})`;
                
                // Check if done
                if (!status.running) {
                    clearInterval(this.pollInterval);
                    
                    if (status.error) {
                        this.setStatus('Error: ' + status.error, false);
                    } else if (status.has_results) {
                        await this.loadResults();
                    }
                    
                    // Reset button
                    const btn = document.getElementById('btn-scan');
                    btn.disabled = false;
                    btn.innerHTML = '<span class="btn-icon">▶</span><span>RUN SCAN</span>';
                    
                    // Hide progress
                    document.getElementById('progress-container').style.display = 'none';
                    
                    // Enable export if we have results
                    if (status.has_results) {
                        document.getElementById('btn-export').disabled = false;
                    }
                }
                
            } catch (error) {
                console.error('Poll error:', error);
            }
        }, 500);
    }
    
    async loadResults() {
        try {
            const response = await fetch('/api/scan/results');
            const data = await response.json();
            this.results = data;
            
            // Save to cache
            this.saveToCache(this.selectedStrategy, data);
            
            // Render with current timestamp
            this.renderResults(data, new Date().toISOString());
            this.setStatus('Ready', false);
        } catch (error) {
            console.error('Failed to load results:', error);
        }
    }
    
    renderResults(data, timestamp) {
        // Show table, hide empty state
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('results-table').style.display = 'table';
        
        // Update meta
        document.getElementById('results-meta').innerHTML = `
            <span class="count">${data.passed_count}</span> / ${data.total_count} passed
            &nbsp;|&nbsp; ${data.strategy.name}
        `;
        
        // Update timestamp
        const timestampEl = document.getElementById('results-timestamp');
        if (timestamp) {
            const date = new Date(timestamp);
            const timeStr = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            const dateStr = date.toLocaleDateString([], { month: 'short', day: 'numeric' });
            timestampEl.innerHTML = `<span class="timestamp-icon">🕐</span> Scanned: ${dateStr} at ${timeStr}`;
        } else {
            timestampEl.innerHTML = '';
        }
        
        // Render table
        const tbody = document.getElementById('results-body');
        tbody.innerHTML = data.candidates.map(c => {
            const dirClass = c.direction === 'BULLISH' ? 'bullish' : 
                            c.direction === 'BEARISH' ? 'bearish' : 'neutral';
            const dirIcon = c.direction === 'BULLISH' ? '▲' : 
                           c.direction === 'BEARISH' ? '▼' : '◆';
            const ret20d = c.return_20d || 0;
            const retClass = ret20d >= 0 ? 'positive' : 'negative';
            
            return `
                <tr data-ticker="${c.ticker}" class="${c.passed ? '' : 'failed'}">
                    <td class="ticker">${c.ticker}</td>
                    <td>
                        <span class="direction ${dirClass}">
                            ${dirIcon} ${c.direction || 'N/A'}
                        </span>
                    </td>
                    <td>${c.trade_type || '-'}</td>
                    <td class="strength">${c.signal_strength.toFixed(0)}%</td>
                    <td>$${(c.price || 0).toFixed(2)}</td>
                    <td class="${retClass}">${ret20d >= 0 ? '+' : ''}${ret20d.toFixed(1)}%</td>
                    <td>${c.iv_rank ? c.iv_rank.toFixed(0) : '-'}</td>
                </tr>
            `;
        }).join('');
        
        // Select first passed candidate
        const firstPassed = data.candidates.find(c => c.passed);
        if (firstPassed) {
            this.selectCandidate(firstPassed.ticker);
        }
    }
    
    selectCandidate(ticker) {
        this.selectedCandidate = ticker;
        
        // Update table selection
        document.querySelectorAll('#results-body tr').forEach(row => {
            row.classList.toggle('selected', row.dataset.ticker === ticker);
        });
        
        // Find candidate data
        const candidate = this.results?.candidates.find(c => c.ticker === ticker);
        if (!candidate) return;
        
        // Render details
        this.renderDetails(candidate);
    }
    
    renderDetails(c) {
        const dirClass = c.direction === 'BULLISH' ? 'bullish' : 
                        c.direction === 'BEARISH' ? 'bearish' : 'neutral';
        
        const structure = this.results?.structure || {};
        const exits = this.results?.exits || {};
        
        // Generate action steps based on trade type
        const actionSteps = this.getActionSteps(c, structure);
        
        document.getElementById('details-content').innerHTML = `
            <div class="detail-section">
                <div class="detail-ticker">${c.ticker}</div>
                <span class="detail-direction ${dirClass}">${c.direction || 'NEUTRAL'}</span>
            </div>
            
            <div class="detail-section action-box">
                <h3>🎯 WHAT TO DO</h3>
                <div class="action-steps">
                    ${actionSteps}
                </div>
            </div>
            
            <div class="detail-section">
                <h3>SIGNAL</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="label">TRADE TYPE</div>
                        <div class="value">${c.trade_type || '-'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">STRENGTH</div>
                        <div class="value" style="color: var(--accent-cyan)">${c.signal_strength.toFixed(0)}%</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3>MARKET DATA</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="label">PRICE</div>
                        <div class="value">$${(c.price || 0).toFixed(2)}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">20D RETURN</div>
                        <div class="value" style="color: ${(c.return_20d || 0) >= 0 ? 'var(--accent-green)' : 'var(--accent-red)'}">
                            ${(c.return_20d || 0) >= 0 ? '+' : ''}${(c.return_20d || 0).toFixed(1)}%
                        </div>
                    </div>
                    <div class="detail-item">
                        <div class="label">IV RANK</div>
                        <div class="value">${c.iv_rank ? c.iv_rank.toFixed(0) : 'N/A'}</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">RSI</div>
                        <div class="value">${c.rsi ? c.rsi.toFixed(0) : 'N/A'}</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3>RECOMMENDED STRUCTURE</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="label">DTE</div>
                        <div class="value">${structure.dte_min || 30}-${structure.dte_max || 45} days</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">LONG DELTA</div>
                        <div class="value">~${structure.long_delta || structure.target_delta || 0.35}</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3>EXIT RULES</h3>
                <div class="detail-grid">
                    <div class="detail-item">
                        <div class="label">TAKE PROFIT</div>
                        <div class="value" style="color: var(--accent-green)">${((exits.take_profit_pct || 0.5) * 100).toFixed(0)}%</div>
                    </div>
                    <div class="detail-item">
                        <div class="label">STOP LOSS</div>
                        <div class="value" style="color: var(--accent-red)">${((exits.stop_loss_pct || 0.5) * 100).toFixed(0)}%</div>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h3>WHY THIS PASSED</h3>
                <ul class="reasons-list">
                    ${c.reasons.map(r => `<li>${r}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    
    getActionSteps(c, structure) {
        const price = c.price || 100;
        const dte = `${structure.dte_min || 30}-${structure.dte_max || 45}`;
        const strategyName = this.results?.strategy?.name || 'Unknown Strategy';
        
        let steps = '';
        let explanation = '';
        
        if (c.trade_type === 'CALL_DEBIT') {
            const buyStrike = Math.round(price * 1.00);
            const sellStrike = Math.round(price * 1.05);
            steps = `
                <div class="action-step buy">
                    <span class="step-num">1</span>
                    <span class="step-action">BUY</span>
                    <span class="step-detail">${c.ticker} $${buyStrike} Call</span>
                </div>
                <div class="action-step sell">
                    <span class="step-num">2</span>
                    <span class="step-action">SELL</span>
                    <span class="step-detail">${c.ticker} $${sellStrike} Call</span>
                </div>
                <div class="action-note">
                    Expiration: ${dte} days out<br>
                    This is a DEBIT spread - you pay upfront<br>
                    Max loss = what you pay
                </div>
            `;
            explanation = `
                <h4>Why a CALL DEBIT SPREAD?</h4>
                <p><strong>Strategy:</strong> ${strategyName}</p>
                <p><strong>Direction:</strong> BULLISH - We expect ${c.ticker} to go UP</p>
                
                <div class="explain-section">
                    <strong>What is this trade?</strong>
                    <p>A call debit spread (also called a "bull call spread") involves buying a call option at a lower strike and selling a call at a higher strike. You pay a "debit" (cost) upfront.</p>
                </div>
                
                <div class="explain-section">
                    <strong>Why this structure for ${strategyName}?</strong>
                    <ul>
                        <li><strong>Defined Risk:</strong> Your max loss is capped at what you pay - you can't lose more</li>
                        <li><strong>Cheaper than buying calls:</strong> Selling the higher strike reduces your cost</li>
                        <li><strong>Less affected by IV crush:</strong> The short leg offsets some volatility risk</li>
                        <li><strong>Trend capture:</strong> Profits if stock moves up, even moderately</li>
                    </ul>
                </div>
                
                <div class="explain-section">
                    <strong>How to execute in your broker:</strong>
                    <ol>
                        <li>Search for ${c.ticker} options</li>
                        <li>Select expiration ${dte} days out</li>
                        <li>Find the $${buyStrike} Call - click BUY</li>
                        <li>Find the $${sellStrike} Call - click SELL</li>
                        <li>Or use "Spread" order type and select "Call Debit Spread"</li>
                        <li>Set limit price at the mid-price shown</li>
                        <li>Submit order</li>
                    </ol>
                </div>
                
                <div class="explain-section">
                    <strong>Profit/Loss:</strong>
                    <ul>
                        <li><strong>Max Profit:</strong> $${sellStrike - buyStrike} per share (spread width) minus what you paid</li>
                        <li><strong>Max Loss:</strong> What you paid (the debit)</li>
                        <li><strong>Breakeven:</strong> $${buyStrike} + debit paid</li>
                        <li><strong>Best case:</strong> Stock closes above $${sellStrike} at expiration</li>
                    </ul>
                </div>
            `;
        } else if (c.trade_type === 'PUT_DEBIT') {
            const buyStrike = Math.round(price * 1.00);
            const sellStrike = Math.round(price * 0.95);
            steps = `
                <div class="action-step buy">
                    <span class="step-num">1</span>
                    <span class="step-action">BUY</span>
                    <span class="step-detail">${c.ticker} $${buyStrike} Put</span>
                </div>
                <div class="action-step sell">
                    <span class="step-num">2</span>
                    <span class="step-action">SELL</span>
                    <span class="step-detail">${c.ticker} $${sellStrike} Put</span>
                </div>
                <div class="action-note">
                    Expiration: ${dte} days out<br>
                    This is a DEBIT spread - you pay upfront<br>
                    Max loss = what you pay
                </div>
            `;
            explanation = `
                <h4>Why a PUT DEBIT SPREAD?</h4>
                <p><strong>Strategy:</strong> ${strategyName}</p>
                <p><strong>Direction:</strong> BEARISH - We expect ${c.ticker} to go DOWN</p>
                
                <div class="explain-section">
                    <strong>What is this trade?</strong>
                    <p>A put debit spread (also called a "bear put spread") involves buying a put option at a higher strike and selling a put at a lower strike. You pay a "debit" (cost) upfront.</p>
                </div>
                
                <div class="explain-section">
                    <strong>Why this structure for ${strategyName}?</strong>
                    <ul>
                        <li><strong>Defined Risk:</strong> Your max loss is capped at what you pay</li>
                        <li><strong>Cheaper than buying puts:</strong> Selling the lower strike reduces your cost</li>
                        <li><strong>Bearish bet with protection:</strong> Profits if stock drops</li>
                        <li><strong>Less affected by IV crush:</strong> The short leg offsets volatility risk</li>
                    </ul>
                </div>
                
                <div class="explain-section">
                    <strong>How to execute in your broker:</strong>
                    <ol>
                        <li>Search for ${c.ticker} options</li>
                        <li>Select expiration ${dte} days out</li>
                        <li>Find the $${buyStrike} Put - click BUY</li>
                        <li>Find the $${sellStrike} Put - click SELL</li>
                        <li>Or use "Spread" order type and select "Put Debit Spread"</li>
                        <li>Set limit price at the mid-price shown</li>
                        <li>Submit order</li>
                    </ol>
                </div>
                
                <div class="explain-section">
                    <strong>Profit/Loss:</strong>
                    <ul>
                        <li><strong>Max Profit:</strong> $${buyStrike - sellStrike} per share (spread width) minus what you paid</li>
                        <li><strong>Max Loss:</strong> What you paid (the debit)</li>
                        <li><strong>Breakeven:</strong> $${buyStrike} - debit paid</li>
                        <li><strong>Best case:</strong> Stock closes below $${sellStrike} at expiration</li>
                    </ul>
                </div>
            `;
        } else if (c.trade_type === 'CALL_CREDIT') {
            const sellStrike = Math.round(price * 1.05);
            const buyStrike = Math.round(price * 1.10);
            steps = `
                <div class="action-step sell">
                    <span class="step-num">1</span>
                    <span class="step-action">SELL</span>
                    <span class="step-detail">${c.ticker} $${sellStrike} Call</span>
                </div>
                <div class="action-step buy">
                    <span class="step-num">2</span>
                    <span class="step-action">BUY</span>
                    <span class="step-detail">${c.ticker} $${buyStrike} Call</span>
                </div>
                <div class="action-note">
                    Expiration: ${dte} days out<br>
                    This is a CREDIT spread - you collect premium<br>
                    Max profit = credit received
                </div>
            `;
            explanation = `
                <h4>Why a CALL CREDIT SPREAD?</h4>
                <p><strong>Strategy:</strong> ${strategyName}</p>
                <p><strong>Direction:</strong> NEUTRAL to BEARISH - We expect ${c.ticker} to stay flat or go down</p>
                
                <div class="explain-section">
                    <strong>What is this trade?</strong>
                    <p>A call credit spread (also called a "bear call spread") involves SELLING a call at a lower strike and BUYING a call at a higher strike. You COLLECT premium upfront (a "credit").</p>
                </div>
                
                <div class="explain-section">
                    <strong>Why this structure for ${strategyName}?</strong>
                    <ul>
                        <li><strong>IV Crush play:</strong> When IV is high, options are expensive - we sell them</li>
                        <li><strong>Time decay works FOR you:</strong> Every day, the options lose value (theta decay)</li>
                        <li><strong>Profit from doing nothing:</strong> If stock stays below $${sellStrike}, you keep the credit</li>
                        <li><strong>Defined risk:</strong> The long call protects you from unlimited loss</li>
                    </ul>
                </div>
                
                <div class="explain-section">
                    <strong>How to execute in your broker:</strong>
                    <ol>
                        <li>Search for ${c.ticker} options</li>
                        <li>Select expiration ${dte} days out</li>
                        <li>Find the $${sellStrike} Call - click SELL</li>
                        <li>Find the $${buyStrike} Call - click BUY</li>
                        <li>Or use "Spread" order type and select "Call Credit Spread"</li>
                        <li>Set limit price at the mid-price shown (you receive this)</li>
                        <li>Submit order</li>
                    </ol>
                </div>
                
                <div class="explain-section">
                    <strong>Profit/Loss:</strong>
                    <ul>
                        <li><strong>Max Profit:</strong> The credit you receive upfront</li>
                        <li><strong>Max Loss:</strong> $${buyStrike - sellStrike} per share minus credit received</li>
                        <li><strong>Breakeven:</strong> $${sellStrike} + credit received</li>
                        <li><strong>Best case:</strong> Stock closes below $${sellStrike} at expiration (keep all credit)</li>
                    </ul>
                </div>
            `;
        } else if (c.trade_type === 'PUT_CREDIT') {
            const sellStrike = Math.round(price * 0.95);
            const buyStrike = Math.round(price * 0.90);
            steps = `
                <div class="action-step sell">
                    <span class="step-num">1</span>
                    <span class="step-action">SELL</span>
                    <span class="step-detail">${c.ticker} $${sellStrike} Put</span>
                </div>
                <div class="action-step buy">
                    <span class="step-num">2</span>
                    <span class="step-action">BUY</span>
                    <span class="step-detail">${c.ticker} $${buyStrike} Put</span>
                </div>
                <div class="action-note">
                    Expiration: ${dte} days out<br>
                    This is a CREDIT spread - you collect premium<br>
                    Max profit = credit received
                </div>
            `;
            explanation = `
                <h4>Why a PUT CREDIT SPREAD?</h4>
                <p><strong>Strategy:</strong> ${strategyName}</p>
                <p><strong>Direction:</strong> NEUTRAL to BULLISH - We expect ${c.ticker} to stay flat or go up</p>
                
                <div class="explain-section">
                    <strong>What is this trade?</strong>
                    <p>A put credit spread (also called a "bull put spread") involves SELLING a put at a higher strike and BUYING a put at a lower strike. You COLLECT premium upfront (a "credit").</p>
                </div>
                
                <div class="explain-section">
                    <strong>Why this structure for ${strategyName}?</strong>
                    <ul>
                        <li><strong>IV Crush play:</strong> When IV is high after a drop, puts are expensive - we sell them</li>
                        <li><strong>Mean reversion:</strong> Stock dropped, we bet it won't drop much more</li>
                        <li><strong>Time decay works FOR you:</strong> Every day, the options lose value</li>
                        <li><strong>Defined risk:</strong> The long put protects you from big losses</li>
                    </ul>
                </div>
                
                <div class="explain-section">
                    <strong>How to execute in your broker:</strong>
                    <ol>
                        <li>Search for ${c.ticker} options</li>
                        <li>Select expiration ${dte} days out</li>
                        <li>Find the $${sellStrike} Put - click SELL</li>
                        <li>Find the $${buyStrike} Put - click BUY</li>
                        <li>Or use "Spread" order type and select "Put Credit Spread"</li>
                        <li>Set limit price at the mid-price shown (you receive this)</li>
                        <li>Submit order</li>
                    </ol>
                </div>
                
                <div class="explain-section">
                    <strong>Profit/Loss:</strong>
                    <ul>
                        <li><strong>Max Profit:</strong> The credit you receive upfront</li>
                        <li><strong>Max Loss:</strong> $${sellStrike - buyStrike} per share minus credit received</li>
                        <li><strong>Breakeven:</strong> $${sellStrike} - credit received</li>
                        <li><strong>Best case:</strong> Stock closes above $${sellStrike} at expiration (keep all credit)</li>
                    </ul>
                </div>
            `;
        } else if (c.trade_type === 'IRON_CONDOR') {
            const callSell = Math.round(price * 1.05);
            const callBuy = Math.round(price * 1.10);
            const putSell = Math.round(price * 0.95);
            const putBuy = Math.round(price * 0.90);
            steps = `
                <div class="action-step sell">
                    <span class="step-num">1</span>
                    <span class="step-action">SELL</span>
                    <span class="step-detail">${c.ticker} $${callSell} Call</span>
                </div>
                <div class="action-step buy">
                    <span class="step-num">2</span>
                    <span class="step-action">BUY</span>
                    <span class="step-detail">${c.ticker} $${callBuy} Call</span>
                </div>
                <div class="action-step sell">
                    <span class="step-num">3</span>
                    <span class="step-action">SELL</span>
                    <span class="step-detail">${c.ticker} $${putSell} Put</span>
                </div>
                <div class="action-step buy">
                    <span class="step-num">4</span>
                    <span class="step-action">BUY</span>
                    <span class="step-detail">${c.ticker} $${putBuy} Put</span>
                </div>
                <div class="action-note">
                    Expiration: ${dte} days out<br>
                    Profit if stock stays between $${putSell}-$${callSell}
                </div>
            `;
            explanation = `
                <h4>Why an IRON CONDOR?</h4>
                <p><strong>Strategy:</strong> ${strategyName}</p>
                <p><strong>Direction:</strong> NEUTRAL - We expect ${c.ticker} to stay in a RANGE</p>
                
                <div class="explain-section">
                    <strong>What is this trade?</strong>
                    <p>An iron condor combines a call credit spread AND a put credit spread. You're selling premium on BOTH sides, betting the stock stays within a range. It's 4 legs total.</p>
                </div>
                
                <div class="explain-section">
                    <strong>Why this structure for ${strategyName}?</strong>
                    <ul>
                        <li><strong>Range-bound stocks:</strong> ${c.ticker} has been flat - we profit from continued flatness</li>
                        <li><strong>Double premium:</strong> Collect credit from both sides</li>
                        <li><strong>High win rate:</strong> Stock can move a bit either way and you still win</li>
                        <li><strong>Time decay x2:</strong> Theta works for you on all 4 legs</li>
                        <li><strong>Defined risk:</strong> Max loss is capped by the wings</li>
                    </ul>
                </div>
                
                <div class="explain-section">
                    <strong>How to execute in your broker:</strong>
                    <ol>
                        <li>Search for ${c.ticker} options</li>
                        <li>Select expiration ${dte} days out</li>
                        <li>Use "Iron Condor" order type if available</li>
                        <li>Or build it as 2 spreads:
                            <ul>
                                <li>Call Credit Spread: Sell $${callSell} / Buy $${callBuy}</li>
                                <li>Put Credit Spread: Sell $${putSell} / Buy $${putBuy}</li>
                            </ul>
                        </li>
                        <li>Set limit price at combined mid-price</li>
                        <li>Submit order</li>
                    </ol>
                </div>
                
                <div class="explain-section">
                    <strong>Profit/Loss:</strong>
                    <ul>
                        <li><strong>Max Profit:</strong> Total credit received (both spreads combined)</li>
                        <li><strong>Max Loss:</strong> Width of one spread ($${callBuy - callSell}) minus total credit</li>
                        <li><strong>Profit Zone:</strong> Stock stays between $${putSell} and $${callSell}</li>
                        <li><strong>Best case:</strong> Stock closes anywhere in the profit zone at expiration</li>
                    </ul>
                </div>
            `;
        } else if (c.trade_type === 'CALL_LONG' || c.trade_type === 'PUT_LONG') {
            const optionType = c.trade_type === 'CALL_LONG' ? 'Call' : 'Put';
            const strike = c.trade_type === 'CALL_LONG' ? Math.round(price * 1.02) : Math.round(price * 0.98);
            const direction = c.trade_type === 'CALL_LONG' ? 'UP' : 'DOWN';
            steps = `
                <div class="action-step buy">
                    <span class="step-num">1</span>
                    <span class="step-action">BUY</span>
                    <span class="step-detail">${c.ticker} $${strike} ${optionType}</span>
                </div>
                <div class="action-note">
                    Expiration: ${dte} days out<br>
                    Single leg - higher risk, higher reward<br>
                    Max loss = premium paid
                </div>
            `;
            explanation = `
                <h4>Why a LONG ${optionType.toUpperCase()}?</h4>
                <p><strong>Strategy:</strong> ${strategyName}</p>
                <p><strong>Direction:</strong> ${c.trade_type === 'CALL_LONG' ? 'BULLISH' : 'BEARISH'} - We expect ${c.ticker} to go ${direction} QUICKLY</p>
                
                <div class="explain-section">
                    <strong>What is this trade?</strong>
                    <p>A simple long ${optionType.toLowerCase()} - you're buying the right to ${c.trade_type === 'CALL_LONG' ? 'buy' : 'sell'} the stock at $${strike}. This is the most straightforward options bet.</p>
                </div>
                
                <div class="explain-section">
                    <strong>Why this structure for ${strategyName}?</strong>
                    <ul>
                        <li><strong>Mean reversion play:</strong> Stock is at an extreme (RSI), expecting snap-back</li>
                        <li><strong>Cheap options:</strong> IV is low, so options are relatively cheap</li>
                        <li><strong>High reward potential:</strong> If the move happens, gains can be 2-5x</li>
                        <li><strong>Defined risk:</strong> Can only lose what you pay</li>
                    </ul>
                </div>
                
                <div class="explain-section">
                    <strong>How to execute in your broker:</strong>
                    <ol>
                        <li>Search for ${c.ticker} options</li>
                        <li>Select expiration ${dte} days out</li>
                        <li>Find the $${strike} ${optionType}</li>
                        <li>Click BUY</li>
                        <li>Set limit price at the ask (or slightly below)</li>
                        <li>Submit order</li>
                    </ol>
                </div>
                
                <div class="explain-section warning">
                    <strong>⚠️ Higher Risk:</strong>
                    <ul>
                        <li>No short leg to reduce cost - you pay full premium</li>
                        <li>Time decay works AGAINST you every day</li>
                        <li>Need the move to happen relatively quickly</li>
                        <li>Can lose 100% of what you paid if wrong</li>
                    </ul>
                </div>
            `;
        } else {
            steps = `<div class="action-note">See "How to Trade" for details on ${c.trade_type}</div>`;
            explanation = `<p>Trade type: ${c.trade_type}</p><p>Click "How to Trade" in the header for general guidance.</p>`;
        }
        
        return `
            ${steps}
            <div class="expand-trigger" onclick="this.parentElement.classList.toggle('expanded')">
                <span class="expand-icon">▼</span>
                <span>Learn more about this trade</span>
            </div>
            <div class="expand-content">
                ${explanation}
            </div>
        `;
    }
    
    exportResults() {
        if (!this.results || !this.results.candidates) {
            alert('No results to export');
            return;
        }
        
        // Build CSV content
        const headers = [
            'Ticker',
            'Passed',
            'Direction',
            'Trade Type',
            'Signal Strength',
            'Price',
            '5D Return',
            '20D Return',
            'IV Rank',
            'RSI',
            'MA20',
            'MA50',
            'Reasons'
        ];
        
        const rows = this.results.candidates.map(c => [
            c.ticker,
            c.passed ? 'YES' : 'NO',
            c.direction || '',
            c.trade_type || '',
            c.signal_strength.toFixed(0),
            (c.price || 0).toFixed(2),
            (c.return_5d || 0).toFixed(2),
            (c.return_20d || 0).toFixed(2),
            c.iv_rank ? c.iv_rank.toFixed(0) : '',
            c.rsi ? c.rsi.toFixed(0) : '',
            c.ma20 ? c.ma20.toFixed(2) : '',
            c.ma50 ? c.ma50.toFixed(2) : '',
            `"${(c.reasons || []).join('; ')}"`
        ]);
        
        const csvContent = [
            headers.join(','),
            ...rows.map(r => r.join(','))
        ].join('\n');
        
        // Add metadata at top
        const metadata = [
            `# Options Edge Scanner Export`,
            `# Strategy: ${this.results.strategy?.name || 'Unknown'}`,
            `# Timestamp: ${this.results.timestamp || new Date().toISOString()}`,
            `# Passed: ${this.results.passed_count} / ${this.results.total_count}`,
            ``
        ].join('\n');
        
        const fullContent = metadata + csvContent;
        
        // Download file
        const blob = new Blob([fullContent], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `options_scan_${new Date().toISOString().slice(0,10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    setStatus(text, scanning) {
        const indicator = document.getElementById('status-indicator');
        indicator.querySelector('.status-text').textContent = text;
        indicator.querySelector('.status-dot').classList.toggle('scanning', scanning);
    }
}

// Initialize app
document.addEventListener('DOMContentLoaded', () => {
    window.scanner = new OptionsScanner();
});
