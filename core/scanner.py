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

def fetch_batch_data(tickers, interval="1d", period="2y"):
    if not tickers:
        return {}
    
    sym_map = {}
    tickers_ns = []
    for t in tickers:
        t_clean = t.strip()
        t_ns = f"{t_clean}.NS" if not t_clean.endswith('.NS') and not t_clean.startswith('^') else t_clean
        sym_map[t_ns] = t_clean
        tickers_ns.append(t_ns)

    if len(tickers_ns) == 1:
        df = fetch_data(tickers[0], interval=interval, period=period)
        return {tickers[0]: df} if df is not None else {}

    res_dict = {}
    chunk_size = 100
    for i in range(0, len(tickers_ns), chunk_size):
        chunk = tickers_ns[i:i + chunk_size]
        try:
            batch_df = yf.download(chunk, period=period, interval=interval, group_by='ticker', progress=False, threads=True)
            if batch_df.empty:
                continue
            for t_ns in chunk:
                raw_sym = sym_map.get(t_ns, t_ns)
                try:
                    if isinstance(batch_df.columns, pd.MultiIndex):
                        if t_ns in batch_df.columns.levels[0]:
                            sub = batch_df[t_ns].dropna(how='all').copy()
                            if not sub.empty and len(sub) >= 20:
                                if isinstance(sub.columns, pd.MultiIndex):
                                    sub.columns = sub.columns.get_level_values(0)
                                sub = sub.reset_index()
                                res_dict[raw_sym] = sub
                    else:
                        df = batch_df.reset_index()
                        res_dict[raw_sym] = df
                except Exception:
                    continue
        except Exception as e:
            print(f"Error fetching batch chunk: {e}")
            continue

    return res_dict

def analyze_gtf(df, interval="1d", zone_type_needed=None, sector_uptrend=False, sector_downtrend=False):
    if df is None or len(df) < 30:
        return None

    # Date handling
    date_col = 'Date' if 'Date' in df.columns else 'Datetime'
    if date_col not in df.columns:
        return None

    # Ensure clean price data
    df = df.dropna(subset=['Open', 'High', 'Low', 'Close']).copy()
    if len(df) < 30:
        return None

    # Calculate Candle Attributes based on GTF institutional rules
    df['Total_Length'] = abs(df['High'] - df['Low'])
    df['Body_Length'] = abs(df['Close'] - df['Open'])
    df['Avg_Length'] = df['Total_Length'].rolling(window=20).mean().fillna(df['Total_Length'])
    
    # GTF Exciting Candle (ERC): Body >= 55% of range and candle not abnormally tiny
    df['Is_Exciting'] = (df['Body_Length'] >= (df['Total_Length'] * 0.55)) & (df['Total_Length'] >= (df['Avg_Length'] * 0.5))
    # GTF Boring Candle (Base): Body <= 48% of range (tight accumulation/distribution)
    df['Is_Base'] = df['Body_Length'] <= (df['Total_Length'] * 0.48)
    
    # EMAs for Trend Confirmation & Score Booster
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
    
    current_price = float(df['Close'].iloc[-1])
    if np.isnan(current_price):
        return None

    ema20_now = float(df['EMA_20'].iloc[-1])
    ema50_now = float(df['EMA_50'].iloc[-1])
    uptrend = (current_price > ema50_now) and (ema20_now >= ema50_now)
    downtrend = (current_price < ema50_now) and (ema20_now <= ema50_now)

    trend_status = "Sideways"
    if uptrend:
        trend_status = "Uptrend"
    elif downtrend:
        trend_status = "Downtrend"

    # Strict lookback window to prevent digging years back into history:
    # 60 candles for Daily (~3 months), 52 candles for Weekly (~1 year), 36 candles for Monthly (~3 years)
    max_lookback = 60 if interval == "1d" else (52 if interval == "1wk" else 36)
    start_idx = max(8, len(df) - max_lookback)
    
    candidates = []
    
    # Reverse loop to search from current market action backwards:
    for i in range(len(df) - 2, start_idx, -1):
        leg_out_candle = df.iloc[i]
        if not df['Is_Exciting'].iloc[i]:
            continue
            
        # Count consecutive base candles backwards (Strict GTF: 1 to 3 base candles, max 4)
        base_count = 0
        j = i - 1
        while j >= 0 and df['Is_Base'].iloc[j] and base_count < 4:
            base_count += 1
            j -= 1
                
        # GTF Rule: strictly 1 to 3 base candles. If 0 or > 3, reject.
        if base_count < 1 or base_count > 3:
            continue
            
        leg_in_idx = i - base_count - 1
        if leg_in_idx < 0:
            continue
            
        leg_in_candle = df.iloc[leg_in_idx]
        base_candles = df.iloc[i-base_count:i]
        
        base_high = float(base_candles['High'].max())
        base_low = float(base_candles['Low'].min())
        base_body_max = float(max(base_candles['Open'].max(), base_candles['Close'].max()))
        base_body_min = float(min(base_candles['Open'].min(), base_candles['Close'].min()))
        
        # GTF Breakout Rule:
        # Rally Leg-out (Demand): Green candle decisively closing ABOVE highest high of base!
        # Drop Leg-out (Supply): Red candle decisively closing BELOW lowest low of base!
        is_rally_out = (leg_out_candle['Close'] > leg_out_candle['Open']) and (leg_out_candle['Close'] > base_high)
        is_drop_out = (leg_out_candle['Close'] < leg_out_candle['Open']) and (leg_out_candle['Close'] < base_low)
        
        if not (is_rally_out or is_drop_out):
            continue
            
        zone_type = "Demand" if is_rally_out else "Supply"
        
        if zone_type_needed and zone_type != zone_type_needed:
            continue

        # Immediate follow-through filter (eliminates sideways chop / fakeouts like UNIONBANK Daily):
        # The 1-2 bars right after leg_out must not close back inside/across proximal
        failed_follow_through = False
        for next_idx in range(i + 1, min(len(df), i + 3)):
            nc = df.iloc[next_idx]
            if zone_type == "Demand":
                if nc['Close'] < base_body_max or nc['Low'] < base_low:
                    failed_follow_through = True
                    break
            else: # Supply
                if nc['Close'] > base_body_min or nc['High'] > base_high:
                    failed_follow_through = True
                    break
        if failed_follow_through:
            continue
            
        bars_ago = (len(df) - 1) - i
        
        # Zone Marking (GTF Standard as seen in TradeTiger)
        # Demand: Proximal = Highest Body of base, Distal = Lowest Wick of base
        # Supply: Proximal = Lowest Body of base, Distal = Highest Wick of base
        if zone_type == "Demand":
            proximal = round(base_body_max, 2)
            distal = round(base_low, 2)
            risk = proximal - distal
            if risk <= 0:
                continue
                
            # Base compactness check
            max_risk_pct = 0.08 if interval == "1d" else (0.15 if interval == "1wk" else 0.18)
            if (risk / proximal) > max_risk_pct:
                continue # Base too wide/loose
                
            # Current Price Viability & CMP Proximity Filter:
            # 1. Price must not have violated distal
            if current_price < distal:
                continue
            # 2. Distance from CMP: Must be within 18% of CMP (or testing proximal)
            dist_pct = (current_price - proximal) / proximal
            if dist_pct < -0.05 or dist_pct > 0.18:
                continue # Outside realistic trade horizon!
                
            # Departure check:
            subsequent = df.iloc[i:]
            max_after = float(subsequent['High'].max())
            departure = max_after - proximal
            min_dep_ratio = 1.3 if bars_ago <= 5 else 1.8
            if departure < (min_dep_ratio * risk):
                continue
                
            # Freshness / Retests:
            peak_idx = subsequent['High'].idxmax()
            after_peak = df.loc[peak_idx + 1:] if peak_idx + 1 < len(df) else pd.DataFrame()
            if not after_peak.empty:
                if after_peak['Low'].min() < distal:
                    continue # Violated!
                tested_count = int(len(after_peak[after_peak['Low'] <= proximal]))
            else:
                tested_count = 0
                
            if tested_count > 2:
                continue # Over-tested
                
        else: # Supply Zone
            proximal = round(base_body_min, 2)
            distal = round(base_high, 2)
            risk = distal - proximal
            if risk <= 0:
                continue
                
            max_risk_pct = 0.08 if interval == "1d" else (0.15 if interval == "1wk" else 0.18)
            if (risk / proximal) > max_risk_pct:
                continue
                
            # Current Price Viability & CMP Proximity Filter:
            if current_price > distal:
                continue
            dist_pct = (proximal - current_price) / proximal
            if dist_pct < -0.05 or dist_pct > 0.18:
                continue
                
            # Departure check:
            subsequent = df.iloc[i:]
            min_after = float(subsequent['Low'].min())
            departure = proximal - min_after
            min_dep_ratio = 1.3 if bars_ago <= 5 else 1.8
            if departure < (min_dep_ratio * risk):
                continue
                
            trough_idx = subsequent['Low'].idxmin()
            after_trough = df.loc[trough_idx + 1:] if trough_idx + 1 < len(df) else pd.DataFrame()
            if not after_trough.empty:
                if after_trough['High'].max() > distal:
                    continue
                tested_count = int(len(after_trough[after_trough['High'] >= proximal]))
            else:
                tested_count = 0
                
            if tested_count > 2:
                continue
                
        # Strength of Zone (Immediate post-base momentum)
        next_candle_exciting = False
        if i + 1 < len(df) and df['Is_Exciting'].iloc[i+1]:
            if (zone_type == "Demand" and df['Close'].iloc[i+1] > df['Open'].iloc[i+1]) or \
               (zone_type == "Supply" and df['Close'].iloc[i+1] < df['Open'].iloc[i+1]):
                next_candle_exciting = True
                
        # Gap between last base candle and leg-out
        last_base_candle = base_candles.iloc[-1]
        has_gap = False
        if zone_type == "Demand" and leg_out_candle['Open'] > last_base_candle['Close']:
            has_gap = True
        elif zone_type == "Supply" and leg_out_candle['Open'] < last_base_candle['Close']:
            has_gap = True

        first_base_candle = df.iloc[i - base_count]
        leg_in_dir = "Rally" if leg_in_candle['Close'] > leg_in_candle['Open'] else "Drop"
        leg_out_dir = "Rally" if is_rally_out else "Drop"
        pattern = f"{leg_in_dir}-Base-{leg_out_dir}"

        # Ranking score (to ensure we pick zones near CMP and timeline priority):
        proximity_score = max(0, 40 - abs(dist_pct) * 200)
        recency_score = max(0, 30 - bars_ago)
        trend_score = 0
        if uptrend and zone_type == "Demand": trend_score = 20
        elif downtrend and zone_type == "Supply": trend_score = 20
        dep_ratio = departure / risk
        dep_bonus = min(10, dep_ratio * 2)

        rank_score = proximity_score + recency_score + trend_score + dep_bonus

        candidates.append({
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
            'dist_pct': round(dist_pct * 100, 1),
            'bars_ago': bars_ago,
            'rank_score': rank_score,
            'idx': i
        })

    if not candidates:
        return None

    # Sort candidates by rank_score descending (top priority to CMP proximity, recency, trend)
    candidates.sort(key=lambda x: x['rank_score'], reverse=True)
    latest_zone = candidates[0]
    
    # 1. Freshness (Max 3 pts)
    fresh_score = 3 if latest_zone['tested_count'] == 0 else 1
        
    # 2. Strength of the zone (Max 3 pts)
    strength_score = 1
    if latest_zone['next_candle_exciting']:
        strength_score = 3
    elif latest_zone['has_gap']:
        strength_score = 2
        
    # 3. Base Size (Max 3 pts - fewer base candles = higher institutional score)
    base_score = 0
    if latest_zone['base_count'] == 1:
        base_score = 3
    elif latest_zone['base_count'] == 2:
        base_score = 2
    elif latest_zone['base_count'] == 3:
        base_score = 1
        
    # 4. Golden / Death Crossover (Max 2)
    crossover_score = 0
    for j in range(max(1, len(df)-10), len(df)):
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
    
    # Prepare history for charting
    df['DateStr'] = df[date_col].dt.strftime('%Y-%m-%d')
    history_df = df[['DateStr', 'Open', 'High', 'Low', 'Close', 'EMA_20', 'EMA_50']].tail(300).dropna()
    history = []
    for _, row in history_df.iterrows():
        history.append({
            'DateStr': str(row['DateStr']),
            'Open': round(float(row['Open']), 2),
            'High': round(float(row['High']), 2),
            'Low': round(float(row['Low']), 2),
            'Close': round(float(row['Close']), 2),
            'EMA_20': round(float(row['EMA_20']), 2),
            'EMA_50': round(float(row['EMA_50']), 2)
        })
        
    tf_map = {
        "1d": "Daily (1D)",
        "1wk": "Weekly (1W)",
        "1mo": "Monthly (1M)",
        "3mo": "Quarterly (3M)"
    }

    prox_val = round(float(latest_zone['proximal']), 2)
    dist_to_entry = round(abs(current_price - prox_val) / prox_val * 100, 2) if prox_val > 0 else 0.0

    return {
        'current_price': float(current_price),
        'zone_type': latest_zone['zone_type'],
        'pattern': latest_zone['pattern'],
        'proximal': prox_val,
        'distal': round(float(latest_zone['distal']), 2),
        'dist_to_entry_pct': dist_to_entry,
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
        
    # Parallel batch download of all candidate tickers
    data_dict = fetch_batch_data(tickers, interval=interval, period=period)
    
    # Pre-fetch sector trend confluence
    sector_trends = {}
    if sector_map:
        needed_sectors = list(set([sector_map[t] for t in tickers if t in sector_map]))
        if needed_sectors:
            sec_dict = fetch_batch_data(needed_sectors, interval=interval, period="1y")
            for sec_idx, sec_df in sec_dict.items():
                if sec_df is not None and len(sec_df) >= 30:
                    s_ema20 = sec_df['Close'].ewm(span=20, adjust=False).mean().iloc[-1]
                    s_ema50 = sec_df['Close'].ewm(span=50, adjust=False).mean().iloc[-1]
                    s_price = sec_df['Close'].iloc[-1]
                    sector_trends[sec_idx] = {
                        'up': bool(s_price > s_ema20 and s_ema20 > s_ema50),
                        'down': bool(s_price < s_ema20 and s_ema20 < s_ema50)
                    }

    candidates = []
    for t in tickers:
        df = data_dict.get(t)
        if df is None or len(df) < 30:
            continue
            
        sec_up = False
        sec_down = False
        if sector_map and t in sector_map and sector_map[t] in sector_trends:
            sec_up = sector_trends[sector_map[t]]['up']
            sec_down = sector_trends[sector_map[t]]['down']
            
        analysis = analyze_gtf(df, interval, sector_uptrend=sec_up, sector_downtrend=sec_down)
        if analysis:
            analysis['ticker'] = t
            cmp = analysis['current_price']
            prox = analysis['proximal']
            dist_pct = abs(cmp - prox) / prox * 100 if prox > 0 else 0
            analysis['dist_to_entry_pct'] = round(dist_pct, 2)
            candidates.append(analysis)

    # Batch HTF Curve check on candidates only
    htf_info = htf_map.get(interval)
    final_results = []
    if htf_info and candidates:
        htf_interval, htf_period = htf_info
        cand_tickers = [c['ticker'] for c in candidates]
        htf_dict = fetch_batch_data(cand_tickers, interval=htf_interval, period=htf_period)
        
        for c in candidates:
            t = c['ticker']
            htf_df = htf_dict.get(t)
            if htf_df is not None and len(htf_df) >= 30:
                opposing_type = "Supply" if c['zone_type'] == "Demand" else "Demand"
                htf_opposing = analyze_gtf(htf_df, htf_interval, zone_type_needed=opposing_type)
                if htf_opposing:
                    current_price = c['current_price']
                    htf_proximal = htf_opposing['proximal']
                    if opposing_type == "Supply" and current_price >= htf_proximal:
                        continue # Hit HTF Supply! Discard trade.
                    elif opposing_type == "Demand" and current_price <= htf_proximal:
                        continue # Hit HTF Demand! Discard trade.
            final_results.append(c)
    else:
        final_results = candidates

    # Sort strictly from BEST to WORST:
    # 1. Primary: Score descending (14 down to 0)
    # 2. Secondary: Trend alignment (Uptrend for Demand, Downtrend for Supply)
    # 3. Tertiary: Distance to entry ascending (closer to entry is more actionable)
    # 4. Quaternary: Freshness (Fresh 0-test first)
    # 5. Base size (tight 1-candle base first)
    def rank_key(x):
        score = x.get('score', 0)
        dist = x.get('dist_to_entry_pct', 999.0)
        freshness = x.get('score_breakdown', {}).get('Freshness (3)', 0)
        base_size = x.get('score_breakdown', {}).get('Base Size (3)', 0)
        trend_align = 1 if (x.get('zone_type') == 'Demand' and x.get('trend') == 'Uptrend') or \
                           (x.get('zone_type') == 'Supply' and x.get('trend') == 'Downtrend') else 0
        return (-score, -trend_align, dist, -freshness, -base_size)

    final_results = sorted(final_results, key=rank_key)

    # Assign explicit 1-based ranks
    for rank, item in enumerate(final_results, start=1):
        item['rank'] = rank

    return final_results
