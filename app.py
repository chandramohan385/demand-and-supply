import os
import json
from flask import Flask, render_template, jsonify, request
from core.scanner import scan_tickers

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
    "NIFTY_500": [], # Populated dynamically from core/stock_lists.json
    "NIFTY_SMALLCAP_100": [], # Populated dynamically from core/stock_lists.json
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
    except Exception as e:
        print(f"Error loading full stock lists: {e}")


SECTOR_MAP = {
    # NIFTY 50 Base
    "RELIANCE": "^CNXENERGY",
    "TCS": "^CNXIT",
    "INFY": "^CNXIT",
    "HDFCBANK": "^NSEBANK",
    "ICICIBANK": "^NSEBANK",
    "SBIN": "^NSEBANK",
    "KOTAKBANK": "^NSEBANK",
    "BHARTIARTL": "^CNXMEDIA", 
    "ITC": "^CNXFMCG",
    "LT": "^CNXINFRA",
    "BAJFINANCE": "^CNXFIN",
    "TATASTEEL": "^CNXMETAL",
    "M&M": "^CNXAUTO",
    "MARUTI": "^CNXAUTO",
    "SUNPHARMA": "^CNXPHARMA",
    # BANK NIFTY
    "AXISBANK": "^NSEBANK", "INDUSINDBK": "^NSEBANK", "PNB": "^NSEBANK",
    "BANKBARODA": "^NSEBANK", "FEDERALBNK": "^NSEBANK", "IDFCFIRSTB": "^NSEBANK",
    # NIFTY IT
    "HCLTECH": "^CNXIT", "WIPRO": "^CNXIT", "TECHM": "^CNXIT",
    "LTIM": "^CNXIT", "PERSISTENT": "^CNXIT", "COFORGE": "^CNXIT", "MPHASIS": "^CNXIT",
    # NIFTY AUTO
    "TATAMOTORS": "^CNXAUTO", "BAJAJ-AUTO": "^CNXAUTO", "HEROMOTOCO": "^CNXAUTO",
    "EICHERMOT": "^CNXAUTO", "TVSMOTOR": "^CNXAUTO", "ASHOKLEY": "^CNXAUTO", "BOSCHLTD": "^CNXAUTO",
    # NIFTY PHARMA
    "DRREDDY": "^CNXPHARMA", "CIPLA": "^CNXPHARMA", "DIVISLAB": "^CNXPHARMA",
    "LUPIN": "^CNXPHARMA", "AUROPHARMA": "^CNXPHARMA", "TORNTPHARM": "^CNXPHARMA",
    "ZYDUSLIFE": "^CNXPHARMA", "BIOCON": "^CNXPHARMA",
    # NIFTY METAL
    "HINDALCO": "^CNXMETAL", "JSWSTEEL": "^CNXMETAL", "COALINDIA": "^CNXMETAL",
    # NIFTY REALTY
    "DLF": "^CNXREALTY", "MACROTECH": "^CNXREALTY", "GODREJPROP": "^CNXREALTY", 
    "PRESTIGE": "^CNXREALTY", "PHOENIXLTD": "^CNXREALTY", "OBEROIRLTY": "^CNXREALTY", 
    "BRIGADE": "^CNXREALTY", "SOBHA": "^CNXREALTY", "LODHA": "^CNXREALTY",
    # NIFTY FMCG
    "HINDUNILVR": "^CNXFMCG", "NESTLEIND": "^CNXFMCG", "BRITANNIA": "^CNXFMCG", 
    "TATACONSUM": "^CNXFMCG", "GODREJCP": "^CNXFMCG", "DABUR": "^CNXFMCG", 
    "MARICO": "^CNXFMCG", "COLPAL": "^CNXFMCG", "UBL": "^CNXFMCG",
    # NIFTY PSU BANK
    "CANBK": "^CNXPSUBANK", "UNIONBANK": "^CNXPSUBANK", "INDIANB": "^CNXPSUBANK", 
    "IOB": "^CNXPSUBANK", "BANKINDIA": "^CNXPSUBANK", "MAHABANK": "^CNXPSUBANK", "CENTRALBK": "^CNXPSUBANK",
    # NIFTY OIL & GAS (Energy)
    "ONGC": "^CNXENERGY", "IOC": "^CNXENERGY", "BPCL": "^CNXENERGY", 
    "GAIL": "^CNXENERGY", "HINDPETRO": "^CNXENERGY", "PETRONET": "^CNXENERGY", 
    "IGL": "^CNXENERGY", "ATGL": "^CNXENERGY", "MGL": "^CNXENERGY",
    # SMALLCAP 100
    "SUZLON": "^NSEI", "BSE": "^NSEI", "CDSL": "^NSEI", 
    "MCX": "^NSEI", "ANGELONE": "^NSEI", "CYIENT": "^NSEI", 
    "RADICO": "^NSEI", "KEI": "^NSEI", "SONACOMS": "^NSEI", 
    "CAMS": "^NSEI", "APARINDS": "^NSEI", "KAYNES": "^NSEI", 
    "TEJASNET": "^NSEI", "CHALET": "^NSEI", "PVRINOX": "^NSEI",
    # NIFTY MEDIA
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
    category = request.args.get('category', 'NIFTY_50')
    tickers = STOCK_LISTS.get(category, STOCK_LISTS['NIFTY_50'])
    try:
        results = scan_tickers(tickers, interval=interval, sector_map=SECTOR_MAP)
        return jsonify({'status': 'success', 'data': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
