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
desired_defaults = ["SP500", "NIFTY", "SILVER", "USD", "BTC"]
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

# --- Incremental Data Loading ---

# Placeholders for UI components that will be updated incrementally
main_chart_placeholder = st.empty()
col1, col2 = st.columns(2)
drawdown_placeholder = col1.empty()
corr_placeholder = col2.empty()
vol_placeholder = st.empty()
metrics_overlay = st.empty()

# Persistent state for raw data
if 'raw_df' not in st.session_state:
    st.session_state.raw_df = pd.DataFrame()

# We need GOLD first as it is the denominator
initial_assets = ["GOLD"]
# Add dependencies (like INR for Nifty)
for asset in selected_assets:
    if asset in deps:
        initial_assets.append(deps[asset])

# Combine into a unique list of tickers to fetch
to_fetch_immediately = list(set([gold_loader.get_ticker_map()[a] for a in initial_assets if a in gold_loader.get_ticker_map()]))

with st.spinner("Fetching base data (Gold & Currencies)..."):
    base_data = gold_loader.fetch_data_with_persistence(to_fetch_immediately, start_date, end_date)
    # Check if we got GOLD
    gold_ticker = gold_loader.get_ticker_map()["GOLD"]
    if gold_ticker in base_data.columns and not base_data[gold_ticker].isna().all():
        st.session_state.raw_df = base_data
    else:
        st.error("⚠️ **Gold data (GC=F) is currently unavailable.**")
        st.info("This is usually due to Yahoo Finance rate limiting. Please wait a minute and click 'Retry'.")
        if st.button("Retry Load"):
            st.rerun()
        st.stop()

# Debug: Show column count
if not st.session_state.raw_df.empty:
    st.sidebar.success(f"✅ Cached {len(st.session_state.raw_df.columns)} assets")
else:
    st.sidebar.warning("No data in session state.")

# Loop through selected assets incrementally
successfully_loaded = []
for asset_name in selected_assets:
    if asset_name == "USD":
        successfully_loaded.append("USD")
        continue # Synthetic handled in processor
    if asset_name == "GOLD":
        continue # Benchmark
        
    ticker = gold_loader.get_ticker_map().get(asset_name)
    if not ticker:
        continue
        
    # Check if we already have this ticker populated in session state
    if ticker not in st.session_state.raw_df.columns or st.session_state.raw_df[ticker].isna().all():
        with st.status(f"Loading {asset_name}...") as s:
            asset_data = gold_loader.fetch_data_with_persistence([ticker], start_date, end_date)
            if not asset_data.empty:
                # Merge columns safely using concat (handles index alignment)
                st.session_state.raw_df = pd.concat([st.session_state.raw_df, asset_data], axis=1)
                st.session_state.raw_df = st.session_state.raw_df.loc[:, ~st.session_state.raw_df.columns.duplicated()]
                st.session_state.raw_df = st.session_state.raw_df[~st.session_state.raw_df.index.duplicated(keep='last')].sort_index()
                s.update(label=f"{asset_name} loaded!", state="complete")
            else:
                s.update(label=f"Failed to load {asset_name} (Rate limited or missing data)", state="error")

    # If it's now in the session state (or was already), add to render list
    if ticker in st.session_state.raw_df.columns and not st.session_state.raw_df[ticker].isna().all():
        successfully_loaded.append(asset_name)

    # Update the UI with everything loaded so far
    try:
        # Determine available assets for this iteration
        # Always include GOLD and dependencies
        render_friendly = list(set(initial_assets + successfully_loaded))
        current_ticker_map = {a: gold_loader.get_ticker_map()[a] for a in render_friendly if a in gold_loader.get_ticker_map()}
        
        normalized_df, metrics_df = gold_processor.process_data(
            st.session_state.raw_df, 
            current_ticker_map, 
            gold_loader.CURRENCY_MAPPING
        )
        
        # Filter for display (exclude benchmarking helpers like INR/JPY unless selected)
        display_cols = [c for c in selected_assets if c in normalized_df.columns]
        if not display_cols:
            continue
            
        final_ts_df = normalized_df[display_cols]
        final_metrics_df = metrics_df.loc[display_cols]

        # Update Placeholders
        with main_chart_placeholder.container():
            st.subheader("📈 Performance vs Gold")
            st.plotly_chart(charts.plot_normalized_performance(final_ts_df), use_container_width=True)

        with drawdown_placeholder.container():
            st.subheader("📉 Drawdowns")
            st.plotly_chart(charts.plot_drawdown_heatmap(final_ts_df), use_container_width=True)

        with corr_placeholder.container():
            st.subheader("📊 Correlation Matrix")
            st.plotly_chart(charts.plot_correlation_heatmap(final_ts_df), use_container_width=True)

        with vol_placeholder.container():
            st.subheader("⚡ Rolling Volatility (30D)")
            st.plotly_chart(charts.plot_rolling_vol(final_ts_df), use_container_width=True)

        with metrics_overlay.container():
            st.subheader("📋 Summary Statistics")
            st.dataframe(final_metrics_df.style.format("{:.2%}"), use_container_width=True)

    except Exception as e:
        if asset_name in successfully_loaded:
            st.error(f"Error rendering {asset_name}: {e}")

# Update sidebar status once more at the end
if not st.session_state.raw_df.empty:
    loaded_tickers = [t for t in st.session_state.raw_df.columns if not st.session_state.raw_df[t].isna().all()]
    st.sidebar.success(f"✅ Active: {', '.join(successfully_loaded)}")

st.divider()
st.caption("Data source: Yahoo Finance. 'Price in Gold' calculated as USD Price of Asset / USD Price of Gold.")
