import pandas as pd
import numpy as np
from gold_processor import process_data

def test_gold_denomination():
    # Mock Data
    dates = pd.date_range("2023-01-01", periods=3)
    data = {
        "GC=F": [1800.0, 1900.0, 2000.0],   # Gold (USD)
        "^GSPC": [3800.0, 3900.0, 4000.0],  # SP500 (USD)
        "INR=X": [83.0, 83.5, 84.0],        # USD/INR Rate (1 USD = X INR) - Wait, Yahoo INR=X is usually rate USDINR.
        "^NSEI": [18000.0, 18200.0, 18400.0] # NIFTY (INR)
    }
    raw_df = pd.DataFrame(data, index=dates)
    
    ticker_map = {
        "GOLD": "GC=F",
        "SP500": "^GSPC",
        "INR": "INR=X",
        "NIFTY": "^NSEI",
        "USD": "USD"
    }
    
    # processor.process_data expects currency mapping for asset type
    currency_map = {
        "GOLD": "USD",
        "SP500": "USD",
        "INR": "ExchRate", # 1/Price is Value in USD
        "NIFTY": "INR",     # Needs to be divided by INR rate
        "USD": "USD_CURRENCY"
    }
    
    # Expected Logic:
    # Day 1:
    # Gold $1800
    # SP500 $3800 -> Gold Terms: 3800/1800 = 2.1111
    # NIFTY 18000 INR. Rate 83. -> USD Val = 18000/83 = 216.867. -> Gold Terms: 216.867/1800 = 0.12048
    
    normalized_df, metrics = process_data(raw_df, ticker_map, currency_map)
    
    print("Computed Data Field Preview:")
    print(normalized_df.head())
    
    # Check Normalization (Day 1 should be 100)
    assert np.isclose(normalized_df.iloc[0]["SP500"], 100.0), "SP500 start not 100"
    assert np.isclose(normalized_df.iloc[0]["NIFTY"], 100.0), "NIFTY start not 100"
    assert np.isclose(normalized_df.iloc[0]["GOLD"], 100.0), "GOLD start not 100"

    print("\nNormalization Check: PASSED")
    
    # Check Day 2 Value for SP500
    # Day 2 Raw: SP500=3900, Gold=1900. Ratio = 2.0526
    # Day 1 Raw Ratio: 3800/1800 = 2.1111
    # Normalized Day 2 = (2.0526 / 2.1111) * 100 = 97.23
    
    val_day2 = normalized_df.iloc[1]["SP500"]
    expected_day2 = ( (3900/1900) / (3800/1800) ) * 100
    
    print(f"SP500 Day 2: Got {val_day2}, Expected {expected_day2}")
    assert np.isclose(val_day2, expected_day2), "SP500 Day 2 calculation incorrect"
    
    print("Gold Denomination Logic Check: PASSED")

    # Check Day 2 Value for NIFTY (Currency Converted)
    # Day 1: (18000/83) / 1800 = 0.1204819
    # Day 2: (18200/83.5) / 1900 = (217.964) / 1900 = 0.114718
    # Norm Day 2 = (0.114718 / 0.1204819) * 100 = 95.216
    
    val_nifty_day2 = normalized_df.iloc[1]["NIFTY"]
    expected_nifty_2 = ( (18200/83.5)/1900 ) / ( (18000/83)/1800 ) * 100
    print(f"NIFTY Day 2: Got {val_nifty_day2}, Expected {expected_nifty_2}")
    assert np.isclose(val_nifty_day2, expected_nifty_2), "NIFTY Day 2 calculation incorrect"

    print("Currency Conversion Logic Check: PASSED")
    print("Verification Script Completed Successfully.")

if __name__ == "__main__":
    test_gold_denomination()
