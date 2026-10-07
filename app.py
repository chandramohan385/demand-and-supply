from flask import Flask, render_template, jsonify, request
from core.scanner import scan_tickers

app = Flask(__name__)

# Representative list of highly liquid Indian stocks (NIFTY 50 examples)
NIFTY_STOCKS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", 
    "SBIN", "KOTAKBANK", "BHARTIARTL", "ITC", "LT", 
    "BAJFINANCE", "TATASTEEL", "M&M", "MARUTI", "SUNPHARMA"
]

SECTOR_MAP = {
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
    "SUNPHARMA": "^CNXPHARMA"
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/scan')
def api_scan():
    interval = request.args.get('interval', '1d')
    try:
        results = scan_tickers(NIFTY_STOCKS, interval=interval, sector_map=SECTOR_MAP)
        return jsonify({'status': 'success', 'data': results})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
