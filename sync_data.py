import gold_loader
import pandas as pd
import datetime
import time
import random
import os

def full_sync():
    print("🚀 Starting Full Historical Sync for all assets...")
    
    # 1. Define the full range
    # Let's go back 25 years to be safe
    end_date = datetime.date.today()
    start_date = end_date - datetime.timedelta(days=365*25)
    
    ticker_map = gold_loader.get_ticker_map()
    all_friendly_names = sorted(list(ticker_map.keys()))
    
    print(f"Target Period: {start_date} to {end_date}")
    print(f"Total Assets to Sync: {len(all_friendly_names)}")
    print("-" * 40)

    # 2. Iterate through each asset and sync
    for i, name in enumerate(all_friendly_names):
        ticker = ticker_map[name]
        if name == "USD":
            print(f"[{i+1}/{len(all_friendly_names)}] Skipping synthetic asset: {name}")
            continue
            
        print(f"[{i+1}/{len(all_friendly_names)}] Syncing {name} ({ticker})...")
        
        try:
            # fetch_data_with_persistence already handles merging and saving
            # We call it for each asset specifically to avoid massive batch requests
            df = gold_loader.fetch_data_with_persistence([ticker], start_date, end_date)
            
            if not df.empty:
                print(f"✅ Success: {len(df)} rows found/updated.")
            else:
                print(f"⚠️ Warning: No data returned for {name}.")
        except Exception as e:
            print(f"❌ Error syncing {name}: {e}")
            
        # Voluntary delay to be nice to Yahoo Finance
        delay = random.uniform(1.0, 3.0)
        time.sleep(delay)

    print("-" * 40)
    print("✨ Sync Complete!")
    
    if os.path.exists(gold_loader.ASSETS_DIR):
        files = [f for f in os.listdir(gold_loader.ASSETS_DIR) if f.endswith('.csv')]
        print(f"Total assets in cache: {len(files)}")
        for f in files:
            path = os.path.join(gold_loader.ASSETS_DIR, f)
            df = pd.read_csv(path, index_col=0)
            print(f" - {f}: {len(df)} rows")
        print(f"Storage directory: {gold_loader.ASSETS_DIR}")

if __name__ == "__main__":
    full_sync()
