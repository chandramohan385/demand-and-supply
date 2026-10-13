import os
from concurrent.futures import ThreadPoolExecutor
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
    chunks = [tickers_ns[i:i + chunk_size] for i in range(0, len(tickers_ns), chunk_size)]

    def download_and_parse(chunk):
        chunk_res = {}
        try:
            batch_df = yf.download(chunk, period=period, interval=interval, group_by='ticker', progress=False, threads=True)
            if batch_df.empty:
                return chunk_res
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
                                chunk_res[raw_sym] = sub
                    else:
                        df = batch_df.reset_index()
                        chunk_res[raw_sym] = df
                except Exception:
                    continue
        except Exception as e:
            print(f"Error fetching batch chunk: {e}")
        return chunk_res

    with ThreadPoolExecutor(max_workers=min(5, len(chunks))) as executor:
        for part in executor.map(download_and_parse, chunks):
            res_dict.update(part)

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

    # Strict lookback window (Swing Horizon) to prevent digging years back into history:
    # 3mo: 6 candles (~1.5 years), 1mo: 12 candles (~1 year), 1wk: 20 candles (~5 months), 1d: 30 candles (~1.5 months)
    lookback_map = {
        "1d": 30,
        "1wk": 20,
        "1mo": 12,
        "3mo": 6
    }
    max_lookback = lookback_map.get(interval, 30)
    start_idx = max(5, len(df) - max_lookback)
    
    max_dist_map = {
        "1d": 0.12,
        "1wk": 0.15,
        "1mo": 0.18,
        "3mo": 0.18
    }
    max_dist = max_dist_map.get(interval, 0.15)
    
    candidates = []
    
    # Reverse loop to strictly search from Current Market Price (right side) backwards (left side):
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

        # Immediate follow-through filter (eliminates sideways chop / fakeouts):
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
            max_risk_pct = 0.08 if interval == "1d" else (0.12 if interval == "1wk" else 0.16)
            if (risk / proximal) > max_risk_pct:
                continue # Base too wide/loose
                
            # Current Price Viability (Check from CMP downwards):
            # Demand zone MUST be under CMP (or CMP testing entry within 1.5%)
            if current_price < (proximal * 0.985):
                continue
            dist_pct = (current_price - proximal) / proximal
            if dist_pct > max_dist:
                continue # Too far away from CMP
                
            # Departure check:
            subsequent = df.iloc[i:]
            max_after = float(subsequent['High'].max())
            departure = max_after - proximal
            min_dep_ratio = 1.3 if bars_ago <= 4 else 1.8
            if departure < (min_dep_ratio * risk):
                continue
                
            # Lifecycle, Freshness & Penetration check:
            post_legout = df.iloc[i+1:]
            if not post_legout.empty:
                if float(post_legout['Low'].min()) < distal:
                    continue # Violated!
                # Deep penetration filter: if price pierced > 20% into zone, pending orders were filled
                deep_penetration = proximal - (0.20 * risk)
                if float(post_legout['Low'].min()) <= deep_penetration:
                    continue # Penetrated deeply: Spent!
                tested_count = int(len(post_legout[post_legout['Low'] <= proximal]))
                if tested_count > 1:
                    continue # Over-tested: Spent!
            else:
                tested_count = 0
                
        else: # Supply Zone
            proximal = round(base_body_min, 2)
            distal = round(base_high, 2)
            risk = distal - proximal
            if risk <= 0:
                continue
                
            max_risk_pct = 0.08 if interval == "1d" else (0.12 if interval == "1wk" else 0.16)
            if (risk / proximal) > max_risk_pct:
                continue
                
            # Current Price Viability (Check from CMP upwards):
            # Supply zone MUST be above CMP (or CMP testing entry within 1.5%)
            if current_price > (proximal * 1.015):
                continue
            dist_pct = (proximal - current_price) / proximal
            if dist_pct > max_dist:
                continue
                
            # Departure check:
            subsequent = df.iloc[i:]
            min_after = float(subsequent['Low'].min())
            departure = proximal - min_after
            min_dep_ratio = 1.3 if bars_ago <= 4 else 1.8
            if departure < (min_dep_ratio * risk):
                continue
                
            # Lifecycle, Freshness & Penetration check:
            post_legout = df.iloc[i+1:]
            if not post_legout.empty:
                if float(post_legout['High'].max()) > distal:
                    continue # Violated!
                deep_penetration = proximal + (0.20 * risk)
                if float(post_legout['High'].max()) >= deep_penetration:
                    continue # Penetrated deeply: Spent!
                tested_count = int(len(post_legout[post_legout['High'] >= proximal]))
                if tested_count > 1:
                    continue # Over-tested: Spent!
            else:
                tested_count = 0
                
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

        # 1. Freshness (Max 3 pts)
        fresh_score = 3 if tested_count == 0 else 1
            
        # 2. Strength of the zone (Max 3 pts)
        strength_score = 1
        if next_candle_exciting:
            strength_score = 3
        elif has_gap:
            strength_score = 2
            
        # 3. Base Size (Max 3 pts)
        base_score = 3 if base_count == 1 else (2 if base_count == 2 else 1)
            
        # 4. Golden / Death Crossover (Max 2)
        crossover_score = 0
        for k in range(max(1, len(df)-10), len(df)):
            if zone_type == "Demand":
                if df['EMA_20'].iloc[k] > df['EMA_50'].iloc[k] and df['EMA_20'].iloc[k-1] <= df['EMA_50'].iloc[k-1]:
                    crossover_score = 2
                    break
            else:
                if df['EMA_20'].iloc[k] < df['EMA_50'].iloc[k] and df['EMA_20'].iloc[k-1] >= df['EMA_50'].iloc[k-1]:
                    crossover_score = 2
                    break
                    
        # 5. EMA Position (Max 1)
        ema_exec_score = 0
        if zone_type == "Demand" and current_price > df['EMA_20'].iloc[-1]:
            ema_exec_score = 1
        elif zone_type == "Supply" and current_price < df['EMA_20'].iloc[-1]:
            ema_exec_score = 1
            
        # 6. Sector Support (Max 2)
        sector_score = 0
        if zone_type == "Demand" and sector_uptrend:
            sector_score = 2
        elif zone_type == "Supply" and sector_downtrend:
            sector_score = 2
            
        score = fresh_score + strength_score + base_score + crossover_score + ema_exec_score + sector_score
        
        # STRICT QUALITY FLOOR: Reject weak setups (< 8). Only high-probability setups!
        if score < 8:
            continue

        score_breakdown = {
            'Freshness (3)': fresh_score,
            'Strength (3)': strength_score,
            'Base Size (3)': base_score,
            'Crossover (2)': crossover_score,
            'EMA Position (1)': ema_exec_score,
            'Sector Support (2)': sector_score
        }

        # Ranking score: top priority to timeline recency to CMP, CMP proximity, score, and trend
        recency_rank = max(0, 30 - bars_ago)
        proximity_rank = max(0, 30 - dist_pct * 100)
        trend_rank = 15 if (uptrend and zone_type == "Demand") or (downtrend and zone_type == "Supply") else 0
        total_rank = (score * 5) + recency_rank + proximity_rank + trend_rank

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
            'total_rank': total_rank,
            'score': score,
            'score_breakdown': score_breakdown,
            'idx': i
        })

    if not candidates:
        return None

    # Pick candidate with highest ranking score
    candidates.sort(key=lambda x: x['total_rank'], reverse=True)
    latest_zone = candidates[0]
    score = latest_zone['score']
    score_breakdown = latest_zone['score_breakdown']
    
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

def scan_tickers(tickers, interval="1d", sector_map=None, is_total_market=False):
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
        if analysis and analysis.get('score', 0) >= 8:
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

    # When scanning Total Market (Lazy Trader mode): "Only the best, the perfect, should be shown"
    if is_total_market and final_results:
        perfect_candidates = [
            c for c in final_results 
            if c.get('score', 0) >= 10 
            and c.get('score_breakdown', {}).get('Freshness (3)', 0) == 3
            and c.get('dist_to_entry_pct', 999.0) <= 10.0
        ]
        if len(perfect_candidates) >= 3:
            final_results = perfect_candidates[:15]
        else:
            final_results = [c for c in final_results if c.get('score', 0) >= 9][:15]

    # Assign explicit 1-based ranks, target prices, verdicts and rationale
    total_scanned = len(tickers)
    for rank, item in enumerate(final_results, start=1):
        item['rank'] = rank
        prox = item['proximal']
        distal = item['distal']
        risk = abs(prox - distal)
        is_dem = item['zone_type'] == 'Demand'
        target = round(prox + (2.0 * risk) if is_dem else prox - (2.0 * risk), 2)
        item['target'] = target
        item['risk_reward'] = '1:2.0'
        
        # Dedicated Trade Verdict Column
        if rank == 1:
            item['verdict'] = 'BEST OF BESTEST'
            item['verdict_badge'] = '👑 BEST OF THE BESTEST'
            item['verdict_desc'] = 'Top Market Pick • Ready to Trade'
        elif rank <= 3:
            item['verdict'] = 'PERFECT SETUP'
            item['verdict_badge'] = '💎 PERFECT SETUP'
            item['verdict_desc'] = 'High Conviction Trade'
        else:
            item['verdict'] = 'ELITE TRADE'
            item['verdict_badge'] = '⭐ ELITE GRADE'
            item['verdict_desc'] = 'Institutional Quality'

        # Separate text / Rationale description
        item['rationale'] = (
            f"👑 INSTITUTIONAL TRADE PLAN (Rank #{rank} of {total_scanned} Stocks): "
            f"{item['ticker']} is identified with an unmitigated {item['zone_type']} Zone ({item['pattern']}) "
            f"featuring 0 prior tests and sharp departure velocity. Current price is ₹{item['current_price']} "
            f"(just {item['dist_to_entry_pct']}% from optimal entry at ₹{prox}). Stop Loss is placed at ₹{distal} "
            f"with a 1:2 Risk-Reward Target at ₹{target}. Supported by {item['trend']} trend structure "
            f"with an Institutional Score of {item['score']}/14."
        )

    return final_results
