import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

st.set_page_config(page_title="Options Analysis", page_icon="📈")

st.write("# Is Now the Time to Buy?")
st.write("If you're looking for Greeks, volatility surfaces, and other useful metrics not available on your current broker, you're in the right place.")
st.write("All stock data are fetched from Yahoo Finance.")

def get_options_data(ticker):
    stock = yf.Ticker(ticker)
    expirations = stock.options
    all_options = pd.DataFrame()

    for date in expirations:
        opt = stock.option_chain(date)
        current_options = pd.concat([opt.calls, opt.puts])
        current_options['Expiration'] = date
        all_options = pd.concat([all_options, current_options])

    all_options['Time to Expiration'] = pd.to_datetime(all_options['Expiration']) - pd.Timestamp.today()
    all_options['Time to Expiration'] = all_options['Time to Expiration'].dt.days / 365
    all_options["Type"] = all_options["contractSymbol"].apply(lambda x: x.split(ticker)[1][6]).map({"C": "Call", "P": "Put"})
    all_options = all_options.sort_values(by=["strike", "Time to Expiration", "Type"])
    all_options["volume"] = all_options["volume"].fillna(0)

    data = stock.history(period='1w', interval='1m')
    # Get the last price from the close column
    last_price = data['Close'].iloc[-1]
    
    return all_options, last_price

ticker = st.text_input('Enter ticker to be studied, e.g. MA,META,V,AMZN,JPM,BA', '').upper()

def get_last_price(ticker):
    # Load the ticker data
    stock = yf.Ticker(ticker)
    
    # Fetch historical data for the last week with 1-minute granularity
    # Note: 1-minute granularity might be limited to certain subscriptions or the recent data
    data = stock.history(period='2d', interval='1m')
    
    # Check if data is empty
    if data.empty:
        st.write("No data available for the specified ticker and interval.")
        return None
    
    # Get the last price from the close column
    last_price = data['Close'].iloc[-1]
    
    return last_price

def compute_volatility_surface_plotly(options_data):
    x = options_data['Time to Expiration']
    y = options_data['strike']
    z = options_data['impliedVolatility']

    xi = np.linspace(x.min(), x.max(), 100)
    yi = np.linspace(min_strike, max_strike, 100)
    xi, yi = np.meshgrid(xi, yi)
    zi = griddata((x, y), z, (xi, yi), method='cubic')
    zi[zi < 0] = 0
    zi_smoothed = gaussian_filter(zi, sigma=1)

    fig = go.Figure(data=[go.Surface(x=xi, y=yi, z=zi_smoothed)])
    fig.update_layout(
        title='Volatility Surface',
        scene=dict(
            xaxis_title='Time to Expiration (Years)',
            yaxis_title='Strike Price ($)',
            zaxis_title='Implied Volatility (%)',
            xaxis=dict(tickformat='.2f'),
            yaxis=dict(tickformat='$,.0f'),
            zaxis=dict(tickformat='.3f'),
        ),
        autosize=True,
        margin=dict(l=0, r=0, b=0, t=30)
    )
    return fig

if ticker:

    options_data, last_price = get_options_data(ticker)
    
    min_strike = int(last_price * 0.8)
    max_strike = int(last_price * 1.2)
    step = int(last_price * 0.01)
    
    min_volume = st.number_input('Set minimum volume', value=1000, step=25)
    min_strike = st.slider('Select minimum strike price', 0, int(last_price*2), value=min_strike, step=step)
    max_strike = st.slider('Select maximum strike price', 0, int(last_price*2), value=max_strike, step=step)

    filtered_data_calls = options_data[(options_data["Type"] == "Call") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]
    filtered_data_puts = options_data[(options_data["Type"] == "Put") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("Call Volatility Surface")
        if not filtered_data_calls.empty:
            fig_1 = compute_volatility_surface_plotly(filtered_data_calls)
            st.plotly_chart(fig_1, use_container_width=True)
        else:
            st.write("No data available for calls within the selected range.")
    with col2:
        st.write("Put Volatility Surface")
        if not filtered_data_puts.empty:
            fig_2 = compute_volatility_surface_plotly(filtered_data_puts)
            st.plotly_chart(fig_2, use_container_width=True)
        else:
            st.write("No data available for puts within the selected range.")

else:
    st.write("No options data available.")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
