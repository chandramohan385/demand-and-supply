import os
import yfinance as yf
import pandas as pd
import numpy as np

def fetch_data(ticker, interval="1d", period="1y"):
    try:
        if not ticker.endswith('.NS') and not ticker.startswith('^'):
            ticker += '.NS'
        df = yf.download(ticker, period=period, interval=interval, progress=False)
        if df.empty:
            return None
        # Handle MultiIndex columns that yfinance sometimes returns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df = df.reset_index()
        return df
    except Exception as e:
        print(f"Error fetching data for {ticker}: {e}")
        return None

def analyze_gtf(df, interval="1d", zone_type_needed=None, sector_uptrend=False, sector_downtrend=False):
    if df is None or len(df) < 200:
        return None

    # Date handling
    date_col = 'Date' if 'Date' in df.columns else 'Datetime'
    if date_col not in df.columns:
        return None

    # Calculate Candle Attributes based on GTF rules
    df['Total_Length'] = abs(df['High'] - df['Low'])
    df['Body_Length'] = abs(df['Close'] - df['Open'])
    df['Avg_Length'] = df['Total_Length'].rolling(window=20).mean()
    
    # An Exciting Candle (ERC) must have a large body (>60% of range) AND not be a microscopic candle
    df['Is_Exciting'] = (df['Body_Length'] > (df['Total_Length'] * 0.60)) & (df['Total_Length'] > (df['Avg_Length'] * 0.5))
    df['Is_Base'] = df['Body_Length'] <= (df['Total_Length'] * 0.50)
    
    # EMAs for Trend Confirmation & Score Booster
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    zones = []
    
    # Reverse loop to find the most recent GTF zone
    # We start from len(df) - 2 to completely IGNORE the current ongoing/incomplete candle 
    # (e.g., an incomplete June Monthly candle or an ongoing daily candle)
    for i in range(len(df) - 2, 6, -1):
        if not df['Is_Exciting'].iloc[i]:
            continue
            
        leg_out_candle = df.iloc[i]
        
        # Count all consecutive base candles backwards
        base_count = 0
        j = i - 1
        while j >= 0 and df['Is_Base'].iloc[j]:
            base_count += 1
            j -= 1
                
        # GTF Rule: Max 5 base candles permitted. If more, it's a chop zone, reject it.
        if base_count == 0 or base_count > 5:
            continue
            
        # Leg in candle
        leg_in_idx = i - base_count - 1
        if leg_in_idx < 0 or not df['Is_Exciting'].iloc[leg_in_idx]:
            continue
            
        leg_in_candle = df.iloc[leg_in_idx]
        base_candles = df.iloc[i-base_count:i]
        
        # Determine direction
        leg_in_dir = "Rally" if leg_in_candle['Close'] > leg_in_candle['Open'] else "Drop"
        leg_out_dir = "Rally" if leg_out_candle['Close'] > leg_out_candle['Open'] else "Drop"
        
        pattern = f"{leg_in_dir}-Base-{leg_out_dir}"
        zone_type = "Demand" if leg_out_dir == "Rally" else "Supply"
        
        if zone_type_needed and zone_type != zone_type_needed:
            continue
            
        # Zone Marking (Proximal & Distal)
        if zone_type == "Demand":
            proximal = max(base_candles['Open'].max(), base_candles['Close'].max())
            distal = base_candles['Low'].min()
        else:
            proximal = min(base_candles['Open'].min(), base_candles['Close'].min())
            distal = base_candles['High'].max()
            
        # Freshness Check (Count penetrations and violdations)
        violated = False
        tested_count = 0
        subsequent_candles = df.iloc[i+1:]
        if len(subsequent_candles) > 0:
            if zone_type == "Demand":
                if subsequent_candles['Low'].min() < distal:
                    violated = True
                else:
                    # Count distinct candles touching proximal
                    tested_count = len(subsequent_candles[subsequent_candles['Low'] <= proximal])
            else:
                if subsequent_candles['High'].max() > distal:
                    violated = True
                else:
                    tested_count = len(subsequent_candles[subsequent_candles['High'] >= proximal])
                    
        if violated or tested_count >= 3:
            continue # Skip violated zones or zones tested 3+ times
            
        # Strength of Zone
        next_candle_exciting = False
        if i + 1 < len(df) and df['Is_Exciting'].iloc[i+1]:
            if (zone_type == "Demand" and df['Close'].iloc[i+1] > df['Open'].iloc[i+1]) or \
               (zone_type == "Supply" and df['Close'].iloc[i+1] < df['Open'].iloc[i+1]):
                next_candle_exciting = True
                
        # Check for gap between last base candle and leg-out
        last_base_candle = base_candles.iloc[-1]
        has_gap = False
        if zone_type == "Demand" and leg_out_candle['Open'] > last_base_candle['Close']:
            has_gap = True
        elif zone_type == "Supply" and leg_out_candle['Open'] < last_base_candle['Close']:
            has_gap = True

        first_base_candle = df.iloc[i - base_count]

        zones.append({
            'pattern': pattern,
            'zone_type': zone_type,
            'proximal': proximal,
            'distal': distal,
            'date_found': leg_out_candle[date_col],
            'start_date': first_base_candle[date_col],
            'base_count': base_count,
            'has_gap': has_gap,
            'tested_count': tested_count,
            'next_candle_exciting': next_candle_exciting,
            'idx': i
        })
        break # Just get the latest one

    if not zones:
        return None
        
    latest_zone = zones[0]
    score = 0
    current_price = df['Close'].iloc[-1]
    
    # Score Booster: Trend Confluence
    uptrend = current_price > df['EMA_20'].iloc[-1] and df['EMA_20'].iloc[-1] > df['EMA_50'].iloc[-1]
    downtrend = current_price < df['EMA_20'].iloc[-1] and df['EMA_20'].iloc[-1] < df['EMA_50'].iloc[-1]
    
    trend_status = "Sideways"
    if uptrend:
        trend_status = "Uptrend"
    elif downtrend:
        trend_status = "Downtrend"
    
    # 1. Freshness (Max 3)
    fresh_score = 0
    if latest_zone['tested_count'] == 0:
        fresh_score = 3
    elif latest_zone['tested_count'] == 1:
        fresh_score = 1
        
    # 2. Strength of the zone (Max 3)
    strength_score = 1 # One exciting
    if latest_zone['next_candle_exciting']:
        strength_score = 3
    elif latest_zone['has_gap']:
        strength_score = 2
        
    # 3. Base Size (Max 3)
    base_score = 0
    if latest_zone['base_count'] <= 3:
        base_score = 3
    elif latest_zone['base_count'] <= 5:
        base_score = 2
        
    # 4. Golden / Death Crossover (Max 2)
    crossover_score = 0
    for j in range(len(df)-10, len(df)):
        if j-1 < 0: continue
        if latest_zone['zone_type'] == "Demand":
            if df['EMA_20'].iloc[j] > df['EMA_50'].iloc[j] and df['EMA_20'].iloc[j-1] <= df['EMA_50'].iloc[j-1]:
                crossover_score = 2
                break
        else:
            if df['EMA_20'].iloc[j] < df['EMA_50'].iloc[j] and df['EMA_20'].iloc[j-1] >= df['EMA_50'].iloc[j-1]:
                crossover_score = 2
                break
                
    # 5. EMA at Execution (Max 1)
    ema_exec_score = 0
    if latest_zone['zone_type'] == "Demand" and current_price > df['EMA_20'].iloc[-1]:
        ema_exec_score = 1
    elif latest_zone['zone_type'] == "Supply" and current_price < df['EMA_20'].iloc[-1]:
        ema_exec_score = 1
        
    # 6. Sector Analysis (Max 2)
    sector_score = 0
    if latest_zone['zone_type'] == "Demand" and sector_uptrend:
        sector_score = 2
    elif latest_zone['zone_type'] == "Supply" and sector_downtrend:
        sector_score = 2
        
    score = fresh_score + strength_score + base_score + crossover_score + ema_exec_score + sector_score
    
    score_breakdown = {
        'Freshness (3)': fresh_score,
        'Strength (3)': strength_score,
        'Base Size (3)': base_score,
        'Crossover (2)': crossover_score,
        'EMA Position (1)': ema_exec_score,
        'Sector Support (2)': sector_score
    }
    
    # Prepare history for charting (provide 300 candles for rich TradingView navigation)
    df['DateStr'] = df[date_col].dt.strftime('%Y-%m-%d')
    history = df[['DateStr', 'Open', 'High', 'Low', 'Close', 'EMA_20', 'EMA_50']].tail(300).to_dict(orient='records')
        
    tf_map = {
        "1d": "Daily (1D)",
        "1wk": "Weekly (1W)",
        "1mo": "Monthly (1M)",
        "3mo": "Quarterly (3M)"
    }

    return {
        'current_price': float(current_price),
        'zone_type': latest_zone['zone_type'],
        'pattern': latest_zone['pattern'],
        'proximal': round(float(latest_zone['proximal']), 2),
        'distal': round(float(latest_zone['distal']), 2),
        'score': score,
        'score_breakdown': score_breakdown,
        'trend': trend_status,
        'ema_20': round(float(df['EMA_20'].iloc[-1]), 2),
        'ema_50': round(float(df['EMA_50'].iloc[-1]), 2),
        'ema_200': round(float(df['EMA_200'].iloc[-1]), 2),
        'date_found': str(latest_zone['date_found']).split()[0],
        'start_date': str(latest_zone['start_date']).split()[0],
        'timeframe': tf_map.get(interval, interval),
        'history': history
    }

def scan_tickers(tickers, interval="1d", sector_map=None):
    period = "2y"
    if interval == "1wk":
        period = "5y"
    elif interval in ["1mo", "3mo"]:
        period = "max"
        
    htf_map = {
        "1d": ("1wk", "5y"),
        "1wk": ("1mo", "max"),
        "1mo": ("3mo", "max"),
        "3mo": None
    }
        
    results = []
    for t in tickers:
        df = fetch_data(t, interval, period)
        
        # Fetch Sector Data
        sector_up = False
        sector_down = False
        if sector_map and t in sector_map:
            sector_idx = sector_map[t]
            sector_df = fetch_data(sector_idx, interval, "1y")
            if sector_df is not None and len(sector_df) >= 50:
                s_ema20 = sector_df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                s_ema50 = sector_df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                s_price = sector_df['Close'].iloc[-1]
                sector_up = s_price > s_ema20 and s_ema20 > s_ema50
                sector_down = s_price < s_ema20 and s_ema20 < s_ema50
        
        analysis = analyze_gtf(df, interval, sector_uptrend=sector_up, sector_downtrend=sector_down)
        
        if analysis:
            # Curve Analysis: Check if it hits opposing Higher Time Frame (HTF) zone
            htf_info = htf_map.get(interval)
            if htf_info:
                htf_interval, htf_period = htf_info
                htf_df = fetch_data(t, htf_interval, htf_period)
                
                opposing_type = "Supply" if analysis['zone_type'] == "Demand" else "Demand"
                htf_opposing_analysis = analyze_gtf(htf_df, htf_interval, zone_type_needed=opposing_type)
                
                if htf_opposing_analysis:
                    current_price = analysis['current_price']
                    htf_proximal = htf_opposing_analysis['proximal']
                    
                    if opposing_type == "Supply":
                        # If finding a Demand zone, check we are not hitting HTF Supply
                        if current_price >= htf_proximal:
                            continue # Hit HTF Supply! Discard trade.
                    else:
                        # If finding a Supply zone, check we are not hitting HTF Demand
                        if current_price <= htf_proximal:
                            continue # Hit HTF Demand! Discard trade.

            analysis['ticker'] = t
            results.append(analysis)
    
    # Sort by score (highest first)
    results = sorted(results, key=lambda x: x['score'], reverse=True)
    return results
