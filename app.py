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
    ],
    "NIFTY_REALTY": [
        "DLF", "MACROTECH", "GODREJPROP", "PRESTIGE", "PHOENIXLTD", 
        "OBEROIRLTY", "BRIGADE", "SOBHA", "LODHA"
    ],
    "NIFTY_FMCG": [
        "ITC", "HINDUNILVR", "NESTLEIND", "BRITANNIA", "TATACONSUM", 
        "GODREJCP", "DABUR", "MARICO", "COLPAL", "UBL"
    ],
    "NIFTY_PSU_BANK": [
        "SBIN", "PNB", "BANKBARODA", "CANBK", "UNIONBANK", 
        "INDIANB", "IOB", "BANKINDIA", "MAHABANK", "CENTRALBK"
    ],
    "NIFTY_OIL_GAS": [
        "RELIANCE", "ONGC", "IOC", "BPCL", "GAIL", 
        "HINDPETRO", "PETRONET", "IGL", "ATGL", "MGL"
    ],
    "NIFTY_500": [
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL",
        "ITC", "LT", "BAJFINANCE", "TATASTEEL", "M&M", "MARUTI", "SUNPHARMA",
        "ADANIENT", "ASIANPAINT", "TITAN", "HAL", "ZOMATO", "TRENT"
    ],
    "NIFTY_SMALLCAP_100": [
        "SUZLON", "BSE", "CDSL", "MCX", "ANGELONE", 
        "CYIENT", "RADICO", "KEI", "SONACOMS", "CAMS",
        "APARINDS", "KAYNES", "TEJASNET", "CHALET", "PVRINOX"
    ],
    "NIFTY_MEDIA": [
        "ZEEL", "SUNTV", "NETWORK18", "TV18BRDCST", "PVRINOX", 
        "SAREGAMA", "HATHWAY", "DISHTV", "NDTV"
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
    "SUZLON": "^CNXSMALLCAP", "BSE": "^CNXSMALLCAP", "CDSL": "^CNXSMALLCAP", 
    "MCX": "^CNXSMALLCAP", "ANGELONE": "^CNXSMALLCAP", "CYIENT": "^CNXSMALLCAP", 
    "RADICO": "^CNXSMALLCAP", "KEI": "^CNXSMALLCAP", "SONACOMS": "^CNXSMALLCAP", 
    "CAMS": "^CNXSMALLCAP", "APARINDS": "^CNXSMALLCAP", "KAYNES": "^CNXSMALLCAP", 
    "TEJASNET": "^CNXSMALLCAP", "CHALET": "^CNXSMALLCAP", "PVRINOX": "^CNXSMALLCAP",
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
