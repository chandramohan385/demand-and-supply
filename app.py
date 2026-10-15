import os
import json
from flask import Flask, render_template, jsonify, request
from core.scanner import scan_tickers, fetch_data

app = Flask(__name__)

# Official and Representative lists of Indian stocks
STOCK_LISTS = {
    "NIFTY_50": [
        "ADANIENT", "ADANIPORTS", "APOLLOHOSP", "ASIANPAINT", "AXISBANK", 
        "BSE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BEL", 
        "BHARTIARTL", "CIPLA", "COALINDIA", "DRREDDY", "EICHERMOT", 
        "ETERNAL", "GRASIM", "HCLTECH", "HDFCBANK", "HDFCLIFE", 
        "HINDALCO", "HINDUNILVR", "ICICIBANK", "ITC", "INFY", 
        "INDIGO", "JSWSTEEL", "JIOFIN", "KOTAKBANK", "LT", 
        "M&M", "MARUTI", "MAXHEALTH", "NTPC", "NESTLEIND", 
        "ONGC", "POWERGRID", "RELIANCE", "SBILIFE", "SHRIRAMFIN", 
        "SBIN", "SUNPHARMA", "TCS", "TATACONSUM", "TMPV", 
        "TATASTEEL", "TECHM", "TITAN", "TRENT", "ULTRACEMCO"
    ],
    "BANK_NIFTY": [
        "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", 
        "INDUSINDBK", "PNB", "BANKBARODA", "FEDERALBNK", "IDFCFIRSTB",
        "AUBANK", "BANDHANBNK"
    ],
    "NIFTY_IT": [
        "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", 
        "LTIM", "PERSISTENT", "COFORGE", "MPHASIS"
    ],
    "NIFTY_AUTO": [
        "M&M", "MARUTI", "TATAMOTORS", "BAJAJ-AUTO", "HEROMOTOCO",
        "EICHERMOT", "TVSMOTOR", "ASHOKLEY", "BOSCHLTD", "TIINDIA", "BHARATFORG"
    ],
    "NIFTY_PHARMA": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN",
        "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE", "BIOCON", "MANKIND"
    ],
    "NIFTY_METAL": [
        "TATASTEEL", "HINDALCO", "JSWSTEEL", "COALINDIA", "VEDL",
        "SAIL", "NMDC", "NATIONALUM", "JINDALSTEL"
    ],
    "NIFTY_REALTY": [
        "DLF", "MACROTECH", "GODREJPROP", "PRESTIGE", "PHOENIXLTD", 
        "OBEROIRLTY", "BRIGADE", "SOBHA", "LODHA"
    ],
    "NIFTY_FMCG": [
        "ITC", "HINDUNILVR", "NESTLEIND", "BRITANNIA", "TATACONSUM", 
        "GODREJCP", "DABUR", "MARICO", "COLPAL", "UBL", "VBL"
    ],
    "NIFTY_PSU_BANK": [
        "SBIN", "PNB", "BANKBARODA", "CANBK", "UNIONBANK", 
        "INDIANB", "IOB", "BANKINDIA", "MAHABANK", "CENTRALBK"
    ],
    "NIFTY_OIL_GAS": [
        "RELIANCE", "ONGC", "IOC", "BPCL", "GAIL", 
        "HINDPETRO", "PETRONET", "IGL", "ATGL", "MGL"
    ],
    "NIFTY_500": [],           # Populated dynamically from core/stock_lists.json
    "TOTAL_MARKET": [],        # Full NSE 2,300+ stocks for Lazy Trader Best of Bestest
    "NIFTY_SMALLCAP_100": [],  # Populated dynamically from core/stock_lists.json
    "NIFTY_MEDIA": [
        "ZEEL", "SUNTV", "NETWORK18", "TV18BRDCST", "PVRINOX", 
        "SAREGAMA", "HATHWAY", "DISHTV", "NDTV"
    ]
}

# Dynamically load complete lists from core/stock_lists.json
stock_lists_file = os.path.join(os.path.dirname(__file__), 'core', 'stock_lists.json')
if os.path.exists(stock_lists_file):
    try:
        with open(stock_lists_file, 'r') as f:
            full_lists = json.load(f)
        if 'NIFTY_50' in full_lists and len(full_lists['NIFTY_50']) == 50:
            STOCK_LISTS['NIFTY_50'] = full_lists['NIFTY_50']
        if 'NIFTY_500' in full_lists:
            STOCK_LISTS['NIFTY_500'] = full_lists['NIFTY_500']
        if 'NIFTY_SMALLCAP_100' in full_lists:
            STOCK_LISTS['NIFTY_SMALLCAP_100'] = full_lists['NIFTY_SMALLCAP_100']
        if 'NSE_ALL' in full_lists and len(full_lists['NSE_ALL']) > 500:
            STOCK_LISTS['TOTAL_MARKET'] = full_lists['NSE_ALL']
        elif 'NIFTY_500' in full_lists:
            STOCK_LISTS['TOTAL_MARKET'] = full_lists['NIFTY_500']
    except Exception as e:
        print(f"Error loading full stock lists: {e}")

SECTOR_MAP = {
    "RELIANCE": "^CNXENERGY",
    "TCS": "^CNXIT", "INFY": "^CNXIT",
    "HDFCBANK": "^NSEBANK", "ICICIBANK": "^NSEBANK", "SBIN": "^NSEBANK", "KOTAKBANK": "^NSEBANK",
    "BHARTIARTL": "^CNXMEDIA",
    "ITC": "^CNXFMCG",
    "LT": "^CNXINFRA",
    "BAJFINANCE": "^CNXFIN",
    "TATASTEEL": "^CNXMETAL",
    "M&M": "^CNXAUTO", "MARUTI": "^CNXAUTO",
    "SUNPHARMA": "^CNXPHARMA",
    "AXISBANK": "^NSEBANK", "INDUSINDBK": "^NSEBANK", "PNB": "^NSEBANK",
    "BANKBARODA": "^NSEBANK", "FEDERALBNK": "^NSEBANK", "IDFCFIRSTB": "^NSEBANK",
    "HCLTECH": "^CNXIT", "WIPRO": "^CNXIT", "TECHM": "^CNXIT",
    "LTIM": "^CNXIT", "PERSISTENT": "^CNXIT", "COFORGE": "^CNXIT", "MPHASIS": "^CNXIT",
    "TATAMOTORS": "^CNXAUTO", "BAJAJ-AUTO": "^CNXAUTO", "HEROMOTOCO": "^CNXAUTO",
    "EICHERMOT": "^CNXAUTO", "TVSMOTOR": "^CNXAUTO", "ASHOKLEY": "^CNXAUTO", "BOSCHLTD": "^CNXAUTO",
    "DRREDDY": "^CNXPHARMA", "CIPLA": "^CNXPHARMA", "DIVISLAB": "^CNXPHARMA",
    "LUPIN": "^CNXPHARMA", "AUROPHARMA": "^CNXPHARMA", "TORNTPHARM": "^CNXPHARMA",
    "ZYDUSLIFE": "^CNXPHARMA", "BIOCON": "^CNXPHARMA",
    "HINDALCO": "^CNXMETAL", "JSWSTEEL": "^CNXMETAL", "COALINDIA": "^CNXMETAL",
    "DLF": "^CNXREALTY", "MACROTECH": "^CNXREALTY", "GODREJPROP": "^CNXREALTY",
    "PRESTIGE": "^CNXREALTY", "PHOENIXLTD": "^CNXREALTY", "OBEROIRLTY": "^CNXREALTY",
    "BRIGADE": "^CNXREALTY", "SOBHA": "^CNXREALTY", "LODHA": "^CNXREALTY",
    "HINDUNILVR": "^CNXFMCG", "NESTLEIND": "^CNXFMCG", "BRITANNIA": "^CNXFMCG",
    "TATACONSUM": "^CNXFMCG", "GODREJCP": "^CNXFMCG", "DABUR": "^CNXFMCG",
    "MARICO": "^CNXFMCG", "COLPAL": "^CNXFMCG", "UBL": "^CNXFMCG",
    "CANBK": "^CNXPSUBANK", "UNIONBANK": "^CNXPSUBANK", "INDIANB": "^CNXPSUBANK",
    "IOB": "^CNXPSUBANK", "BANKINDIA": "^CNXPSUBANK", "MAHABANK": "^CNXPSUBANK", "CENTRALBK": "^CNXPSUBANK",
    "ONGC": "^CNXENERGY", "IOC": "^CNXENERGY", "BPCL": "^CNXENERGY",
    "GAIL": "^CNXENERGY", "HINDPETRO": "^CNXENERGY", "PETRONET": "^CNXENERGY",
    "IGL": "^CNXENERGY", "ATGL": "^CNXENERGY", "MGL": "^CNXENERGY",
    "SUZLON": "^NSEI", "BSE": "^NSEI", "CDSL": "^NSEI",
    "MCX": "^NSEI", "ANGELONE": "^NSEI", "CYIENT": "^NSEI",
    "RADICO": "^NSEI", "KEI": "^NSEI", "SONACOMS": "^NSEI",
    "CAMS": "^NSEI", "APARINDS": "^NSEI", "KAYNES": "^NSEI",
    "TEJASNET": "^NSEI", "CHALET": "^NSEI", "PVRINOX": "^NSEI",
    "ZEEL": "^CNXMEDIA", "SUNTV": "^CNXMEDIA", "NETWORK18": "^CNXMEDIA",
    "TV18BRDCST": "^CNXMEDIA", "SAREGAMA": "^CNXMEDIA", "HATHWAY": "^CNXMEDIA",
    "DISHTV": "^CNXMEDIA", "NDTV": "^CNXMEDIA"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan')
def api_scan():
    interval = request.args.get('interval', '1d')
    category = request.args.get('category', 'TOTAL_MARKET')
    zone_type = request.args.get('zone_type', 'ALL')
    is_total_market = (category == 'TOTAL_MARKET')

    # Instant response for TOTAL_MARKET from pre-computed cache
    if is_total_market:
        cache_file = os.path.join(os.path.dirname(__file__), 'core', 'market_cache.json')
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                if interval in cache_data and cache_data[interval].get('data'):
                    entry = cache_data[interval]
                    demand_data = entry.get('demand_data', [x for x in entry['data'] if x['zone_type'] == 'Demand'])
                    supply_data = entry.get('supply_data', [x for x in entry['data'] if x['zone_type'] == 'Supply'])
                    best_demand = entry.get('best_demand_pick', demand_data[0] if demand_data else None)
                    best_supply = entry.get('best_supply_pick', supply_data[0] if supply_data else None)
                    
                    data = entry['data']
                    best_pick = entry['best_pick']
                    if zone_type == 'Demand':
                        data = demand_data
                        best_pick = best_demand
                    elif zone_type == 'Supply':
                        data = supply_data
                        best_pick = best_supply
                        
                    return jsonify({
                        'status': 'success',
                        'data': data,
                        'demand_data': demand_data,
                        'supply_data': supply_data,
                        'best_pick': best_pick,
                        'best_demand_pick': best_demand,
                        'best_supply_pick': best_supply,
                        'total_scanned': entry.get('total_scanned', len(STOCK_LISTS['TOTAL_MARKET'])),
                        'cached': True
                    })
            except Exception as e:
                print(f"Error loading market cache: {e}")

    # For index live scans
    tickers = STOCK_LISTS.get(category, STOCK_LISTS.get('TOTAL_MARKET', STOCK_LISTS['NIFTY_50']))
    
    try:
        results, demand_res, supply_res = scan_tickers(tickers, interval=interval, sector_map=SECTOR_MAP, is_total_market=is_total_market, return_splits=True)
        data = results
        best_pick = results[0] if results else None
        if zone_type == 'Demand':
            data = demand_res
            best_pick = demand_res[0] if demand_res else None
        elif zone_type == 'Supply':
            data = supply_res
            best_pick = supply_res[0] if supply_res else None
            
        total_count = len(STOCK_LISTS.get(category, tickers))
        return jsonify({
            'status': 'success',
            'data': data,
            'demand_data': demand_res,
            'supply_data': supply_res,
            'best_pick': best_pick,
            'best_demand_pick': demand_res[0] if demand_res else None,
            'best_supply_pick': supply_res[0] if supply_res else None,
            'total_scanned': total_count
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/history')
def api_history():
    """Fetch candlestick history on demand for TradingView charting."""
    ticker = request.args.get('ticker')
    interval = request.args.get('interval', '1d')
    if not ticker:
        return jsonify({'status': 'error', 'message': 'Ticker required'})
    try:
        period = "1y" if interval == "1d" else ("2y" if interval == "1wk" else "5y")
        df = fetch_data(ticker, interval=interval, period=period)
        if df is None or len(df) < 10:
            return jsonify({'status': 'error', 'message': f'No historical data for {ticker}'})
        
        df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        date_col = 'Date' if 'Date' in df.columns else 'Datetime'
        df['DateStr'] = df[date_col].dt.strftime('%Y-%m-%d')
        history_df = df[['DateStr', 'Open', 'High', 'Low', 'Close', 'EMA_20', 'EMA_50']].tail(150).dropna()
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
        return jsonify({'status': 'success', 'ticker': ticker, 'history': history})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/api/stock_count')
def api_stock_count():
    """Returns the count of stocks in each category for UI display."""
    counts = {k: len(v) for k, v in STOCK_LISTS.items()}
    return jsonify(counts)

@app.route('/api/update_nse_list', methods=['POST'])
def api_update_nse_list():
    """Refresh the NSE_ALL list by downloading fresh from NSE archives."""
    try:
        import urllib.request
        import csv
        import io
        url = 'https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv'
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Referer': 'https://www.nseindia.com',
        }
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            content = response.read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(content))
        nse_all = []
        for row in reader:
            sym = row.get('SYMBOL', '').strip()
            series = row.get(' SERIES', '').strip()
            if sym and series == 'EQ':
                nse_all.append(sym)
        nse_all = sorted(list(set(nse_all)))
        with open(stock_lists_file, 'r') as f:
            sl = json.load(f)
        sl['NSE_ALL'] = nse_all
        with open(stock_lists_file, 'w') as f:
            json.dump(sl, f, separators=(',', ':'))
        STOCK_LISTS['TOTAL_MARKET'] = nse_all
        return jsonify({'status': 'success', 'count': len(nse_all),
                        'message': f'NSE list refreshed: {len(nse_all)} stocks loaded'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
