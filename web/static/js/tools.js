// Tools Page JavaScript

class ToolsPage {
    constructor() {
        this.currentTool = 'calculator';
        this.watchlist = this.loadWatchlist();
        this.trades = this.loadTrades();
        this.init();
    }

    init() {
        this.bindEvents();
        this.updateJournalStats();
        this.renderWatchlist();
        this.loadEarnings();
    }

    bindEvents() {
        // Tool navigation
        document.querySelectorAll('.tool-nav-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tool = e.currentTarget.dataset.tool;
                this.switchTool(tool);
            });
        });

        // Calculator
        document.getElementById('calc-strategy').addEventListener('change', (e) => {
            this.updateCalculatorInputs(e.target.value);
        });
        document.getElementById('btn-calculate').addEventListener('click', () => {
            this.calculate();
        });

        // Watchlist
        document.getElementById('btn-add-ticker').addEventListener('click', () => {
            this.addToWatchlist();
        });
        document.getElementById('watchlist-ticker').addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addToWatchlist();
        });

        // Trade Journal
        document.getElementById('btn-new-trade').addEventListener('click', () => {
            this.openTradeModal();
        });
        document.getElementById('trade-modal-close').addEventListener('click', () => {
            this.closeTradeModal();
        });
        document.getElementById('btn-cancel-trade').addEventListener('click', () => {
            this.closeTradeModal();
        });
        document.getElementById('trade-form').addEventListener('submit', (e) => {
            e.preventDefault();
            this.saveTrade();
        });
        document.getElementById('btn-export-journal').addEventListener('click', () => {
            this.exportJournal();
        });

        // Earnings filters
        document.querySelectorAll('#tool-earnings .filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('#tool-earnings .filter-btn').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
                this.loadEarnings(e.target.dataset.filter);
            });
        });


        // Modal backdrop close
        document.getElementById('trade-modal').addEventListener('click', (e) => {
            if (e.target.id === 'trade-modal') this.closeTradeModal();
        });
    }

    switchTool(tool) {
        this.currentTool = tool;
        
        document.querySelectorAll('.tool-nav-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tool === tool);
        });
        
        document.querySelectorAll('.tool-panel').forEach(panel => {
            panel.classList.toggle('active', panel.id === `tool-${tool}`);
        });
    }

    // ========== Calculator ==========
    updateCalculatorInputs(strategy) {
        const singleLeg = document.getElementById('single-leg-inputs');
        const spread = document.getElementById('spread-inputs');
        const condor = document.getElementById('condor-inputs');

        singleLeg.style.display = 'none';
        spread.style.display = 'none';
        condor.style.display = 'none';

        if (strategy === 'long_call' || strategy === 'long_put') {
            singleLeg.style.display = 'block';
        } else if (strategy === 'iron_condor') {
            condor.style.display = 'block';
        } else {
            spread.style.display = 'block';
        }
    }

    calculate() {
        const strategy = document.getElementById('calc-strategy').value;
        const stockPrice = parseFloat(document.getElementById('calc-stock-price').value);
        const contracts = parseInt(document.getElementById('calc-contracts').value);
        const multiplier = contracts * 100;

        let maxProfit, maxLoss, breakeven, profitZone;

        if (strategy === 'long_call') {
            const strike = parseFloat(document.getElementById('calc-strike').value);
            const premium = parseFloat(document.getElementById('calc-premium').value);
            
            maxProfit = 'Unlimited';
            maxLoss = premium * multiplier;
            breakeven = strike + premium;
            profitZone = `Above $${breakeven.toFixed(2)}`;
        } 
        else if (strategy === 'long_put') {
            const strike = parseFloat(document.getElementById('calc-strike').value);
            const premium = parseFloat(document.getElementById('calc-premium').value);
            
            maxProfit = (strike - premium) * multiplier;
            maxLoss = premium * multiplier;
            breakeven = strike - premium;
            profitZone = `Below $${breakeven.toFixed(2)}`;
        }
        else if (strategy === 'call_debit' || strategy === 'put_debit') {
            const longStrike = parseFloat(document.getElementById('calc-long-strike').value);
            const shortStrike = parseFloat(document.getElementById('calc-short-strike').value);
            const netPremium = parseFloat(document.getElementById('calc-net-premium').value);
            
            const width = Math.abs(shortStrike - longStrike);
            maxProfit = (width - netPremium) * multiplier;
            maxLoss = netPremium * multiplier;
            
            if (strategy === 'call_debit') {
                breakeven = longStrike + netPremium;
                profitZone = `Above $${breakeven.toFixed(2)}`;
            } else {
                breakeven = longStrike - netPremium;
                profitZone = `Below $${breakeven.toFixed(2)}`;
            }
        }
        else if (strategy === 'call_credit' || strategy === 'put_credit') {
            const longStrike = parseFloat(document.getElementById('calc-long-strike').value);
            const shortStrike = parseFloat(document.getElementById('calc-short-strike').value);
            const netPremium = parseFloat(document.getElementById('calc-net-premium').value);
            
            const width = Math.abs(shortStrike - longStrike);
            maxProfit = netPremium * multiplier;
            maxLoss = (width - netPremium) * multiplier;
            
            if (strategy === 'call_credit') {
                breakeven = Math.min(longStrike, shortStrike) + netPremium;
                profitZone = `Below $${breakeven.toFixed(2)}`;
            } else {
                breakeven = Math.max(longStrike, shortStrike) - netPremium;
                profitZone = `Above $${breakeven.toFixed(2)}`;
            }
        }
        else if (strategy === 'iron_condor') {
            const putBuy = parseFloat(document.getElementById('calc-put-buy').value);
            const putSell = parseFloat(document.getElementById('calc-put-sell').value);
            const callSell = parseFloat(document.getElementById('calc-call-sell').value);
            const callBuy = parseFloat(document.getElementById('calc-call-buy').value);
            const credit = parseFloat(document.getElementById('calc-condor-credit').value);
            
            const width = Math.max(putSell - putBuy, callBuy - callSell);
            maxProfit = credit * multiplier;
            maxLoss = (width - credit) * multiplier;
            breakeven = `$${(putSell - credit).toFixed(2)} / $${(callSell + credit).toFixed(2)}`;
            profitZone = `Between $${putSell.toFixed(2)} and $${callSell.toFixed(2)}`;
        }

        // Display results
        document.getElementById('result-max-profit').textContent = 
            maxProfit === 'Unlimited' ? 'Unlimited' : `$${maxProfit.toFixed(2)}`;
        document.getElementById('result-max-loss').textContent = `-$${maxLoss.toFixed(2)}`;
        document.getElementById('result-breakeven').textContent = 
            typeof breakeven === 'string' ? breakeven : `$${breakeven.toFixed(2)}`;
        document.getElementById('result-zone').textContent = profitZone;

        // Risk/Reward ratio
        if (maxProfit === 'Unlimited') {
            document.getElementById('result-rr').textContent = '∞:1';
            document.getElementById('result-winrate').textContent = 'N/A';
        } else {
            const rr = (maxProfit / maxLoss).toFixed(2);
            document.getElementById('result-rr').textContent = `${rr}:1`;
            const winRateNeeded = (1 / (1 + parseFloat(rr)) * 100).toFixed(0);
            document.getElementById('result-winrate').textContent = `${winRateNeeded}%`;
        }

        // Draw P/L chart
        this.drawPLChart(strategy, stockPrice, contracts);
    }

    drawPLChart(strategy, stockPrice, contracts) {
        const canvas = document.getElementById('pl-canvas');
        const ctx = canvas.getContext('2d');
        
        // Set canvas size
        canvas.width = canvas.parentElement.offsetWidth - 32;
        canvas.height = canvas.parentElement.offsetHeight - 32;
        
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;
        
        // Clear canvas
        ctx.fillStyle = '#0d1117';
        ctx.fillRect(0, 0, width, height);
        
        // Calculate P/L data points
        const priceRange = stockPrice * 0.3;
        const minPrice = stockPrice - priceRange;
        const maxPrice = stockPrice + priceRange;
        const points = [];
        
        for (let price = minPrice; price <= maxPrice; price += priceRange / 50) {
            const pl = this.calculatePLAtPrice(strategy, price, contracts);
            points.push({ price, pl });
        }
        
        // Find min/max P/L for scaling
        const plValues = points.map(p => p.pl);
        const minPL = Math.min(...plValues);
        const maxPL = Math.max(...plValues);
        const plRange = maxPL - minPL || 1;
        
        // Draw grid
        ctx.strokeStyle = '#30363d';
        ctx.lineWidth = 1;
        
        // Horizontal grid lines
        for (let i = 0; i <= 4; i++) {
            const y = padding + (height - 2 * padding) * i / 4;
            ctx.beginPath();
            ctx.moveTo(padding, y);
            ctx.lineTo(width - padding, y);
            ctx.stroke();
        }
        
        // Draw zero line
        const zeroY = padding + (height - 2 * padding) * (maxPL / plRange);
        ctx.strokeStyle = '#6e7681';
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(padding, zeroY);
        ctx.lineTo(width - padding, zeroY);
        ctx.stroke();
        ctx.setLineDash([]);
        
        // Draw current stock price line
        const currentX = padding + (stockPrice - minPrice) / (maxPrice - minPrice) * (width - 2 * padding);
        ctx.strokeStyle = '#58a6ff';
        ctx.setLineDash([5, 5]);
        ctx.beginPath();
        ctx.moveTo(currentX, padding);
        ctx.lineTo(currentX, height - padding);
        ctx.stroke();
        ctx.setLineDash([]);
        
        // Draw P/L line
        ctx.beginPath();
        ctx.strokeStyle = '#39c5cf';
        ctx.lineWidth = 2;
        
        points.forEach((point, i) => {
            const x = padding + (point.price - minPrice) / (maxPrice - minPrice) * (width - 2 * padding);
            const y = padding + (maxPL - point.pl) / plRange * (height - 2 * padding);
            
            if (i === 0) {
                ctx.moveTo(x, y);
            } else {
                ctx.lineTo(x, y);
            }
        });
        ctx.stroke();
        
        // Fill profit area
        ctx.beginPath();
        ctx.fillStyle = 'rgba(63, 185, 80, 0.1)';
        let started = false;
        points.forEach((point, i) => {
            if (point.pl > 0) {
                const x = padding + (point.price - minPrice) / (maxPrice - minPrice) * (width - 2 * padding);
                const y = padding + (maxPL - point.pl) / plRange * (height - 2 * padding);
                if (!started) {
                    ctx.moveTo(x, zeroY);
                    started = true;
                }
                ctx.lineTo(x, y);
            }
        });
        if (started) {
            const lastProfitPoint = points.filter(p => p.pl > 0).pop();
            if (lastProfitPoint) {
                const x = padding + (lastProfitPoint.price - minPrice) / (maxPrice - minPrice) * (width - 2 * padding);
                ctx.lineTo(x, zeroY);
            }
            ctx.closePath();
            ctx.fill();
        }
        
        // Labels
        ctx.fillStyle = '#8b949e';
        ctx.font = '10px JetBrains Mono';
        ctx.textAlign = 'center';
        
        // Price labels
        ctx.fillText(`$${minPrice.toFixed(0)}`, padding, height - 10);
        ctx.fillText(`$${stockPrice.toFixed(0)}`, currentX, height - 10);
        ctx.fillText(`$${maxPrice.toFixed(0)}`, width - padding, height - 10);
        
        // P/L labels
        ctx.textAlign = 'right';
        ctx.fillText(`$${maxPL.toFixed(0)}`, padding - 5, padding + 4);
        ctx.fillText(`$0`, padding - 5, zeroY + 4);
        ctx.fillText(`$${minPL.toFixed(0)}`, padding - 5, height - padding + 4);
    }

    calculatePLAtPrice(strategy, price, contracts) {
        const multiplier = contracts * 100;
        
        if (strategy === 'long_call') {
            const strike = parseFloat(document.getElementById('calc-strike').value);
            const premium = parseFloat(document.getElementById('calc-premium').value);
            return (Math.max(0, price - strike) - premium) * multiplier;
        }
        else if (strategy === 'long_put') {
            const strike = parseFloat(document.getElementById('calc-strike').value);
            const premium = parseFloat(document.getElementById('calc-premium').value);
            return (Math.max(0, strike - price) - premium) * multiplier;
        }
        else if (strategy === 'call_debit') {
            const longStrike = parseFloat(document.getElementById('calc-long-strike').value);
            const shortStrike = parseFloat(document.getElementById('calc-short-strike').value);
            const netPremium = parseFloat(document.getElementById('calc-net-premium').value);
            const longValue = Math.max(0, price - longStrike);
            const shortValue = Math.max(0, price - shortStrike);
            return (longValue - shortValue - netPremium) * multiplier;
        }
        else if (strategy === 'put_debit') {
            const longStrike = parseFloat(document.getElementById('calc-long-strike').value);
            const shortStrike = parseFloat(document.getElementById('calc-short-strike').value);
            const netPremium = parseFloat(document.getElementById('calc-net-premium').value);
            const longValue = Math.max(0, longStrike - price);
            const shortValue = Math.max(0, shortStrike - price);
            return (longValue - shortValue - netPremium) * multiplier;
        }
        else if (strategy === 'call_credit') {
            const longStrike = parseFloat(document.getElementById('calc-long-strike').value);
            const shortStrike = parseFloat(document.getElementById('calc-short-strike').value);
            const netPremium = parseFloat(document.getElementById('calc-net-premium').value);
            const shortValue = Math.max(0, price - Math.min(longStrike, shortStrike));
            const longValue = Math.max(0, price - Math.max(longStrike, shortStrike));
            return (netPremium - shortValue + longValue) * multiplier;
        }
        else if (strategy === 'put_credit') {
            const longStrike = parseFloat(document.getElementById('calc-long-strike').value);
            const shortStrike = parseFloat(document.getElementById('calc-short-strike').value);
            const netPremium = parseFloat(document.getElementById('calc-net-premium').value);
            const shortValue = Math.max(0, Math.max(longStrike, shortStrike) - price);
            const longValue = Math.max(0, Math.min(longStrike, shortStrike) - price);
            return (netPremium - shortValue + longValue) * multiplier;
        }
        else if (strategy === 'iron_condor') {
            const putBuy = parseFloat(document.getElementById('calc-put-buy').value);
            const putSell = parseFloat(document.getElementById('calc-put-sell').value);
            const callSell = parseFloat(document.getElementById('calc-call-sell').value);
            const callBuy = parseFloat(document.getElementById('calc-call-buy').value);
            const credit = parseFloat(document.getElementById('calc-condor-credit').value);
            
            const putSpreadValue = Math.max(0, putSell - price) - Math.max(0, putBuy - price);
            const callSpreadValue = Math.max(0, price - callSell) - Math.max(0, price - callBuy);
            return (credit - putSpreadValue - callSpreadValue) * multiplier;
        }
        return 0;
    }

    // ========== Watchlist ==========
    loadWatchlist() {
        try {
            return JSON.parse(localStorage.getItem('options_watchlist')) || [];
        } catch {
            return [];
        }
    }

    saveWatchlist() {
        localStorage.setItem('options_watchlist', JSON.stringify(this.watchlist));
    }

    async addToWatchlist() {
        const input = document.getElementById('watchlist-ticker');
        const ticker = input.value.trim().toUpperCase();
        
        if (!ticker) return;
        if (this.watchlist.find(w => w.ticker === ticker)) {
            alert('Ticker already in watchlist');
            return;
        }

        // Add to watchlist with placeholder data
        this.watchlist.push({
            ticker,
            price: '--',
            change: '--',
            ivRank: '--',
            notes: '',
            addedAt: new Date().toISOString()
        });
        
        this.saveWatchlist();
        this.renderWatchlist();
        input.value = '';

        // Fetch real data (if API available)
        this.updateWatchlistData(ticker);
    }

    async updateWatchlistData(ticker) {
        try {
            // Try to fetch from our API
            const response = await fetch(`/api/quote/${ticker}`);
            if (response.ok) {
                const data = await response.json();
                const item = this.watchlist.find(w => w.ticker === ticker);
                if (item) {
                    item.price = data.price || '--';
                    item.change = data.change_pct ? `${data.change_pct.toFixed(2)}%` : '--';
                    item.ivRank = data.iv_rank ? `${data.iv_rank.toFixed(0)}` : '--';
                    this.saveWatchlist();
                    this.renderWatchlist();
                }
            }
        } catch (e) {
            console.log('Could not fetch quote data:', e);
        }
    }

    removeFromWatchlist(ticker) {
        this.watchlist = this.watchlist.filter(w => w.ticker !== ticker);
        this.saveWatchlist();
        this.renderWatchlist();
    }

    updateWatchlistNotes(ticker, notes) {
        const item = this.watchlist.find(w => w.ticker === ticker);
        if (item) {
            item.notes = notes;
            this.saveWatchlist();
        }
    }

    renderWatchlist() {
        const tbody = document.getElementById('watchlist-body');
        
        if (this.watchlist.length === 0) {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="6">Add tickers to your watchlist to track them</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.watchlist.map(item => {
            const changeClass = item.change.includes('-') ? 'negative' : 
                               (item.change !== '--' ? 'positive' : '');
            return `
                <tr>
                    <td><strong>${item.ticker}</strong></td>
                    <td>${item.price !== '--' ? '$' + item.price : '--'}</td>
                    <td class="${changeClass}">${item.change}</td>
                    <td>${item.ivRank}</td>
                    <td>
                        <input type="text" class="notes-input" value="${item.notes || ''}" 
                               placeholder="Add notes..." 
                               onchange="window.tools.updateWatchlistNotes('${item.ticker}', this.value)">
                    </td>
                    <td>
                        <button class="btn-remove" onclick="window.tools.removeFromWatchlist('${item.ticker}')">
                            Remove
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // ========== Trade Journal ==========
    loadTrades() {
        try {
            return JSON.parse(localStorage.getItem('options_trades')) || [];
        } catch {
            return [];
        }
    }

    saveTrades() {
        localStorage.setItem('options_trades', JSON.stringify(this.trades));
    }

    openTradeModal() {
        document.getElementById('trade-modal').style.display = 'flex';
        document.getElementById('trade-date').value = new Date().toISOString().split('T')[0];
    }

    closeTradeModal() {
        document.getElementById('trade-modal').style.display = 'none';
        document.getElementById('trade-form').reset();
    }

    saveTrade() {
        const trade = {
            id: Date.now(),
            ticker: document.getElementById('trade-ticker').value.toUpperCase(),
            date: document.getElementById('trade-date').value,
            strategy: document.getElementById('trade-strategy').value,
            entry: parseFloat(document.getElementById('trade-entry').value),
            exit: document.getElementById('trade-exit').value ? 
                  parseFloat(document.getElementById('trade-exit').value) : null,
            contracts: parseInt(document.getElementById('trade-contracts').value),
            notes: document.getElementById('trade-notes').value
        };

        this.trades.unshift(trade);
        this.saveTrades();
        this.renderJournal();
        this.updateJournalStats();
        this.closeTradeModal();
    }

    updateJournalStats() {
        const closedTrades = this.trades.filter(t => t.exit !== null);
        const totalTrades = closedTrades.length;
        
        if (totalTrades === 0) {
            document.getElementById('stat-total-trades').textContent = this.trades.length;
            document.getElementById('stat-win-rate').textContent = '0%';
            document.getElementById('stat-total-pnl').textContent = '$0';
            document.getElementById('stat-avg-win').textContent = '$0';
            document.getElementById('stat-avg-loss').textContent = '$0';
            return;
        }

        const pnls = closedTrades.map(t => (t.exit - t.entry) * t.contracts * 100);
        const wins = pnls.filter(p => p > 0);
        const losses = pnls.filter(p => p < 0);
        
        const totalPnl = pnls.reduce((a, b) => a + b, 0);
        const winRate = (wins.length / totalTrades * 100).toFixed(0);
        const avgWin = wins.length > 0 ? wins.reduce((a, b) => a + b, 0) / wins.length : 0;
        const avgLoss = losses.length > 0 ? losses.reduce((a, b) => a + b, 0) / losses.length : 0;

        document.getElementById('stat-total-trades').textContent = this.trades.length;
        document.getElementById('stat-win-rate').textContent = `${winRate}%`;
        document.getElementById('stat-win-rate').className = `stat-value ${winRate >= 50 ? 'positive' : 'negative'}`;
        
        document.getElementById('stat-total-pnl').textContent = `$${totalPnl.toFixed(0)}`;
        document.getElementById('stat-total-pnl').className = `stat-value ${totalPnl >= 0 ? 'positive' : 'negative'}`;
        
        document.getElementById('stat-avg-win').textContent = `$${avgWin.toFixed(0)}`;
        document.getElementById('stat-avg-win').className = 'stat-value positive';
        
        document.getElementById('stat-avg-loss').textContent = `$${avgLoss.toFixed(0)}`;
        document.getElementById('stat-avg-loss').className = 'stat-value negative';
    }

    renderJournal() {
        const tbody = document.getElementById('journal-body');
        
        if (this.trades.length === 0) {
            tbody.innerHTML = `
                <tr class="empty-row">
                    <td colspan="7">No trades recorded yet. Click "New Trade" to add one.</td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.trades.map(trade => {
            let pnl = '--';
            let pnlClass = '';
            
            if (trade.exit !== null) {
                const profit = (trade.exit - trade.entry) * trade.contracts * 100;
                pnl = `$${profit.toFixed(0)}`;
                pnlClass = profit >= 0 ? 'positive' : 'negative';
            }

            return `
                <tr>
                    <td>${trade.date}</td>
                    <td><strong>${trade.ticker}</strong></td>
                    <td>${trade.strategy}</td>
                    <td>$${trade.entry.toFixed(2)}</td>
                    <td>${trade.exit !== null ? '$' + trade.exit.toFixed(2) : 'Open'}</td>
                    <td class="${pnlClass}">${pnl}</td>
                    <td>${trade.notes || '-'}</td>
                </tr>
            `;
        }).join('');
    }

    exportJournal() {
        if (this.trades.length === 0) {
            alert('No trades to export');
            return;
        }

        const headers = ['Date', 'Ticker', 'Strategy', 'Entry', 'Exit', 'Contracts', 'P/L', 'Notes'];
        const rows = this.trades.map(t => {
            const pnl = t.exit !== null ? ((t.exit - t.entry) * t.contracts * 100).toFixed(2) : '';
            return [
                t.date,
                t.ticker,
                t.strategy,
                t.entry.toFixed(2),
                t.exit !== null ? t.exit.toFixed(2) : '',
                t.contracts,
                pnl,
                `"${t.notes || ''}"`
            ];
        });

        const csv = [headers.join(','), ...rows.map(r => r.join(','))].join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `trade_journal_${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
    }

    // ========== Earnings Calendar ==========
    async loadEarnings(filter = 'this-week') {
        const grid = document.getElementById('earnings-grid');
        grid.innerHTML = '<div class="loading-state">Loading earnings calendar...</div>';

        try {
            const response = await fetch(`/api/earnings?filter=${filter}`);
            const data = await response.json();
            
            if (data.earnings && data.earnings.length > 0) {
                this.renderEarnings(data.earnings);
            } else {
                grid.innerHTML = '<div class="loading-state">No earnings scheduled for this period</div>';
            }
        } catch (e) {
            // Show sample data if API not available
            this.renderEarnings(this.getSampleEarnings());
        }
    }

    getSampleEarnings() {
        const today = new Date();
        return [
            { ticker: 'AAPL', date: new Date(today.getTime() + 86400000).toISOString(), time: 'amc', estimate: '1.43' },
            { ticker: 'MSFT', date: new Date(today.getTime() + 86400000 * 2).toISOString(), time: 'amc', estimate: '2.82' },
            { ticker: 'GOOGL', date: new Date(today.getTime() + 86400000 * 3).toISOString(), time: 'amc', estimate: '1.85' },
            { ticker: 'AMZN', date: new Date(today.getTime() + 86400000 * 4).toISOString(), time: 'bmo', estimate: '1.14' },
            { ticker: 'META', date: new Date(today.getTime() + 86400000 * 5).toISOString(), time: 'amc', estimate: '4.96' },
            { ticker: 'NVDA', date: new Date(today.getTime() + 86400000 * 6).toISOString(), time: 'amc', estimate: '0.64' },
        ];
    }

    renderEarnings(earnings) {
        const grid = document.getElementById('earnings-grid');
        
        grid.innerHTML = earnings.map(e => {
            const date = new Date(e.date);
            const dateStr = date.toLocaleDateString('en-US', { 
                weekday: 'short', 
                month: 'short', 
                day: 'numeric' 
            });
            const timeClass = e.time === 'bmo' ? 'before-open' : 'after-close';
            const timeLabel = e.time === 'bmo' ? 'Before Open' : 'After Close';
            const timeBadgeClass = e.time === 'bmo' ? 'bmo' : 'amc';

            return `
                <div class="earnings-card ${timeClass}">
                    <div class="earnings-header">
                        <span class="earnings-ticker">${e.ticker}</span>
                        <span class="earnings-time ${timeBadgeClass}">${timeLabel}</span>
                    </div>
                    <div class="earnings-date">📅 ${dateStr}</div>
                    <div class="earnings-estimate">Est. EPS: $${e.estimate || 'N/A'}</div>
                </div>
            `;
        }).join('');
    }

}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    window.tools = new ToolsPage();
});

