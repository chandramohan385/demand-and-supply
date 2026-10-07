document.addEventListener('DOMContentLoaded', () => {
    const scanBtn = document.getElementById('scan-btn');
    const loader = document.getElementById('loader');
    const table = document.getElementById('results-table');
    const tbody = document.getElementById('results-body');

    scanBtn.addEventListener('click', async () => {
        // UI Updates
        scanBtn.disabled = true;
        scanBtn.querySelector('.btn-text').innerText = 'Scanning...';
        loader.classList.remove('hidden');
        table.classList.add('hidden');
        tbody.innerHTML = '';

        const interval = document.getElementById('timeframe-select').value;
        const category = document.getElementById('category-select').value;
        try {
            const response = await fetch(`/api/scan?interval=${interval}&category=${category}`);
            const result = await response.json();

            if (result.status === 'success') {
                populateTable(result.data);
            } else {
                alert('Error scanning stocks: ' + result.message);
            }
        } catch (error) {
            console.error('Fetch error:', error);
            alert('Failed to connect to the scanning engine.');
        } finally {
            // UI Reset
            scanBtn.disabled = false;
            scanBtn.querySelector('.btn-text').innerText = 'Run Market Scan';
            loader.classList.add('hidden');
        }
    });

    // Global variable to store raw data for charting
    let globalData = [];

    function populateTable(data) {
        globalData = data;
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align: center;">No high-probability setups found right now.</td></tr>';
            table.classList.remove('hidden');
            return;
        }

        data.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.style.cursor = 'pointer';
            // Stagger animation delay
            tr.style.animation = `fadeInUp 0.3s ease-out ${index * 0.1}s forwards`;
            tr.style.opacity = '0'; // Start invisible
            
            const zoneClass = item.zone_type === 'Demand' ? 'zone-demand' : 'zone-supply';
            
            tr.innerHTML = `
                <td class="ticker-name">${item.ticker}</td>
                <td>₹${item.current_price.toFixed(2)}</td>
                <td class="${zoneClass}">${item.zone_type}</td>
                <td><span class="badge">${item.pattern}</span></td>
                <td>₹${item.proximal.toFixed(2)}</td>
                <td>₹${item.distal.toFixed(2)}</td>
                <td style="font-size: 0.9rem; font-weight: bold; color: ${item.trend === 'Uptrend' ? '#2ea043' : item.trend === 'Downtrend' ? '#da3633' : '#8b949e'};">${item.trend}</td>
                <td class="score-high">
                    <div class="tooltip-container">
                        ${item.score}/14
                        <div class="tooltip-text">
                            <div style="border-bottom: 1px solid rgba(255,255,255,0.1); margin-bottom: 5px; padding-bottom: 5px; text-align: center; font-weight: bold;">Score Breakdown</div>
                            <div class="tooltip-row"><span>Freshness:</span> <span>+${item.score_breakdown['Freshness (3)']}</span></div>
                            <div class="tooltip-row"><span>Strength:</span> <span>+${item.score_breakdown['Strength (3)']}</span></div>
                            <div class="tooltip-row"><span>Base Size:</span> <span>+${item.score_breakdown['Base Size (3)']}</span></div>
                            <div class="tooltip-row"><span>20/50 Crossover:</span> <span>+${item.score_breakdown['Crossover (2)']}</span></div>
                            <div class="tooltip-row"><span>EMA Support:</span> <span>+${item.score_breakdown['EMA Position (1)']}</span></div>
                            <div class="tooltip-row"><span>Sector Alignment:</span> <span>+${item.score_breakdown['Sector Support (2)']}</span></div>
                        </div>
                    </div>
                </td>
            `;
            
            // Add click listener to plot chart
            tr.addEventListener('click', () => {
                renderChart(item);
            });
            
            tbody.appendChild(tr);
        });

        table.classList.remove('hidden');
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

        // 1. Draw Institutional GTF Base Zone
        ctx.fillStyle = isDemand ? 'rgba(168, 85, 247, 0.22)' : 'rgba(236, 72, 153, 0.22)';
        ctx.fillRect(xStart, zoneTop, boxWidth, zoneHeight);
        ctx.strokeStyle = isDemand ? 'rgba(168, 85, 247, 0.85)' : 'rgba(236, 72, 153, 0.85)';
        ctx.lineWidth = 1.5;
        ctx.strokeRect(xStart, zoneTop, boxWidth, zoneHeight);

        // 2. Draw Target 1:2 Zone (Reward Box)
        if (yTarget !== null) {
            const targetTop = Math.min(yEntry, yTarget);
            const targetHeight = Math.max(2, Math.abs(yEntry - yTarget));
            ctx.fillStyle = 'rgba(8, 153, 129, 0.12)';
            ctx.fillRect(xStart, targetTop, boxWidth, targetHeight);
            ctx.strokeStyle = 'rgba(8, 153, 129, 0.5)';
            ctx.lineWidth = 1;
            ctx.setLineDash([4, 4]);
            ctx.strokeRect(xStart, targetTop, boxWidth, targetHeight);
            ctx.setLineDash([]);
        }

        // 3. Draw Zone Labels
        ctx.fillStyle = '#ffffff';
        ctx.font = '600 11px Outfit, sans-serif';
        const badgeLabel = `${activeItem.zone_type.toUpperCase()} ZONE (${activeItem.pattern})`;
        ctx.fillText(badgeLabel, xStart + 8, zoneTop + Math.min(18, zoneHeight / 2 + 4));
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

        // Cleanup old chart
        if (activeChart) {
            activeChart.remove();
            activeChart = null;
        }

        chartContainer.innerHTML = '';

        // Initialize TradingView Lightweight Chart
        const chart = LightweightCharts.createChart(chartContainer, {
            width: chartContainer.clientWidth,
            height: 560,
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
            color: isDemand ? '#8b5cf6' : '#ec4899',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Solid,
            axisLabelVisible: true,
            title: `Proximal (Entry)`,
        });

        // Distal Line (SL)
        candleSeries.createPriceLine({
            price: sl,
            color: isDemand ? '#a78bfa' : '#f472b6',
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Dashed,
            axisLabelVisible: true,
            title: `Distal (SL)`,
        });

        // Target Line (1:2 Target)
        candleSeries.createPriceLine({
            price: target,
            color: '#10b981',
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

        // Sync Zone Canvas with chart scrolling/zooming
        chart.timeScale().subscribeVisibleTimeRangeChange(drawZoneOverlay);
        chart.timeScale().subscribeVisibleLogicalRangeChange(drawZoneOverlay);

        // Fit view nicely around the zone
        chart.timeScale().fitContent();
        setTimeout(drawZoneOverlay, 50);

        // Scroll page to chart
        chartSection.scrollIntoView({ behavior: 'smooth' });
    }

    // Reset Scale Button
    resetBtn.addEventListener('click', () => {
        if (!activeChart) return;
        activeChart.timeScale().fitContent();
        activeChart.priceScale('right').applyOptions({ autoScale: true });
        setTimeout(drawZoneOverlay, 50);
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
            activeChart.applyOptions({ width: chartContainer.clientWidth });
            drawZoneOverlay();
        }
    });
});
