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

    for interval in ['1d', '1wk', '1mo', '3mo']:
        print(f"\n--- Scanning Total Market for interval: {interval} ---")
        t0 = time.time()
        # Full market scan across the complete universe of 2,349 NSE stocks
        top_universe = all_stocks
        results_overall, results_demand, results_supply = scan_tickers(
            top_universe, 
            interval=interval, 
            sector_map=SECTOR_MAP, 
            is_total_market=True, 
            return_splits=True
        )
        print(f"Scan for {interval} completed in {time.time()-t0:.2f}s with {len(results_overall)} overall, {len(results_demand)} Demand, {len(results_supply)} Supply setups found")
        
        existing_cache[interval] = {
            'timestamp': time.time(),
            'total_scanned': len(all_stocks),
            'best_pick': results_overall[0] if results_overall else None,
            'best_demand_pick': results_demand[0] if results_demand else None,
            'best_supply_pick': results_supply[0] if results_supply else None,
            'data': results_overall,
            'demand_data': results_demand,
            'supply_data': results_supply
        }

    with open(cache_file, 'w') as f:
        json.dump(existing_cache, f, separators=(',', ':'))
    print(f"\nCache successfully saved to {cache_file}!")

if __name__ == '__main__':
    generate_full_market_cache()
