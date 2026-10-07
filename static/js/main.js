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
    const chartTitle = document.getElementById('chart-title');

    closeChartBtn.addEventListener('click', () => {
        chartSection.classList.add('hidden');
    });

    function renderChart(item) {
        chartSection.classList.remove('hidden');
        
        // Clear description of what the user is looking at
        const zoneDesc = item.zone_type === 'Demand' ? 'Support / Buy Zone' : 'Resistance / Sell Zone';
        const timeframeText = document.getElementById('timeframe-select').options[document.getElementById('timeframe-select').selectedIndex].text;
        
        chartTitle.innerHTML = `<span>${item.ticker}</span> - ${timeframeText} <br> <span style="font-size: 1rem; font-weight: normal; color: #8b949e;">Showing: ${item.zone_type} Zone (${item.pattern}) &bull; ${zoneDesc} &bull; Box drawn from Proximal to Distal Line</span>`;

        const history = item.history;
        const dates = history.map(d => d.DateStr);
        const opens = history.map(d => d.Open);
        const highs = history.map(d => d.High);
        const lows = history.map(d => d.Low);
        const closes = history.map(d => d.Close);
        const ema20 = history.map(d => d.EMA_20);
        const ema50 = history.map(d => d.EMA_50);

        const trace1 = {
            x: dates,
            close: closes,
            decreasing: {line: {color: '#f44336'}, fillcolor: '#f44336'}, // Red from image
            high: highs,
            increasing: {line: {color: '#00897b'}, fillcolor: '#00897b'}, // Teal from image
            line: {color: 'rgba(31,119,180,1)'},
            low: lows,
            open: opens,
            name: 'Candlesticks',
            type: 'candlestick',
            xaxis: 'x',
            yaxis: 'y'
        };

        const trace2 = {
            x: dates,
            y: ema20,
            type: 'scatter',
            mode: 'lines',
            name: '20 EMA (Trend)',
            line: {color: '#3b82f6', width: 2}
        };

        const trace3 = {
            x: dates,
            y: ema50,
            type: 'scatter',
            mode: 'lines',
            name: '50 EMA (Trend)',
            line: {color: '#f59e0b', width: 2}
        };

        const data = [trace1, trace2, trace3];

        // Calculate Risk/Reward values (1:2 Target)
        const isDemand = item.zone_type === 'Demand';
        const entry = item.proximal;
        const sl = item.distal;
        const risk = Math.abs(entry - sl);
        const target = isDemand ? entry + (risk * 2) : entry - (risk * 2);

        // Styling based on the user's TradingView screenshot
        const zoneFillColor = isDemand ? 'rgba(180, 130, 210, 0.2)' : 'rgba(180, 130, 210, 0.2)'; // Purple
        const zoneLineColor = 'rgba(130, 50, 180, 0.8)'; // Darker purple border
        
        const rewardFillColor = 'rgba(80, 200, 200, 0.25)'; // Teal Target Box
        const riskFillColor = 'rgba(250, 120, 120, 0.25)'; // Light Red Stop Loss Box

        // We extend the boxes visually into the future (add 30 days)
        const startDate = item.start_date; // Starts exactly at the first base candle
        const lastDateObj = new Date(dates[dates.length - 1]);
        lastDateObj.setDate(lastDateObj.getDate() + 30);
        const futureDate = lastDateObj.toISOString().split('T')[0];

        // Find the start date in the history array to add padding to the left
        const startIdx = dates.indexOf(item.start_date);
        // Add 15 candles of padding to the left so the drop into the zone is visible
        const paddingIdx = Math.max(0, startIdx - 15);
        const viewStartDate = startIdx !== -1 ? dates[paddingIdx] : dates[dates.length - 60] || dates[0];

        const layout = {
            dragmode: 'pan',
            margin: { r: 60, t: 40, b: 40, l: 10 },
            showlegend: true,
            legend: {
                orientation: "h", yanchor: "bottom", y: 1.02, xanchor: "right", x: 1, font: { color: '#8b949e' }
            },
            xaxis: {
                autorange: false, 
                domain: [0, 1],
                range: [viewStartDate, futureDate],
                rangeslider: {visible: false}, type: 'date', gridcolor: 'rgba(255,255,255,0.05)',
                fixedrange: false,
                showspikes: true, spikemode: 'across', spikethickness: 1, spikedash: 'dot', spikecolor: '#8b949e'
            },
            yaxis: {
                autorange: false, 
                domain: [0, 1], 
                type: 'linear', 
                gridcolor: 'rgba(255,255,255,0.05)',
                fixedrange: false,
                side: 'right',
                showspikes: true, spikemode: 'across', spikethickness: 1, spikedash: 'dot', spikecolor: '#8b949e',
                range: [
                    Math.min(...item.history.map(h => h.Low)) * 0.95,
                    Math.max(...item.history.map(h => h.High)) * 1.05
                ]
            },
            hovermode: 'x unified',
            plot_bgcolor: '#0a0c10',
            paper_bgcolor: '#0a0c10',
            font: { color: '#e6edf3' },
            shapes: [
                // 1. The Purple GTF Zone (Base Candle Range)
                {
                    type: 'rect', xref: 'x', yref: 'y',
                    x0: startDate, y0: entry, x1: futureDate, y1: sl,
                    fillcolor: zoneFillColor, line: { color: zoneLineColor, width: 2 }
                },
                // 2. The Target (Reward) Box - Teal
                {
                    type: 'rect', xref: 'x', yref: 'y',
                    x0: startDate, y0: entry, x1: futureDate, y1: target,
                    fillcolor: rewardFillColor, line: { width: 0 }
                },
                // 3. The Stop Loss (Risk) Box - Red
                {
                    type: 'rect', xref: 'x', yref: 'y',
                    x0: startDate, y0: entry, x1: futureDate, y1: sl,
                    fillcolor: riskFillColor, line: { width: 0 }
                },
                // 4. Current Price Line (Dotted)
                {
                    type: 'line', xref: 'paper', yref: 'y',
                    x0: 0, x1: 1, y0: item.current_price, y1: item.current_price,
                    line: { color: 'rgba(255, 255, 255, 0.4)', width: 1, dash: 'dot' }
                }
            ],
            annotations: [
                // "Demand zone" Text inside the purple box
                {
                    x: startDate, y: (entry + sl) / 2,
                    xref: 'x', yref: 'y',
                    text: isDemand ? 'Demand zone' : 'Supply zone',
                    showarrow: false,
                    font: { color: '#e6edf3', size: 13, family: 'Outfit, sans-serif' },
                    xanchor: 'left', xshift: 10
                },
                // Current Price Label on Y-axis
                {
                    x: 1, y: item.current_price,
                    xref: 'paper', yref: 'y',
                    text: `  ₹${item.current_price.toFixed(2)}`,
                    showarrow: false,
                    font: { color: '#ffffff', size: 12, family: 'Outfit, sans-serif' },
                    xanchor: 'left', bgcolor: 'rgba(0,0,0,0.6)', borderpad: 3
                }
            ]
        };

        const config = {
            responsive: true, 
            scrollZoom: true,
            displayModeBar: true,
            toImageButtonOptions: {
                format: 'png',
                filename: `${item.ticker}_${timeframeText}_GTF_Setup`.replace(/[^a-z0-9]/gi, '_').toLowerCase(),
                height: 800,
                width: 1400,
                scale: 1.5
            }
        };

        Plotly.newPlot('plotly-chart', data, layout, config);
        
        // Scroll to chart
        chartSection.scrollIntoView({ behavior: 'smooth' });
    }
});
