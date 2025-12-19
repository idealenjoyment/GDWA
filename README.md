# 🪙 Gold-Denominated Global Asset Dashboard

Benchmark major global assets against **Gold** (XAU) to see their true purchasing power performance, stripped of fiat currency inflation and volatility.

![Dashboard Preview](https://github.com/user-attachments/assets/vibrant-ui-placeholder) 

## 🚀 Features

-   **Gold-Denominated Performance**: Automatically converts asset prices from native currencies (USD, INR, JPY, etc.) into Gold.
-   **Multi-Asset Support**: Benchmarks S&P 500, Nasdaq, Nifty 50, Nikkei 225, Bitcoin, Ethereum, Silver, and more.
-   **Full OHLCV Sync**: Standalone sync script to download decades of historical data locally.
-   **Optimized Persistence**: Assets are stored in individual CSV files at `data/assets/` for maximum portability and fast loading.
-   **Interactive Analytics**:
    *   Dynamic performance series (indexed to 100).
    *   Rolling 30-day volatility.
    *   Underwater Drawdown heatmaps.
    *   Asset correlation matrices.
-   **Incremental Loading**: Responsive Streamlit UI that renders data progressively as it becomes available.

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/gold-denominated-assets.git
   cd gold-denominated-assets
   ```

2. **Install dependencies**:
   ```bash
   pip install streamlit yfinance pandas plotly numpy
   ```

3. **(Optional) Run Full Sync**:
   Download historical data for all assets to minimize API calls:
   ```bash
   python sync_data.py
   ```

## 📈 Usage

Start the dashboard locally:
```bash
streamlit run app.py
```

- **Configuration**: Use the sidebar to select your date range and the assets you want to benchmark.
- **Cache Management**: The sidebar displays the status of your local data cache.

## 📂 Project Structure

- `app.py`: Main Streamlit application.
- `gold_loader.py`: Data fetching, local persistence, and rate-limiting logic.
- `gold_processor.py`: Financial calculations (Gold denomination, CAGR, Volatility, Drawdowns).
- `charts.py`: Plotly visualization templates.
- `sync_data.py`: CLI script for full historical data synchronization.
- `data/assets/`: Local storage for asset OHLCV data.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## ⚠️ Disclaimer

*This tool is for informational purposes only. It is not financial advice. Data is sourced from Yahoo Finance and may contain inaccuracies.*
