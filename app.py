import streamlit as st
import datetime
import pandas as pd
import os
import gold_loader
import gold_processor
import charts
import importlib
importlib.reload(gold_loader)
importlib.reload(gold_processor)
importlib.reload(charts)

# Set page config
st.set_page_config(
    page_title="Gold-Denominated Global Asset Dashboard",
    page_icon="🪙",
    layout="wide"
)

st.title("🪙 Gold-Denominated Global Asset Dashboard")
st.markdown("""
This dashboard allows you to benchmark major global assets against **Gold**.
By stripping away fiat currency volatility, we can see the *true* purchasing power performance of assets.
""")

# --- Sidebar ---
st.sidebar.header("Configuration")

# Date Range
default_start = datetime.date.today() - datetime.timedelta(days=365*20)
default_end = datetime.date.today()

start_date = st.sidebar.date_input("Start Date", default_start)
end_date = st.sidebar.date_input("End Date", default_end)

if start_date >= end_date:
    st.sidebar.error("Error: End Date must be after Start Date.")
    st.stop()

# Asset Selection
st.sidebar.subheader("Select Assets")
ticker_map = gold_loader.get_ticker_map()
all_assets = sorted(list(ticker_map.keys()))

# Cache Status
if os.path.exists(gold_loader.ASSETS_DIR):
    files = [f for f in os.listdir(gold_loader.ASSETS_DIR) if f.endswith('.csv')]
    if files:
        # Get the latest modified file in the directory
        latest_file = max([os.path.join(gold_loader.ASSETS_DIR, f) for f in files], key=os.path.getmtime)
        mtime = os.path.getmtime(latest_file)
        last_updated = datetime.datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M')
        st.sidebar.caption(f"📂 Local cache ({len(files)} assets) last updated: {last_updated}")
    else:
        st.sidebar.caption("📂 Local cache folder empty.")
else:
    st.sidebar.caption("📂 No local cache found.")

# Default selection (robust check)
desired_defaults = ["SP500", "NIFTY", "SILVER", "USD", "INR"]
default_assets = [a for a in desired_defaults if a in all_assets]

selected_assets = st.sidebar.multiselect("Assets to Compare", all_assets, default=default_assets)

if not selected_assets:
    st.warning("Please select at least one asset to compare.")
    st.stop()
    
# Always include Gold for calculation purposes (it is the denominator)
fetch_list = set(selected_assets)
fetch_list.add("GOLD")

# Add dependent currencies if indices are selected
deps = {
    "NIFTY": "INR",
    "NIKKEI": "JPY",
}

final_fetch_list = set(fetch_list)
for asset in fetch_list:
    if asset in deps:
        final_fetch_list.add(deps[asset])

# --- Data Loading / Refreshing ---

# Persistent state for raw data
if 'raw_df' not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()

# Build complete ordered fetch list: base assets first, then selected assets
# Base assets = GOLD + any currency dependencies
base_assets = ["GOLD"]
for asset in selected_assets:
    if asset in deps and deps[asset] not in base_assets:
        base_assets.append(deps[asset])

# Selected assets (excluding GOLD, USD, and already-in-base currencies)
asset_queue = [a for a in selected_assets if a not in base_assets and a != "USD"]
all_to_load = base_assets + asset_queue
total_steps = len(all_to_load)

# Add Refresh Button to the Sidebar
st.sidebar.divider()
refresh_clicked = st.sidebar.button("🔄 Refresh Data", type="primary", use_container_width=True, help="Fetch latest data from Yahoo Finance into local cache")

if refresh_clicked:
    progress_bar = st.progress(0, text="Preparing to refresh data...")
    status_container = st.empty()
    
    for step_idx, asset_name in enumerate(all_to_load):
        ticker = gold_loader.get_ticker_map().get(asset_name)
        if not ticker: continue
        
        progress_pct = (step_idx) / total_steps
        progress_bar.progress(progress_pct, text=f"Fetching {asset_name} ({step_idx + 1}/{total_steps})...")
        
        with status_container.status(f"Syncing {asset_name}...") as s:
            gold_loader.fetch_data_with_persistence([ticker], start_date, end_date)
            s.update(label=f"✅ {asset_name} synced", state="complete")
            
    progress_bar.empty()
    status_container.empty()

# Always read what's currently in cache for the required tickers
all_tickers = [gold_loader.get_ticker_map().get(a) for a in all_to_load if gold_loader.get_ticker_map().get(a)]
st.session_state.raw_df = gold_loader.get_close_prices(all_tickers, start_date, end_date)

successfully_loaded = []
gold_ticker = gold_loader.get_ticker_map()["GOLD"]

# Validate that GOLD loaded successfully (required for everything else)
if gold_ticker not in st.session_state.raw_df.columns or st.session_state.raw_df[gold_ticker].isna().all():
    st.error("⚠️ **Gold data (GC=F) is currently unavailable in the local cache.**")
    st.info("Please click the '🔄 Refresh Data' button in the sidebar to download data from Yahoo Finance.")
    st.stop()
else:
    # Track successfully loaded selected assets
    for asset_name in selected_assets:
        if asset_name == "GOLD": continue
        t = gold_loader.get_ticker_map().get(asset_name)
        if t and t in st.session_state.raw_df.columns and not st.session_state.raw_df[t].isna().all():
            successfully_loaded.append(asset_name)

# USD is synthetic — always available
if "USD" in selected_assets:
    successfully_loaded.append("USD")

# --- Render Charts (single pass) ---

if not st.session_state.raw_df.empty:
    st.sidebar.success(f"✅ Active: {', '.join(successfully_loaded)}")
else:
    st.sidebar.warning("No data in session state.")

if successfully_loaded:
    try:
        render_friendly = list(set(base_assets + successfully_loaded))
        current_ticker_map = {
            a: gold_loader.get_ticker_map()[a]
            for a in render_friendly
            if a in gold_loader.get_ticker_map()
        }

        normalized_df, metrics_df = gold_processor.process_data(
            st.session_state.raw_df,
            current_ticker_map,
            gold_loader.CURRENCY_MAPPING,
        )

        display_cols = [c for c in selected_assets if c in normalized_df.columns]

        if display_cols:
            final_ts_df = normalized_df[display_cols]
            final_metrics_df = metrics_df.loc[display_cols]

            st.subheader("📈 Performance vs Gold")
            st.plotly_chart(
                charts.plot_normalized_performance(final_ts_df), use_container_width=True
            )

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("📉 Drawdowns")
                st.plotly_chart(
                    charts.plot_drawdown_heatmap(final_ts_df), use_container_width=True
                )
            with col2:
                st.subheader("📊 Correlation Matrix")
                st.plotly_chart(
                    charts.plot_correlation_heatmap(final_ts_df), use_container_width=True
                )

            st.subheader("⚡ Rolling Volatility (30D)")
            st.plotly_chart(
                charts.plot_rolling_vol(final_ts_df), use_container_width=True
            )

            st.subheader("📋 Summary Statistics")
            st.dataframe(
                final_metrics_df.style.format("{:.2%}"), use_container_width=True
            )

    except Exception as e:
        st.error(f"Error rendering charts: {e}")

st.divider()
st.caption("Data source: Yahoo Finance. 'Price in Gold' calculated as USD Price of Asset / USD Price of Gold.")

