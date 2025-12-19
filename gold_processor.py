import pandas as pd
import numpy as np

def calculate_metrics(gold_denominated_series):
    """
    Calculates key metrics for a single asset series:
    - CAGR
    - Annualized Volatility
    - Max Drawdown
    """
    # CAGR
    start_val = gold_denominated_series.iloc[0]
    end_val = gold_denominated_series.iloc[-1]
    years = (gold_denominated_series.index[-1] - gold_denominated_series.index[0]).days / 365.25
    if years <= 0:
        cagr = 0.0
    else:
        cagr = (end_val / start_val) ** (1 / years) - 1

    # Returns
    # Using fill_method=None to avoid deprecation warning as per Pandas 2.1+
    daily_returns = gold_denominated_series.pct_change(fill_method=None).dropna()
    
    # Volatility (Annualized)
    volatility = daily_returns.std() * np.sqrt(252)
    
    # Max Drawdown
    rolling_max = gold_denominated_series.cummax()
    drawdown = (gold_denominated_series - rolling_max) / rolling_max
    max_drawdown = drawdown.min()
    
    return {
        "CAGR": cagr,
        "Volatility": volatility,
        "Max Drawdown": max_drawdown
    }

def process_data(raw_data, ticker_map, currency_map):
    """
    Inputs:
    - raw_data: DataFrame with columns as Tickers (Close prices).
    - ticker_map: Dict mapping 'Friendly Name' -> 'Ticker'.
    - currency_map: Dict mapping 'Friendly Name' -> 'Currency Code' (or 'ExchRate').
    
    Returns:
    - gold_denominated_df: DataFrame of assets priced in Gold, normalized to 100.
    - metrics: Dict of metrics per asset.
    """
    df = raw_data.copy()
    
    # Invert mapping to Ticker -> Friendly Name for easier column access
    inv_map = {v: k for k, v in ticker_map.items()}
    df.rename(columns=inv_map, inplace=True)
    
    # Ensure Gold is present
    if "GOLD" not in df.columns:
        raise ValueError("Gold price data missing from result.")
    
    gold_price_usd = df["GOLD"]
    
    processed_df = pd.DataFrame(index=df.index)
    
    # Process each asset
    for asset_name in ticker_map.keys():
        if asset_name == "GOLD":
            processed_df[asset_name] = 1.0 # Gold in terms of Gold is 1 (or 100 normalized)
            continue
            
        asset_type = currency_map.get(asset_name)
        
        asset_price_usd = None
        
        if asset_type == "USD_CURRENCY":
            # The asset IS the US Dollar. Its price in USD is 1.0.
            asset_price_usd = 1.0
        else:
            if asset_name not in df.columns:
                # If it's a selected asset but missing from data (e.g. failed fetch)
                # We skip or handle error. For now, skip to avoid Crash.
                continue
            asset_price_raw = df[asset_name]
            
            if asset_type == "USD":
                asset_price_usd = asset_price_raw
                
            elif asset_type == "ExchRate":
                # Price_USD = 1 / Rate
                asset_price_usd = 1.0 / asset_price_raw
                
            elif asset_type == "INR":
                usdinr = df["INR"]
                asset_price_usd = asset_price_raw / usdinr
                
            elif asset_type == "JPY":
                usdjpy = df["JPY"]
                asset_price_usd = asset_price_raw / usdjpy
                
            elif asset_type == "CNY":
                usdcny = df["CNY"]
                asset_price_usd = asset_price_raw / usdcny
            
        # Denominate in Gold
        # Price_Au = Price_USD / Price_Gold_USD
        processed_df[asset_name] = asset_price_usd / gold_price_usd

    # Normalize to 100 at the first available data point
    def normalize_series(s):
        first_valid = s.first_valid_index()
        if first_valid is not None:
            first_val = s.loc[first_valid]
            if first_val != 0:
                return 100 * s / first_val
        return s
        
    normalized_df = processed_df.apply(normalize_series)
    
    # Calculate metrics
    metrics = {}
    for col in normalized_df.columns:
        metrics[col] = calculate_metrics(normalized_df[col])
        
    return normalized_df, pd.DataFrame(metrics).T
