from pathlib import Path

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

pd.set_option('display.max_columns', None) # Show all columns in the DataFrame

symbol = "TD.TO"
interval="1d"

output_dir = Path(__file__).resolve().parent
output_dir.mkdir(exist_ok=True)
h5_path = output_dir / f"{symbol}_{interval}_ta.h5"

df = pd.read_hdf(path_or_buf=h5_path, key=symbol.replace(".","_"))
#df.head(20)

# Chan theory kline containment relationship processing
def process_chan_containment(df):
    if 'Datetime' in df.columns:
        df = df.reset_index(drop=True)
    else:
        df = df.reset_index()
    df = df.copy()
    df['Direction'] = 0  # 0 is not sure Direction，1 is up，-1 is down
    df['Merged'] = False
    
    # the first K-line direction cannot be determined
    df.loc[0, 'Direction'] = 0
    
    i = 1
    while i < len(df):
        prev_idx = i - 1
        # find the previous unmerged K-line
        while prev_idx >= 0 and df.loc[prev_idx, 'Merged']:
            prev_idx -= 1
        
        if prev_idx < 0:
            df.loc[i, 'Direction'] = 0
            i += 1
            continue
            
        # check containment relationship
        prev_high = df.loc[prev_idx, 'High']
        prev_low = df.loc[prev_idx, 'Low']
        curr_high = df.loc[i, 'High']
        curr_low = df.loc[i, 'Low']
        
        # check containment relationship
        if (curr_high <= prev_high and curr_low >= prev_low) or \
           (curr_high >= prev_high and curr_low <= prev_low):
            
            # set direction
            if df.loc[prev_idx, 'Direction'] != 0:
                direction = df.loc[prev_idx, 'Direction']
            else:
                # if direction is not determined, compare with the previous K-line
                prev_prev_idx = prev_idx - 1
                while prev_prev_idx >= 0 and df.loc[prev_prev_idx, 'Merged']:
                    prev_prev_idx -= 1
                
                if prev_prev_idx < 0:
                    direction = 1 if curr_high > prev_high else -1
                else:
                    prev_prev_high = df.loc[prev_prev_idx, 'High']
                    prev_prev_low = df.loc[prev_prev_idx, 'Low']
                    
                    if prev_prev_high < prev_high:
                        direction = 1
                    elif prev_prev_low > prev_low:
                        direction = -1
                    else:
                        direction = 1 if curr_high > prev_high else -1
            
            # (Adjust the previous K-line's high and low based on the direction)
            if direction == 1:  # upward
                new_high = max(prev_high, curr_high)
                new_low = max(prev_low, curr_low)
            else:  # downward
                new_high = min(prev_high, curr_high)
                new_low = min(prev_low, curr_low)
            
            #  reset previous k-line high and low
            df.loc[prev_idx, 'High'] = new_high
            df.loc[prev_idx, 'Low'] = new_low
            
            # mark current K-line as merged
            df.loc[i, 'Merged'] = True
            df.loc[prev_idx, 'Direction'] = direction
            
        else:
            # non-containment relationship, determine direction
            if curr_high > prev_high and curr_low > prev_low:
                df.loc[i, 'Direction'] = 1
            elif curr_high < prev_high and curr_low < prev_low:
                df.loc[i, 'Direction'] = -1
            else:
                df.loc[i, 'Direction'] = 0
        
        i += 1
    
    # return non-merged K-lines
    filtered = df[~df['Merged']]
    if 'Datetime' in filtered.columns:
        return filtered.set_index('Datetime', drop=True)
    if 'index' in filtered.columns:
        return filtered.set_index('index', drop=True)
    return filtered.set_index(filtered.columns[0], drop=True)
    

df_contained = process_chan_containment(df)
#df_contained.head(10)
output_h5_path = output_dir / f"{symbol}_{interval}_ta_contained.h5"
df_contained.to_hdf(path_or_buf=output_h5_path, key=symbol.replace(".","_"), mode="a") 



# plot high-low chart
def _prepare_plot_df(df):
    df = df.reset_index()
    time_col = None
    for candidate in ['Datetime', 'Date', 'date']:
        if candidate in df.columns:
            time_col = candidate
            break
    if time_col is None:
        time_col = df.columns[0]
    if time_col not in df.columns:
        df[time_col] = df.index
    return df, time_col


def high_low_chart(df):
    df, time_col = _prepare_plot_df(df)
    fig = go.Figure()

    for i in range(len(df)):
        fig.add_trace(go.Scatter(
            x=[i, i],
            y=[df['Low'].iloc[i], df['High'].iloc[i]],
            mode='lines',
            line=dict(color='blue', width=2),
            showlegend=False,
            hovertext=f"High: {df['High'].iloc[i]}<br>Low: {df['Low'].iloc[i]}<br>{time_col}: {df[time_col].iloc[i]}"
        ))

    fig.update_layout(
        title='High-Low Price Range',
        xaxis_title='Datetime',
        yaxis_title='Price',
        xaxis=dict(rangeslider_visible=False, type='category', nticks=20),
    )

    return fig


# compare original and processed data
def create_candlestick_chart(original_df, processed_df):
    original_df, original_time_col = _prepare_plot_df(original_df)
    processed_df, processed_time_col = _prepare_plot_df(processed_df)
    fig = make_subplots(
        rows=2, cols=1,
        subplot_titles=('Chan Theory K-line containment Relationship'),
        vertical_spacing=0.1,
        row_width=[0.5, 0.5]
    )

    # original K-line chart
    for i in range(len(original_df)):
        fig.add_trace(go.Scatter(
            x=[i, i],
            y=[original_df['Low'].iloc[i], original_df['High'].iloc[i]],
            mode='lines',
            line=dict(color='blue', width=2),
            showlegend=False,
            hovertext=f"High: {original_df['High'].iloc[i]}<br>Low: {original_df['Low'].iloc[i]}<br>{original_time_col}: {original_df[original_time_col].iloc[i]}",
            ), row=1, col=1)

    # processed K-line chart
    for i in range(len(processed_df)):
        fig.add_trace(go.Scatter(
            x=[i, i],
            y=[processed_df['Low'].iloc[i], processed_df['High'].iloc[i]],
            mode='lines',
            line=dict(color='blue', width=2),
            showlegend=False,
            hovertext=f"High: {processed_df['High'].iloc[i]}<br>Low: {processed_df['Low'].iloc[i]}<br>{processed_time_col}: {processed_df[processed_time_col].iloc[i]}",
            ), row=2, col=1)

    fig.update_layout(
        title='Chan Theory K-line containment Relationship',
        height=800,
        showlegend=False,
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=False
    )

    fig.update_yaxes(title_text='Price', row=1, col=1)
    fig.update_yaxes(title_text='Price', row=2, col=1)

    return fig


fig = high_low_chart(df)
fig.write_html(output_dir / f"{symbol}_{interval}_high_low_Original.html")

fig = high_low_chart(df_contained)
fig.write_html(output_dir / f"{symbol}_{interval}_high_low_Contained.html")

fig = create_candlestick_chart(df, df_contained)
fig.write_html(output_dir / f"{symbol}_{interval}_chan_theory_kline_containment.html")

