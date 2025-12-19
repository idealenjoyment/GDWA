import plotly.express as px
import plotly.graph_objects as go
import pandas as pd

def plot_normalized_performance(df, title="Gold-Denominated Performance (Indexed to 100)"):
    """
    Line chart for normalized asset values.
    """
    fig = px.line(df, title=title)
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Value (Base 100 in Gold)",
        legend_title="Asset",
        hovermode="x unified",
        template="plotly_dark"
    )
    return fig

def plot_drawdown_heatmap(df):
    """
    Shows drawdowns. Since we want 'small multiples' or togglable, 
    but for a summary view, a line chart of drawdowns is often clearer than heatmap 
    if there are few assets. User asked for 'Underwater drawdown chart - One chart per asset (small multiples)'.
    
    We can do a Facet plot or just overlaid lines for now (easier to read interactively).
    Let's try overlaid lines first, but if too messy, we can refactor.
    """
    # Calculate drawdown
    rolling_max = df.cummax()
    drawdown = (df - rolling_max) / rolling_max
    
    fig = px.area(drawdown, title="Underwater Drawdown vs Gold")
    fig.update_layout(
         xaxis_title="Date",
         yaxis_title="Drawdown %",
         template="plotly_dark",
         hovermode="x unified"
    )
    return fig

def plot_correlation_heatmap(df, window_days=365):
    """
    Correlation of Gold-Denominated Returns.
    """
    returns = df.pct_change(fill_method=None).dropna()
    # Rolling correlation is complex to visualize for *all pairs* over time.
    # Usually a static heatmap of the *current* or *average* correlation over the selected period is best.
    # The requirement says 'Rolling 1-year correlation Heatmap'. 
    # This might mean a heatmap of the *latest* rolling window, OR a time series of correlations.
    # A time series of correlations for N assets is N*(N-1)/2 lines (messy).
    # Let's provide a Heatmap of the correlation over the ENTIRE selected range.
    
    corr_matrix = returns.corr()
    
    fig = px.imshow(corr_matrix, 
                    text_auto=True, 
                    title=f"Correlation Matrix (Daily Returns, Gold Denominated)",
                    color_continuous_scale="RdBu",
                    zmin=-1, zmax=1)
    fig.update_layout(template="plotly_dark")
    return fig

def plot_rolling_vol(df, window=30):
    """
    Rolling annualized volatility.
    """
    returns = df.pct_change(fill_method=None).dropna()
    rolling_vol = returns.rolling(window=window).std() * (252**0.5)
    
    fig = px.line(rolling_vol, title=f"Rolling {window}-Day Annualized Volatility")
    fig.update_layout(
        yaxis_title="Annualized Volatility",
        template="plotly_dark"
    )
    return fig
