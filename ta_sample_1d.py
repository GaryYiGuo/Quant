import pandas as pd
import pandas_ta as ta
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import date, timedelta
from pathlib import Path



pd.set_option('display.max_columns', None) # Show all columns in the DataFrame

# Download historical stock data from Yahoo Finance
# 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
# Minute Data: 7 days
# 2 Minute Data: 60 days
# 5 Minute Data: 60 days
# 15 Minute Data: 60 days
# 30 Minute Data: 60 days
# Hourly Data: 730 days
# Daily/Weekly/Monthly: No limits
symbol = "TD.TO"
start_date = (date.today() - timedelta(days=3650)).strftime("%Y-%m-%d") # 3650 days ago
end_date = date.today().strftime("%Y-%m-%d") # Today
#print(f"Downloading data for {symbol} from {start_date} to {end_date}")
interval="1d"
auto_adjust=True

# pandas_ta forwards a `proxy` argument to yfinance, which is no longer accepted
# by newer yfinance releases. Patch that compatibility gap before loading data.
try:
    from yfinance.base import PriceHistory
except ImportError:
    PriceHistory = None

if PriceHistory is not None:
    original_history = PriceHistory.history

    def _compatible_history(self, *args, **kwargs):
        kwargs.pop("proxy", None)
        return original_history(self, *args, **kwargs)

    PriceHistory.history = _compatible_history

output_dir = Path(__file__).resolve().parent
output_dir.mkdir(exist_ok=True)

df = pd.DataFrame().ta.ticker(symbol, start=start_date, end=end_date, interval=interval, auto_adjust=auto_adjust,) 

df=df.rename(columns={'Stock Splits':'Stock_Splitsose'})
df['symbol']=symbol
df['Datetime_str']=df.index.strftime('%Y-%m-%d')
#df.head(10) # Show the first 10 rows

#=================== Technical Analysis ====================
# Simple Moving Average, SMA, average of a selected range of prices, usually closing prices
df.ta.sma(length=5, append=True) 
df.ta.sma(length=20, append=True)  
df.ta.sma(length=250, append=True)  
#Exponential Moving Average, EMA, greater emphasis on recent price data, more responsive to price changes
df.ta.ema(length=5, append=True) 
df.ta.ema(length=20, append=True)  
df.ta.ema(length=250, append=True)  

#Relative Strength Index, RSI, momentum oscillator that measures the speed and change of price movements
df.ta.rsi(close=df['Close'], length=14, append=True) # RSI with default parameters

#MACD, Moving Average Convergence Divergence, trend-following momentum indicator
df.ta.macd(close=df['Close'], fast=12, slow=26, signal=9, append=True) # MACD with default parameters

#Bollinger Bands, volatility bands placed above and below a moving average
# Bollinger Bands with default parameters
# The columns added will be: BBM_20_2.0, BBU_20_2.0, BBL_20_2.0
# BBM: Middle Band, BBU: Upper Band, BBL: Lower Band
df.ta.bbands(close=df['Close'], length=20, std=2, append=True) 


#KDJ, Stochastic Oscillator, momentum indicator comparing a particular closing price 
# to a range of its prices over a certain period of time
# The columns added will be: K_14_3_3, D_14_3_3, J_14_3_3
# K: %K line, D: %D line, J: %J line
df.ta.kdj(close=df['Close'], high=df['High'], low=df['Low'], k=14, d=3, smooth_k=3, append=True) # KDJ with default parameters

# df.tail(10) # Show the last 10 rows


# Save the DataFrame to an HDF5 file when PyTables is available
h5_path = output_dir / f"{symbol}_{interval}_ta.h5"
try:
    df.to_hdf(path_or_buf=h5_path, key=symbol.replace(".","_"), mode="a")
except ImportError:
    print(f"PyTables not installed; skipped HDF5 export to {h5_path}")
# Read the DataFrame from the HDF5 file
# df=pd.read_hdf(path_or_buf=r"G:\stock\Quant\CA_Bank_10yrs_ta.h5", key=symbol) 



#=================== plotly candlestick chart ====================
fig=go.Figure(data=[go.Candlestick(x=df.Datetime_str,
                open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'])],
                layout=go.Layout(title=f"{symbol} Price interval in {interval}", yaxis_title="Price (CAD)", 
                                 xaxis=dict(
                    title="Datetime",
                    nticks=20,  # Set number of ticks on x-axis
                    rangeslider=dict(visible=False),
                    type="category"  # Set x-axis type to 'category' to avoid datetime formatting
                )))
output_file = output_dir / f"{symbol}_{interval}_ta_Price.html"
fig.write_html(output_file)


#=================== plotly candlestick chart with MACD ====================
fig=make_subplots(rows=2, cols=1, shared_xaxes=True,
                    vertical_spacing=0.1,
                    row_heights=[0.7, 0.3]) # Adjust row heights as desired

# Add Candlestick trace
fig.add_trace(go.Candlestick(x=df.Datetime_str, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close']), row=1, col=1)

# Add MACD traces
fig.add_trace(go.Scatter(x=df.Datetime_str, y=df['MACD_12_26_9'], mode='lines', name='MACD', line=dict(color='blue', width=1)), row=2, col=1)
fig.add_trace(go.Scatter(x=df.Datetime_str, y=df['MACDs_12_26_9'], mode='lines', name='Signal Line', line=dict(color='orange', width=1)), row=2, col=1)
fig.add_trace(go.Bar(x=df.Datetime_str, y=df['MACDh_12_26_9'], name='MACD Histogram', 
                     marker_color=np.where(df['MACDh_12_26_9'] >= 0, 'green', 'red')), row=2, col=1)


fig.update_yaxes(title_text="Price (CAD)", row=1, col=1)
fig.update_yaxes(title_text="MACD", row=2, col=1)   
fig.update_xaxes(rangeslider_visible=False, nticks=20, type='category', row=1, col=1)
fig.update_xaxes(rangeslider_visible=False, nticks=20, type='category', row=2, col=1)

fig.update_layout(showlegend=True, title_text=f"{symbol} Price interval in {interval} with MACD")

output_file = output_dir / f"{symbol}_{interval}_ta_Price_MACD.html"
fig.write_html(output_file)





   