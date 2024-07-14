import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

# Set page config for dark theme
st.set_page_config(page_title="Options Analysis", page_icon="📈", layout="wide",)

st.title("Is Now the Time to Buy?")
st.markdown("""
If you're looking for Greeks, volatility surfaces, and other useful metrics not available on your current broker, you're in the right place.
All stock data are here fetched from Yahoo Finance, this aims to provide a clear and concise interface.
Please use the interactive window on the left to provide the ticker and some required values.
""")

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

    data = stock.history(period='1d', interval='1m')
    # Get the last price from the close column
    if data.empty:
        data = stock.history(period='2w', interval='1d')
        if data.empty:
            last_price = 500
        else:
            last_price = data['Close'].iloc[-1]
    else:
        last_price = data['Close'].iloc[-1]
    
    return all_options, last_price

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

# Input area in sidebar
st.sidebar.header("User Input Features")
ticker = st.sidebar.text_input('Enter ticker to be studied, e.g. MA,META,V,AMZN,JPM,BA', '').upper()
min_volume = st.sidebar.number_input('Set minimum volume', value=1000, step=25)

if ticker:
    options_data, last_price = get_options_data(ticker)
    min_strike = int(last_price * 0.8)
    max_strike = int(last_price * 1.2)
    step = int(last_price * 0.01)
    
    min_strike = st.sidebar.slider('Select minimum strike price', 0, int(last_price*2), value=min_strike, step=step)
    max_strike = st.sidebar.slider('Select maximum strike price', 0, int(last_price*2), value=max_strike, step=step)

    filtered_data_calls = options_data[(options_data["Type"] == "Call") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]
    filtered_data_puts = options_data[(options_data["Type"] == "Put") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]

    # Define the gap size in pixels
    gap_size = 30  # You can adjust this value based on your preference
    
    # Create two columns with a specified gap between them
    col1, col2 = st.columns([1, 1], gap=gap_size)
    
    with col1:
        st.subheader("Call Volatility Surface")
        if not filtered_data_calls.empty:
            fig_1 = compute_volatility_surface_plotly(filtered_data_calls)
            st.plotly_chart(fig_1, use_container_width=True)
        else:
            st.write("No data available for calls within the selected range.")

    with col2:
        st.subheader("Put Volatility Surface")
        if not filtered_data_puts.empty:
            fig_2 = compute_volatility_surface_plotly(filtered_data_puts)
            st.plotly_chart(fig_2, use_container_width=True)
        else:
            st.write("No data available for puts within the selected range.")
    else:
        st.sidebar.write("No options data available.")

# Hide streamlit branding
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
