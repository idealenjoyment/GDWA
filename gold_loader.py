import yfinance as yf
import pandas as pd
import streamlit as st
import os
import time
import random
import datetime

# Mapping of asset keys to Yahoo Finance Tickers
ASSET_TICKERS = {
    # Benchmark
    "GOLD": "GC=F",          # Gold Futures (USD)

    # Currencies
    "USD": "USD",            # US Dollar (Synthetic)
    "INR": "INR=X",          # USD/INR
    "JPY": "JPY=X",          # USD/JPY
    "CNY": "CNY=X",          # USD/CNY
    
    # Indices
    "NIFTY": "^NSEI",        # Nifty 50 (INR)
    "SP500": "^GSPC",        # S&P 500 (USD)
    "NASDAQ": "^IXIC",       # Nasdaq Composite (USD)
    "NIKKEI": "^N225",       # Nikkei 225 (JPY)

    # Commodities
    "SILVER": "SI=F",        # Silver Futures (USD)
    "CRUDE_BRENT": "BZ=F",   # Brent Crude Futures (USD)
    "COPPER": "HG=F",         # Copper Futures (USD)
    
    # Crypto (USD)
    "BTC": "BTC-USD",
    "ETH": "ETH-USD"
}

CURRENCY_MAPPING = {
    "NIFTY": "INR",
    "NIKKEI": "JPY",
    # Others are USD denominated natively by Yahoo (usually)
    "SP500": "USD",
    "NASDAQ": "USD",
    "GOLD": "USD",
    "SILVER": "USD",
    "CRUDE_BRENT": "USD",
    "COPPER": "USD",
    "USD": "USD_CURRENCY",
    "INR": "ExchRate", # Special handling
    "JPY": "ExchRate",
    "CNY": "ExchRate",
    "BTC": "USD",
    "ETH": "USD",
}

ASSETS_DIR = "data/assets/"

def get_asset_path(ticker):
    """Returns the filesystem path for a given ticker's OHLCV data."""
    # Clean ticker name for filename (remove ^ or = characters)
    clean_name = ticker.replace("^", "").replace("=", "").replace("/", "_")
    return os.path.join(ASSETS_DIR, f"{clean_name}.csv")

def retry_yf_download(tickers, start, end, max_retries=3):
    """
    Downloads data with exponential backoff for rate limits.
    Returns the full OHLCV dataframe.
    """
    if not tickers:
        return pd.DataFrame()
        
    for i in range(max_retries):
        # Even before first try, be a bit nice if we are in a loop
        time.sleep(random.uniform(0.5, 1.5))
        try:
            # We fetch OHLCV (all columns)
            data = yf.download(tickers, start=start, end=end, progress=False)
            if data is not None and not data.empty:
                return data
            # If empty but no exception, might be weekend or holiday
            return pd.DataFrame()
        except Exception as e:
            msg = str(e)
            if "Too Many Requests" in msg or "Rate limit" in msg:
                # More aggressive backoff: 5s, 15s, 45s...
                wait_time = (5 * (3 ** i)) + random.uniform(2, 5)
                warning_text = f"Yahoo rate limit hit. Retrying in {wait_time:.1f}s... (Attempt {i+1}/{max_retries})"
                print(warning_text)
                try:
                    st.toast(warning_text)
                except:
                    pass
                time.sleep(wait_time)
            else:
                print(f"YFinance Error: {e}")
                # Don't break on first error if it's intermittent, but for now we follow old logic
                break
    return pd.DataFrame()

def ensure_dataframe(data):
    if isinstance(data, pd.Series):
        return data.to_frame()
    return pd.DataFrame() if data is None else data

def load_asset_data(ticker):
    """Loads OHLCV data for a single asset from its CSV file."""
    path = get_asset_path(ticker)
    if os.path.exists(path):
        try:
            return pd.read_csv(path, index_col=0, parse_dates=True)
        except Exception as e:
            print(f"Error loading {ticker} from {path}: {e}")
    return pd.DataFrame()

def save_asset_data(ticker, df):
    """Saves OHLCV data for a single asset to its CSV file, merging with existing data."""
    if df.empty:
        return
        
    path = get_asset_path(ticker)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    existing_df = load_asset_data(ticker)
    if not existing_df.empty:
        # Merge and deduplicate
        combined = pd.concat([existing_df, df]).sort_index()
        combined = combined[~combined.index.duplicated(keep='last')]
    else:
        combined = df
        
    combined.to_csv(path)

def fetch_data_with_persistence(tickers, start_date, end_date):
    """
    Fetches OHLCV data for multiple tickers, syncing with local storage.
    Returns a combined 'Close' price dataframe for the requested range.
    """
    # Convert dates to datetime for comparison
    start_dt = pd.to_datetime(start_date)
    # yfinance 'Close' data for today might not be available yet.
    yesterday = datetime.datetime.now() - datetime.timedelta(days=1)
    end_dt = min(pd.to_datetime(end_date), pd.to_datetime(yesterday.date()))
    
    # Sync each ticker individually
    for ticker in tickers:
        if ticker == "USD": continue
        sync_asset(ticker, start_dt, end_dt)
        
    return get_close_prices(tickers, start_dt, end_dt)

def sync_asset(ticker, start_dt, end_dt):
    """Syncs a single asset's local storage with Yahoo Finance."""
    existing_df = load_asset_data(ticker)
    
    needs_fetch = False
    fetch_start = start_dt
    fetch_end = end_dt
    
    if existing_df.empty:
        needs_fetch = True
    else:
        cache_start = existing_df.index.min()
        cache_end = existing_df.index.max()
        
        if start_dt < cache_start:
            needs_fetch = True
            fetch_end = cache_start
        
        if end_dt > cache_end:
            needs_fetch = True
            fetch_start = cache_end + pd.Timedelta(days=1)
            fetch_end = end_dt

    if needs_fetch and fetch_start < fetch_end:
        new_data = retry_yf_download([ticker], fetch_start, fetch_end)
        if not new_data.empty:
            # Standardize to TZ-naive
            if new_data.index.tz is not None:
                new_data.index = new_data.index.tz_localize(None)
                
            # Flatten multi-index if it exists
            if isinstance(new_data.columns, pd.MultiIndex):
                new_data.columns = new_data.columns.get_level_values(0)
            save_asset_data(ticker, new_data)

def get_close_prices(tickers, start_date, end_date):
    """Combines 'Close' prices from individual asset files into a single dataframe."""
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    combined_close = pd.DataFrame()
    
    for ticker in tickers:
        if ticker == "USD":
            continue
            
        df = load_asset_data(ticker)
        if not df.empty and 'Close' in df.columns:
            # Standardize index to TZ-naive for safe joining
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            subset = df.loc[start_dt:end_dt, 'Close']
            # Using concat or join for better index safety
            if combined_close.empty:
                combined_close = subset.to_frame(name=ticker)
            else:
                combined_close = combined_close.join(subset.to_frame(name=ticker), how='outer')
            
    return combined_close.ffill()

def get_base_tickers():
    return list(ASSET_TICKERS.values())

def get_ticker_map():
    return ASSET_TICKERS
