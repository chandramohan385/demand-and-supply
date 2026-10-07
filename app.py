from flask import Flask, render_template, jsonify, request
from core.scanner import scan_tickers

app = Flask(__name__)

# Representative list of highly liquid Indian stocks (NIFTY 50 examples)
STOCK_LISTS = {
    "NIFTY_50": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
        "SBIN", "BHARTIARTL", "ITC", "LT", "BAJFINANCE", 
        "TATASTEEL", "M&M", "MARUTI", "SUNPHARMA", "KOTAKBANK"
    ],
    "BANK_NIFTY": [
        "HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK", 
        "INDUSINDBK", "PNB", "BANKBARODA", "FEDERALBNK", "IDFCFIRSTB"
    ],
    "NIFTY_IT": [
        "TCS", "INFY", "HCLTECH", "WIPRO", "TECHM", 
        "LTIM", "PERSISTENT", "COFORGE", "MPHASIS"
    ],
    "NIFTY_AUTO": [
        "M&M", "MARUTI", "TATAMOTORS", "BAJAJ-AUTO", "HEROMOTOCO",
        "EICHERMOT", "TVSMOTOR", "ASHOKLEY", "BOSCHLTD"
    ],
    "NIFTY_PHARMA": [
        "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN",
        "AUROPHARMA", "TORNTPHARM", "ZYDUSLIFE", "BIOCON"
    ],
    "NIFTY_METAL": [
        "TATASTEEL", "HINDALCO", "JSWSTEEL", "COALINDIA", "VEDL",
        "SAIL", "NMDC", "NATIONALUM"
    ]
}

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
    "VEDL": "^CNXMETAL", "SAIL": "^CNXMETAL", "NMDC": "^CNXMETAL", "NATIONALUM": "^CNXMETAL"
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
