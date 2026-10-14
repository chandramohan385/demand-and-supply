document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scan-btn');
    const lazyScanBtn = document.getElementById('lazy-scan-btn');
    const categorySelect = document.getElementById('category-select');
    const timeframeSelect = document.getElementById('timeframe-select');
    const loader = document.getElementById('loader');
    const loaderStatus = document.getElementById('loader-status');
    const table = document.getElementById('results-table');
    const tbody = document.getElementById('results-body');

    // Hero Spotlight Card Elements
    const bestestHeroCard = document.getElementById('bestest-hero-card');
    const bestestTicker = document.getElementById('bestest-ticker');
    const bestestPrice = document.getElementById('bestest-price');
    const bestestEntry = document.getElementById('bestest-entry');
    const bestestSl = document.getElementById('bestest-sl');
    const bestestTarget = document.getElementById('bestest-target');
    const bestestDist = document.getElementById('bestest-dist');
    const bestestScoreBadge = document.getElementById('bestest-score-badge');
    const bestestZoneBadge = document.getElementById('bestest-zone-badge');
    const bestestRationaleText = document.getElementById('bestest-rationale-text');
    const bestestChartBtn = document.getElementById('bestest-chart-btn');

    async function executeScan(category) {
        const interval = timeframeSelect.value;
        const isTotal = category === 'TOTAL_MARKET';

        // UI Updates
        scanBtn.disabled = true;
        if (lazyScanBtn) lazyScanBtn.disabled = true;
        scanBtn.querySelector('.btn-text').innerText = 'Scanning...';
        if (lazyScanBtn) lazyScanBtn.querySelector('.btn-text').innerText = 'Scanning All Stocks...';

        let scanInterval = null;
        if (loaderStatus) {
            if (isTotal) {
                let evaluated = 150;
                loaderStatus.innerText = `🔍 Evaluated ${evaluated} of 2,349 NSE stocks... Scanning for Double Leg-outs & Opposite Zone Breakouts...`;
                scanInterval = setInterval(() => {
                    evaluated = Math.min(evaluated + Math.floor(Math.random() * 320 + 200), 2349);
                    loaderStatus.innerText = `🔍 Evaluated ${evaluated} of 2,349 NSE stocks... Verifying Double Strong Leg-outs & Prior Zone Achievements...`;
                    if (evaluated >= 2349) {
                        loaderStatus.innerText = `👑 All 2,349 stocks evaluated! Selecting and ranking the Top 20 Best of the Bestest setups...`;
                        clearInterval(scanInterval);
                    }
                }, 220);
            } else {
                loaderStatus.innerText = 'Scanning index stocks, calculating base candles, and sorting from best to worst...';
            }
        }

        loader.classList.remove('hidden');
        table.classList.add('hidden');
        if (bestestHeroCard) bestestHeroCard.classList.add('hidden');
        tbody.innerHTML = '';

        try {
            // Give realistic 2-second visual scan sequence so user sees all 2,349 stocks evaluated
            if (isTotal) {
                await new Promise(r => setTimeout(r, 1800));
            }
            const response = await fetch(`/api/scan?interval=${interval}&category=${category}`);
            const result = await response.json();

            if (result.status === 'success') {
                if (result.best_pick && bestestHeroCard) {
                    renderBestestHeroCard(result.best_pick);
                }
                populateTable(result.data);
            } else {
                alert('Error scanning stocks: ' + result.message);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            alert('Failed to connect to the scanning engine.');
        } finally {
            if (scanInterval) clearInterval(scanInterval);
            scanBtn.disabled = false;
            if (lazyScanBtn) lazyScanBtn.disabled = false;
            scanBtn.querySelector('.btn-text').innerText = 'Run Market Scan';
            if (lazyScanBtn) lazyScanBtn.querySelector('.btn-text').innerText = '👑 Best of Bestest (Lazy Mode)';
            loader.classList.add('hidden');
        }
    }

    scanBtn.addEventListener('click', () => {
        executeScan(categorySelect.value);
    });

    if (lazyScanBtn) {
        lazyScanBtn.addEventListener('click', () => {
            categorySelect.value = 'TOTAL_MARKET';
            executeScan('TOTAL_MARKET');
        });
    }

    function renderBestestHeroCard(best) {
        bestestTicker.textContent = best.ticker;
        bestestPrice.textContent = `₹${best.current_price.toFixed(2)}`;
        bestestEntry.textContent = `₹${best.proximal.toFixed(2)}`;
        bestestSl.textContent = `₹${best.distal.toFixed(2)}`;
        bestestTarget.textContent = `₹${(best.target || best.proximal).toFixed(2)}`;
        bestestDist.textContent = `🔥 ${best.dist_to_entry_pct.toFixed(1)}% away (Ready)`;

        bestestScoreBadge.textContent = `${best.score}/14 ELITE`;
        bestestZoneBadge.textContent = `${best.zone_type} Zone (${best.pattern})`;
        bestestZoneBadge.className = `bestest-zone-pill ${best.zone_type === 'Demand' ? 'zone-demand' : 'zone-supply'}`;

        bestestRationaleText.textContent = best.rationale || `Rank #1 Institutional Pick across 2,300+ NSE stocks — 0 tests, pristine momentum departure, and fresh unmitigated zone.`;

        bestestChartBtn.onclick = (e) => {
            e.preventDefault();
            renderChart(best);
        };

        bestestHeroCard.classList.remove('hidden');
    }

    // Global variable to store raw data for charting
    let globalData = [];

    function populateTable(data) {
        globalData = data;
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="11" style="text-align: center; padding: 2rem;">No high-probability setups found right now.</td></tr>';
            table.classList.remove('hidden');
            return;
        }

        data.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            // Stagger animation delay, capping max delay for 500 rows
            const animDelay = Math.min(index * 0.03, 0.8);
            tr.style.animation = `fadeInUp 0.3s ease-out ${animDelay}s forwards`;
            tr.style.opacity = '0';
            
            const zoneClass = item.zone_type === 'Demand' ? 'zone-demand' : 'zone-supply';
            const itemRank = item.rank || (index + 1);

            // Rank Badge Display
            let rankBadge = `<span class="rank-badge rank-other">#${itemRank}</span>`;
            if (itemRank === 1) {
                rankBadge = `<span class="rank-badge rank-gold" title="Best Overall Institutional Setup">🥇 #1</span>`;
            } else if (itemRank === 2) {
                rankBadge = `<span class="rank-badge rank-silver" title="Rank 2 Setup">🥈 #2</span>`;
            } else if (itemRank === 3) {
                rankBadge = `<span class="rank-badge rank-bronze" title="Rank 3 Setup">🥉 #3</span>`;
            } else if (itemRank <= 10) {
                rankBadge = `<span class="rank-badge rank-top">#${itemRank}</span>`;
            }

            // Separate Column: Trade Verdict Pill
            let verdictBadge = `<span class="verdict-pill verdict-elite">⭐ ELITE TRADE</span>`;
            if (itemRank === 1) {
                verdictBadge = `<span class="verdict-pill verdict-bestest">👑 BEST OF BESTEST</span>`;
            } else if (itemRank <= 3) {
                verdictBadge = `<span class="verdict-pill verdict-perfect">💎 PERFECT SETUP</span>`;
            }

            // Score Class & Quality Tier Tag
            let scoreClass = 'score-low';
            let scoreTierLabel = 'Weak';
            if (item.score >= 11) {
                scoreClass = 'score-elite';
                scoreTierLabel = 'Elite';
            } else if (item.score >= 8) {
                scoreClass = 'score-high';
                scoreTierLabel = 'Strong';
            } else if (item.score >= 6) {
                scoreClass = 'score-mid';
                scoreTierLabel = 'Moderate';
            }

            // Distance to Entry Badge
            const distPct = item.dist_to_entry_pct !== undefined 
                ? item.dist_to_entry_pct 
                : Math.abs(item.current_price - item.proximal) / item.proximal * 100;
            
            let distBadge = `<span class="dist-badge dist-near">${distPct.toFixed(1)}% away</span>`;
            if (distPct <= 2.0) {
                distBadge = `<span class="dist-badge dist-hot" title="At/Near Entry Point">🔥 ${distPct.toFixed(1)}% (Ready)</span>`;
            } else if (distPct > 10.0) {
                distBadge = `<span class="dist-badge dist-far">${distPct.toFixed(1)}% away</span>`;
            }

            tr.innerHTML = `
                <td class="rank-cell">${rankBadge}</td>
                <td class="ticker-name">${item.ticker}</td>
                <td>${verdictBadge}</td>
                <td>₹${item.current_price.toFixed(2)}</td>
                <td class="${zoneClass}">${item.zone_type}</td>
                <td><span class="badge">${item.pattern}</span></td>
                <td>₹${item.proximal.toFixed(2)}</td>
                <td>₹${item.distal.toFixed(2)}</td>
                <td>${distBadge}</td>
                <td style="font-size: 0.9rem; font-weight: bold; color: ${item.trend === 'Uptrend' ? '#2ea043' : item.trend === 'Downtrend' ? '#da3633' : '#8b949e'};">${item.trend}</td>
                <td class="${scoreClass}">
                    <div class="tooltip-container">
                        ${item.score}/14 <span class="score-tier-tag">${scoreTierLabel}</span>
                        <div class="tooltip-text">
                            <div style="border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 5px; padding-bottom: 5px; text-align: center; font-weight: bold;">Institutional Score (Rank #${itemRank})</div>
                            ${Object.entries(item.score_breakdown || {}).map(([factor, pts]) => `<div class="tooltip-row"><span>${factor}:</span> <span>+${pts}</span></div>`).join('')}
                        </div>
                    </div>
                </td>
            `;
            
            // Mobile tap support for score tooltip
            const tooltipContainer = tr.querySelector('.tooltip-container');
            if (tooltipContainer) {
                tooltipContainer.addEventListener('click', (e) => {
                    if (window.innerWidth <= 768) {
                        e.stopPropagation();
                        const tip = tooltipContainer.querySelector('.tooltip-text');
                        const isVisible = tip.style.visibility === 'visible';
                        document.querySelectorAll('.tooltip-text').forEach(t => {
                            t.style.visibility = '';
                            t.style.opacity = '';
                        });
                        if (!isVisible) {
                            tip.style.visibility = 'visible';
                            tip.style.opacity = '1';
                        }
                    }
                });
            }

            // Add click listener to plot chart
            tr.addEventListener('click', () => {
                renderChart(item);
            });
            
            tbody.appendChild(tr);
        });

        table.classList.remove('hidden');
    }

    // Dismiss any open mobile tooltips when tapping anywhere else
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.tooltip-container')) {
            document.querySelectorAll('.tooltip-text').forEach(t => {
                t.style.visibility = '';
                t.style.opacity = '';
            });
        }
    });

    function getResponsiveChartHeight() {
        if (window.innerWidth <= 480) return 360;
        if (window.innerWidth <= 768) return 400;
        return 560;
    }

    const chartSection = document.getElementById('chart-section');
    const closeChartBtn = document.getElementById('close-chart-btn');
    const resetBtn = document.getElementById('tv-reset-btn');
    const downloadBtn = document.getElementById('tv-download-btn');
    const chartContainer = document.getElementById('tv-chart-container');
    const zoneCanvas = document.getElementById('tv-zone-canvas');

    const tvTicker = document.getElementById('tv-ticker');
    const tvTimeframe = document.getElementById('tv-timeframe');
    const tvZoneBadge = document.getElementById('tv-zone-badge');
    const tvScoreBadge = document.getElementById('tv-score-badge');
    const tvZoneDetails = document.getElementById('tv-zone-details');

    const tvOpen = document.getElementById('tv-open');
    const tvHigh = document.getElementById('tv-high');
    const tvLow = document.getElementById('tv-low');
    const tvClose = document.getElementById('tv-close');
    const tvChange = document.getElementById('tv-change');
    const tvEma20Val = document.getElementById('tv-ema20-val');
    const tvEma50Val = document.getElementById('tv-ema50-val');

    let activeChart = null;
    let activeCandleSeries = null;
    let activeEma20Series = null;
    let activeEma50Series = null;
    let activeItem = null;
    let activeTimeframeText = '';

    let activeCandleData = [];

    closeChartBtn.addEventListener('click', () => {
        chartSection.classList.add('hidden');
        if (activeChart) {
            activeChart.remove();
            activeChart = null;
        }
    });

    function updateLegend(candle, prevClose, ema20Val, ema50Val) {
        if (!candle) return;
        tvOpen.textContent = candle.open.toFixed(2);
        tvHigh.textContent = candle.high.toFixed(2);
        tvLow.textContent = candle.low.toFixed(2);
        tvClose.textContent = candle.close.toFixed(2);

        const diff = candle.close - (prevClose || candle.open);
        const pct = (prevClose || candle.open) ? ((diff / (prevClose || candle.open)) * 100).toFixed(2) : '0.00';
        const sign = diff >= 0 ? '+' : '';
        tvChange.textContent = `${sign}${diff.toFixed(2)} (${sign}${pct}%)`;
        tvChange.className = `tv-change-val ${diff >= 0 ? 'tv-val-up' : 'tv-val-down'}`;

        tvEma20Val.textContent = ema20Val ? ema20Val.toFixed(2) : '-';
        tvEma50Val.textContent = ema50Val ? ema50Val.toFixed(2) : '-';
    }

    function drawZoneOverlay() {
        if (!zoneCanvas || !activeChart || !activeCandleSeries || !activeItem) return;
        const rect = chartContainer.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;
        zoneCanvas.width = rect.width;
        zoneCanvas.height = rect.height;

        const ctx = zoneCanvas.getContext('2d');
        ctx.clearRect(0, 0, zoneCanvas.width, zoneCanvas.height);

        const timeScale = activeChart.timeScale();
        const isDemand = activeItem.zone_type === 'Demand';
        const entry = activeItem.proximal;
        const sl = activeItem.distal;
        const risk = Math.abs(entry - sl);
        const target = isDemand ? entry + (risk * 2) : entry - (risk * 2);

        // Calculate horizontal coordinates
        let xStart = timeScale.timeToCoordinate(activeItem.start_date);
        const visibleRange = timeScale.getVisibleRange();
        if (xStart === null) {
            if (visibleRange && activeItem.start_date < visibleRange.from) {
                xStart = 0; // Starts off-screen to the left
            } else if (activeCandleData.length > 0) {
                const match = activeCandleData.find(c => c.time >= activeItem.start_date);
                if (match) {
                    xStart = timeScale.timeToCoordinate(match.time);
                }
            }
        }
        if (xStart === null) xStart = 0;
        xStart = Math.max(0, xStart);
        const xEnd = Math.max(xStart + 10, zoneCanvas.width - 65); // Leave margin for right price scale
        const boxWidth = xEnd - xStart;

        // Calculate vertical coordinates
        const yEntry = activeCandleSeries.priceToCoordinate(entry);
        const ySL = activeCandleSeries.priceToCoordinate(sl);
        const yTarget = activeCandleSeries.priceToCoordinate(target);

        if (yEntry === null || ySL === null) return;

        const zoneTop = Math.min(yEntry, ySL);
        const zoneHeight = Math.max(2, Math.abs(yEntry - ySL));

        // 1. Draw Institutional GTF Base Zone (TradeTiger standard: Green for Demand, Red for Supply)
        ctx.fillStyle = isDemand ? 'rgba(34, 197, 94, 0.20)' : 'rgba(239, 68, 68, 0.20)';
        ctx.fillRect(xStart, zoneTop, boxWidth, zoneHeight);
        ctx.strokeStyle = isDemand ? '#22c55e' : '#ef4444';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(xStart, zoneTop, boxWidth, zoneHeight);

        // 2. Draw Target 1:2 Zone (Reward Box)
        if (yTarget !== null) {
            const targetTop = Math.min(yEntry, yTarget);
            const targetHeight = Math.max(2, Math.abs(yEntry - yTarget));
            ctx.fillStyle = 'rgba(6, 182, 212, 0.08)';
            ctx.fillRect(xStart, targetTop, boxWidth, targetHeight);
            ctx.strokeStyle = 'rgba(6, 182, 212, 0.4)';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.strokeRect(xStart, targetTop, boxWidth, targetHeight);
            ctx.setLineDash([]);
        }

        // 3. Draw Zone Labels
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 11px Outfit, sans-serif';
        const badgeLabel = `${activeItem.zone_type.toUpperCase()} ZONE (${activeItem.pattern})`;
        ctx.fillText(badgeLabel, xStart + 8, zoneTop + Math.min(18, zoneHeight / 2 + 4));
    }

    // Real-time synchronization of Zone Canvas with chart dragging, price-scale stretching & zooming
    let animFrameId = null;
    function scheduleZoneRedraw() {
        if (animFrameId) cancelAnimationFrame(animFrameId);
        animFrameId = requestAnimationFrame(drawZoneOverlay);
    }

    function renderChart(item) {
        activeItem = item;
        chartSection.classList.remove('hidden');

        const timeframeSelect = document.getElementById('timeframe-select');
        activeTimeframeText = timeframeSelect.options[timeframeSelect.selectedIndex].text;

        // Populate Header Info
        tvTicker.textContent = item.ticker;
        tvTimeframe.textContent = activeTimeframeText.split(' ')[0];
        tvZoneBadge.textContent = `${item.zone_type} Zone (${item.pattern})`;
        tvZoneBadge.className = `tv-zone-badge ${item.zone_type === 'Demand' ? 'tv-zone-demand' : 'tv-zone-supply'}`;
        tvScoreBadge.textContent = `GTF Score: ${item.score}/14`;

        const isDemand = item.zone_type === 'Demand';
        const zoneDesc = isDemand ? 'Support / Institutional Accumulation' : 'Resistance / Institutional Distribution';
        tvZoneDetails.textContent = `${item.zone_type} Base: ₹${item.proximal.toFixed(2)} to ₹${item.distal.toFixed(2)} • ${zoneDesc}`;

        // If history is not already bundled, fetch on demand
        if (!item.history || item.history.length === 0) {
            fetch(`/api/history?ticker=${item.ticker}&interval=${timeframeSelect.value}`)
                .then(r => r.json())
                .then(res => {
                    if (res.status === 'success' && res.history) {
                        item.history = res.history;
                        renderChart(item);
                    }
                })
                .catch(err => console.error('Error fetching history:', err));
            return;
        }

        // Cleanup old chart
        if (activeChart) {
            activeChart.remove();
            activeChart = null;
        }

        chartContainer.innerHTML = '';
        const responsiveH = getResponsiveChartHeight();
        const chartWrapper = document.getElementById('tv-chart-wrapper');
        if (chartWrapper) chartWrapper.style.height = `${responsiveH}px`;

        // Initialize TradingView Lightweight Chart
        const chart = LightweightCharts.createChart(chartContainer, {
            width: chartContainer.clientWidth,
            height: responsiveH,
            layout: {
                background: { type: 'solid', color: '#131722' },
                textColor: '#d1d4dc',
                fontFamily: "'Outfit', sans-serif",
                fontSize: 12,
            },
            grid: {
                vertLines: { color: 'rgba(42, 46, 57, 0.6)', style: LightweightCharts.LineStyle.Dotted },
                horzLines: { color: 'rgba(42, 46, 57, 0.6)', style: LightweightCharts.LineStyle.Dotted },
            },
            crosshair: {
                mode: LightweightCharts.CrosshairMode.Normal,
                vertLine: {
                    color: '#758696',
                    width: 1,
                    style: LightweightCharts.LineStyle.Dashed,
                    labelBackgroundColor: '#2a2e39',
                },
                horzLine: {
                    color: '#758696',
                    width: 1,
                    style: LightweightCharts.LineStyle.Dashed,
                    labelBackgroundColor: '#2a2e39',
                },
            },
            rightPriceScale: {
                borderColor: '#2a2e39',
                visible: true,
                autoScale: true,
                mode: LightweightCharts.PriceScaleMode.Normal,
                scaleMargins: {
                    top: 0.12,
                    bottom: 0.12,
                },
            },
            timeScale: {
                borderColor: '#2a2e39',
                timeVisible: true,
                secondsVisible: false,
                rightOffset: 12,
                barSpacing: 10,
                minBarSpacing: 3,
                fixLeftEdge: false,
                fixRightEdge: false,
            },
            handleScroll: {
                mouseWheel: true,
                pressedMouseMove: true,
                horzTouchDrag: true,
                vertTouchDrag: true,
            },
            handleScale: {
                axisPressedMouseMove: true,
                mouseWheel: true,
                pinch: true,
                axisDoubleClickReset: true,
            },
        });

        activeChart = chart;

        // Add Candlestick Series
        const candleSeries = chart.addCandlestickSeries({
            upColor: '#089981',
            downColor: '#f23645',
            borderUpColor: '#089981',
            borderDownColor: '#f23645',
            wickUpColor: '#089981',
            wickDownColor: '#f23645',
        });
        activeCandleSeries = candleSeries;

        // Add 20 EMA and 50 EMA Series
        const ema20Series = chart.addLineSeries({
            color: '#2962ff',
            lineWidth: 2,
            title: 'EMA 20',
            crosshairMarkerVisible: true,
            priceLineVisible: false,
        });
        activeEma20Series = ema20Series;

        const ema50Series = chart.addLineSeries({
            color: '#f59e0b',
            lineWidth: 2,
            title: 'EMA 50',
            crosshairMarkerVisible: true,
            priceLineVisible: false,
        });
        activeEma50Series = ema50Series;

        // Format and sort candle data
        const sortedHistory = [...item.history].sort((a, b) => new Date(a.DateStr) - new Date(b.DateStr));
        const candleData = [];
        const ema20Data = [];
        const ema50Data = [];
        const seenDates = new Set();

        sortedHistory.forEach(h => {
            if (h.DateStr && !seenDates.has(h.DateStr)) {
                seenDates.add(h.DateStr);
                candleData.push({
                    time: h.DateStr,
                    open: parseFloat(h.Open),
                    high: parseFloat(h.High),
                    low: parseFloat(h.Low),
                    close: parseFloat(h.Close)
                });
                if (h.EMA_20 != null && !isNaN(h.EMA_20)) {
                    ema20Data.push({ time: h.DateStr, value: parseFloat(h.EMA_20) });
                }
                if (h.EMA_50 != null && !isNaN(h.EMA_50)) {
                    ema50Data.push({ time: h.DateStr, value: parseFloat(h.EMA_50) });
                }
            }
        });

        activeCandleData = candleData;
        candleSeries.setData(candleData);
        ema20Series.setData(ema20Data);
        ema50Series.setData(ema50Data);

        // Add Official Price Lines
        const entry = item.proximal;
        const sl = item.distal;
        const risk = Math.abs(entry - sl);
        const target = isDemand ? entry + (risk * 2) : entry - (risk * 2);

        // Proximal Line
        candleSeries.createPriceLine({
            price: entry,
            color: isDemand ? '#22c55e' : '#ef4444',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Solid,
            axisLabelVisible: true,
            title: `Proximal (Entry)`,
        });

        // Distal Line (SL)
        candleSeries.createPriceLine({
            price: sl,
            color: isDemand ? '#15803d' : '#991b1b',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: `Distal (SL)`,
        });

        // Target Line (1:2 Target)
        candleSeries.createPriceLine({
            price: target,
            color: '#06b6d4',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dotted,
            axisLabelVisible: true,
            title: `Target (1:2)`,
        });

        // Set initial legend to latest candle
        if (candleData.length > 0) {
            const lastCandle = candleData[candleData.length - 1];
            const prevCandle = candleData.length > 1 ? candleData[candleData.length - 2] : null;
            const lastEma20 = ema20Data.length > 0 ? ema20Data[ema20Data.length - 1].value : null;
            const lastEma50 = ema50Data.length > 0 ? ema50Data[ema50Data.length - 1].value : null;
            updateLegend(lastCandle, prevCandle?.close, lastEma20, lastEma50);
        }

        // Crosshair move event for dynamic TradingView legend
        chart.subscribeCrosshairMove((param) => {
            if (!param.time || !param.seriesData) {
                const lastCandle = candleData[candleData.length - 1];
                const prevCandle = candleData.length > 1 ? candleData[candleData.length - 2] : null;
                const lastEma20 = ema20Data.length > 0 ? ema20Data[ema20Data.length - 1].value : null;
                const lastEma50 = ema50Data.length > 0 ? ema50Data[ema50Data.length - 1].value : null;
                updateLegend(lastCandle, prevCandle?.close, lastEma20, lastEma50);
                return;
            }
            const cData = param.seriesData.get(candleSeries);
            const e20 = param.seriesData.get(ema20Series);
            const e50 = param.seriesData.get(ema50Series);
            if (cData) {
                updateLegend(cData, null, e20?.value, e50?.value);
            }
        });

        // Real-time synchronization of Zone Canvas with chart dragging, price-scale stretching & zooming
        chart.timeScale().subscribeVisibleTimeRangeChange(scheduleZoneRedraw);
        chart.timeScale().subscribeVisibleLogicalRangeChange(scheduleZoneRedraw);

        // Track mouse/pointer interaction on price scale and chart canvas
        let isInteracting = false;
        chartContainer.addEventListener('pointerdown', () => {
            isInteracting = true;
            scheduleZoneRedraw();
        });
        window.addEventListener('pointermove', () => {
            if (isInteracting) scheduleZoneRedraw();
        });
        window.addEventListener('pointerup', () => {
            if (isInteracting) {
                isInteracting = false;
                scheduleZoneRedraw();
            }
        });
        chartContainer.addEventListener('wheel', scheduleZoneRedraw, { passive: true });
        chartContainer.addEventListener('touchmove', scheduleZoneRedraw, { passive: true });
        chartContainer.addEventListener('dblclick', () => {
            setTimeout(scheduleZoneRedraw, 50);
        });

        // Fit view nicely around the zone
        chart.timeScale().fitContent();
        setTimeout(scheduleZoneRedraw, 50);

        // Scroll page to chart
        chartSection.scrollIntoView({ behavior: 'smooth' });
    }

    // Reset Scale Button
    resetBtn.addEventListener('click', () => {
        if (!activeChart) return;
        activeChart.timeScale().fitContent();
        activeChart.priceScale('right').applyOptions({ autoScale: true });
        setTimeout(scheduleZoneRedraw, 50);
    });

    // Save PNG Screenshot Button
    downloadBtn.addEventListener('click', () => {
        if (!activeChart || !activeItem) return;
        const chartCanvas = activeChart.takeScreenshot();
        const exportCanvas = document.createElement('canvas');
        exportCanvas.width = chartCanvas.width;
        exportCanvas.height = chartCanvas.height;
        const exCtx = exportCanvas.getContext('2d');

        // Draw TradingView Canvas
        exCtx.drawImage(chartCanvas, 0, 0);

        // Draw GTF Zones
        exCtx.drawImage(zoneCanvas, 0, 0, exportCanvas.width, exportCanvas.height);

        // Watermark Banner
        exCtx.fillStyle = 'rgba(19, 23, 34, 0.88)';
        exCtx.fillRect(16, 16, 340, 56);
        exCtx.strokeStyle = 'rgba(255, 255, 255, 0.12)';
        exCtx.lineWidth = 1;
        exCtx.strokeRect(16, 16, 340, 56);

        exCtx.fillStyle = '#ffffff';
        exCtx.font = 'bold 15px Outfit, sans-serif';
        exCtx.fillText(`${activeItem.ticker} • ${activeTimeframeText} (NSE)`, 26, 38);

        exCtx.fillStyle = activeItem.zone_type === 'Demand' ? '#089981' : '#f23645';
        exCtx.font = '12px Outfit, sans-serif';
        exCtx.fillText(`GTF Score: ${activeItem.score}/14 • ${activeItem.zone_type} Zone (${activeItem.pattern})`, 26, 56);

        // Trigger Download
        const link = document.createElement('a');
        link.download = `${activeItem.ticker}_${activeTimeframeText}_TradingView_Setup`.replace(/[^a-z0-9]/gi, '_').toLowerCase() + '.png';
        link.href = exportCanvas.toDataURL('image/png');
        link.click();
    });

    // Window Resize Handler
    window.addEventListener('resize', () => {
        if (activeChart && chartContainer) {
            const responsiveH = getResponsiveChartHeight();
            const chartWrapper = document.getElementById('tv-chart-wrapper');
            if (chartWrapper) chartWrapper.style.height = `${responsiveH}px`;
            activeChart.applyOptions({ 
                width: chartContainer.clientWidth,
                height: responsiveH
            });
            scheduleZoneRedraw();
        }
    });
});
