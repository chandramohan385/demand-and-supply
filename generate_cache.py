import os
import json
import time
from core.scanner import scan_tickers
from app import STOCK_LISTS, SECTOR_MAP

def generate_full_market_cache():
    all_stocks = STOCK_LISTS.get('TOTAL_MARKET', [])
    if not all_stocks:
        with open('core/stock_lists.json') as f:
            sl = json.load(f)
            all_stocks = sl.get('NSE_ALL', sl.get('NIFTY_500', []))
    
    print(f"Total stocks to scan for cache: {len(all_stocks)}")
    cache_file = os.path.join(os.path.dirname(__file__), 'core', 'market_cache.json')
    
    existing_cache = {}
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                existing_cache = json.load(f)
        except Exception:
            existing_cache = {}

    for interval in ['1d', '1wk']:
        print(f"\n--- Scanning Total Market for interval: {interval} ---")
        t0 = time.time()
        # Scan with is_total_market=True
        # To avoid rate limits, we scan the top 500 liquid stocks first
        top_universe = STOCK_LISTS.get('NIFTY_500', all_stocks[:500])
        results = scan_tickers(top_universe, interval=interval, sector_map=SECTOR_MAP, is_total_market=True)
        print(f"Scan for {interval} completed in {time.time()-t0:.2f}s with {len(results)} elite setups found")
        
        best_pick = results[0] if results else None
        existing_cache[interval] = {
            'timestamp': time.time(),
            'total_scanned': len(all_stocks),
            'best_pick': best_pick,
            'data': results
        }

    with open(cache_file, 'w') as f:
        json.dump(existing_cache, f, separators=(',', ':'))
    print(f"\nCache successfully saved to {cache_file}!")

if __name__ == '__main__':
    generate_full_market_cache()
