import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import plotly.express as px

# Set page config for dark theme
st.set_page_config(page_title="Options Analysis", page_icon="📈", layout="wide",)

st.title("Is Now the Time to Buy?")
st.markdown("""
If you're looking for Greeks, volatility surfaces, and other useful metrics not available on your current broker, you're in the right place.
All stock data are here fetched from Yahoo Finance, this tool aims to provide a clear and concise interface.
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

def calculate_call_put_ratio(options_data):
    total_calls = options_data[options_data['Type'] == 'Call']['volume'].sum()
    total_puts = options_data[options_data['Type'] == 'Put']['volume'].sum()
    ratio = total_calls / total_puts if total_puts != 0 else float('inf')  # Avoid division by zero
    return ratio, total_calls, total_puts

def calculate_monthly_call_put_ratios(options_data):
    # Convert expiration dates to month-year format
    options_data['Month'] = pd.to_datetime(options_data['Expiration']).dt.to_period('M')
    # Group by Type and Month
    grouped = options_data.groupby(['Type', 'Month'])
    # Calculate total volume for Calls and Puts separately
    monthly_volumes = grouped['volume'].sum().unstack('Type')
    # Calculate Call-Put Ratios
    monthly_volumes['Call-Put Ratio'] = monthly_volumes['Call'] / monthly_volumes['Put']
    return monthly_volumes[['Call-Put Ratio']]

def plot_call_put_ratio(ratios_df):
    # Reset index to use 'Month' in the plot
    ratios_df = ratios_df.reset_index()
    ratios_df['Month'] = ratios_df['Month'].dt.strftime('%Y-%m')
    fig = px.line(
        ratios_df, 
        x='Month', 
        y='Call-Put Ratio',
        title='Monthly Call-Put Ratio',
        labels={'Month': 'Expiration Month', 'Call-Put Ratio': 'Ratio'},
        markers=True
        )  # Use markers to highlight data points
    fig.update_layout(
        xaxis_title='Month',
        yaxis_title='Call-Put Ratio',
        xaxis=dict(tickformat="%Y-%m"),
        hovermode='x'
        )
    return fig

def compute_volatility_surface_plotly(options_data, current_price=1):
    x = options_data['Time to Expiration']
    y = np.log(options_data['strike'] / current_price)
    z = options_data['impliedVolatility']

    xi = np.linspace(x.min(), x.max(), 100)
    yi = np.linspace(np.log(min_strike/current_price), np.log(max_strike/current_price), 100)
    xi, yi = np.meshgrid(xi, yi)
    zi = griddata((x, y), z, (xi, yi), method='cubic')
    zi_smoothed = gaussian_filter(zi, sigma=1)

    fig = go.Figure(data=[go.Surface(x=xi, y=yi, z=zi_smoothed)])
    fig.update_layout(
        title='',
        scene=dict(
            xaxis_title='Time to Expiration (Years)',
            yaxis_title='Log Strike Price / Current Price',
            zaxis_title='Implied Volatility',
            xaxis=dict(tickformat='.2f'),
            yaxis=dict(tickformat='$,.2f'),
            zaxis=dict(tickformat='.3f'),
        ),
        autosize=True,
        margin=dict(l=0, r=0, b=0, t=30)
    )
    return fig

# Input area in sidebar
st.sidebar.header("User Input Features")
ticker = st.sidebar.text_input('Enter ticker to be studied, e.g. MA,META,V,AMZN,JPM,BA', '').upper()

if ticker:
    st.sidebar.subheader("Parameters for the Volatility Surfaces")
    min_volume = st.sidebar.number_input('Set minimum volume', value=1000, step=25)
    options_data, last_price = get_options_data(ticker)
    min_strike = int(last_price * 0.8)
    max_strike = int(last_price * 1.2)
    step = int(last_price * 0.01)
    min_strike = st.sidebar.slider('Select minimum strike price', 0, int(last_price*2), value=min_strike, step=step)
    max_strike = st.sidebar.slider('Select maximum strike price', 0, int(last_price*2), value=max_strike, step=step)
    filtered_data_calls = options_data[(options_data["Type"] == "Call") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]
    filtered_data_puts = options_data[(options_data["Type"] == "Put") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]

    st.header("Asking for Greeks ?")
    st.write("Please select a contract")
    # Assume 'options_data' is your DataFrame with all the options contracts
    expiration_dates = sorted(options_data['Expiration'].unique())
    expiration = st.selectbox("Expiration Date", expiration_dates)
    option_type = st.selectbox("Contract", ["Call", "Put"])
    
    # Filter options for the selected expiration date
    available_contracts = options_data[options_data['Expiration'] == expiration]
    # Allow user to select between Calls and Puts
    filtered_contracts = available_contracts[available_contracts['Type'] == option_type]
    # Display contracts for selection
    available_strikes = filtered_contracts["strike"].unique()
    strike = st.selectbox("Strike", available_strikes)

    select_contract = filtered_contracts[filtered_contracts["strike"] == strike]
    
    # Display the selected contract's details and Greeks
    st.subheader("Selected Contract Details")
    st.write(f"**Type:** {selected_contract['Type']}")
    st.write(f"**Strike Price:** {selected_contract['strike']}")
    st.write(f"**Volume:** {selected_contract['volume']}")
    st.write(f"**Open Interest:** {selected_contract['openInterest']}")
    st.write(f"**Implied Volatility:** {selected_contract['impliedVolatility']}")
        
    # Assuming you have Greeks in your data
    if 'delta' in selected_contract and 'gamma' in selected_contract:
        st.write(f"**Delta:** {selected_contract['delta']}")
        st.write(f"**Gamma:** {selected_contract['gamma']}")
        st.write(f"**Theta:** {selected_contract['theta']}")
        st.write(f"**Vega:** {selected_contract['vega']}")

    st.header("Market Sentiment")
    st.write("We use here the Put Call Ratio metric. Check out my blog [post](https://zaltarba.github.io/blog/AboutMarketSentiment/) the known more about it")

    call_put_ratio, total_calls, total_puts = calculate_call_put_ratio(options_data)
    # Display using custom HTML/CSS
    ratio_html = f"""
    <div style="font-size: 16px; font-weight: bold; color: {'green' if call_put_ratio > 1 else 'red'};">
        Call-Put Ratio: {call_put_ratio:.2f}
        <div style="font-size: 12px; color: gray;">
            Calls: {total_calls}, Puts: {total_puts}
        </div>
    </div>
    """
    st.markdown(ratio_html, unsafe_allow_html=True)

    monthly_ratios = calculate_monthly_call_put_ratios(options_data)
    call_put_ratio_fig = plot_call_put_ratio(monthly_ratios)
    st.plotly_chart(call_put_ratio_fig, use_container_width=True)
        
    # Create three columns, where col_spacer is just a minimal-width spacer
    st.header("Volatility Surface")
    st.write("Feel free to hidden the sidebar on the left for a better visibility")
    col1, col_spacer, col2 = st.columns([1, 0.2, 1])
    with col1:
        st.subheader("Call Volatility Surface")
        if not filtered_data_calls.empty:
            fig_1 = compute_volatility_surface_plotly(filtered_data_calls, last_price)
            st.plotly_chart(fig_1, use_container_width=True)
    
    with col_spacer:
        st.write("")  # Spacer column
    
    with col2:
        st.subheader("Put Volatility Surface")
        if not filtered_data_puts.empty:
            fig_2 = compute_volatility_surface_plotly(filtered_data_puts, last_price)
            st.plotly_chart(fig_2, use_container_width=True)

else:
    st.write("Please use the interactive window on the left to provide the ticker and some required values.")

# Hide streamlit branding
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
