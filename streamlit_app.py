import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import numpy as np
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter
import plotly.express as px
import scipy.stats as si

# Set page config for dark theme
st.set_page_config(page_title="Options Analysis", page_icon="📈", layout="wide",)

st.title("Is Now the Time to Buy?")
st.markdown("""
If you're looking for Greeks, volatility surfaces, and other useful metrics not available on your current broker, you're in the right place.
All stock data are here fetched from Yahoo Finance, this tool aims to provide a clear and concise interface.
""")

# Function to fetch and plot data
def plot_stock(ticker):
    stock = yf.Ticker(ticker)

    try:
        # Get historical data for the last year
        data = stock.history(period="1y", interval="1d")
        if data.empty:
            st.error("No data fetched for the ticker. Please check the ticker symbol.")
            return None
    except Exception as e:
        st.error(f"An error occurred while fetching the data: {e}")
        return None

    # Creating the candlestick chart
    fig = go.Figure(data=[go.Candlestick(x=data.index,
                                         open=data['Open'],
                                         high=data['High'],
                                         low=data['Low'],
                                         close=data['Close'])])
    fig.update_layout(title='',
                      xaxis_title='Date',
                      yaxis_title='Price (USD)',
                      xaxis_rangeslider_visible=False)
    return fig

def get_financial_stats(ticker):
    stock = yf.Ticker(ticker)
    stats = {
        'PE Ratio': stock.info.get('trailingPE', 'N/A'),
        'Price/Sales (ttm)': stock.info.get('priceToSalesTrailing12Months', 'N/A'),
        'EBITDA Margin': stock.info.get('ebitdaMargins', 'N/A'),
        'Market Cap': stock.info.get('marketCap', 'N/A'),
        'Enterprise Value': stock.info.get('enterpriseValue', 'N/A'),
        'Profit Margins': stock.info.get('profitMargins', 'N/A'),
        'Return on Assets': stock.info.get('returnOnAssets', 'N/A'),
        'Return on Equity': stock.info.get('returnOnEquity', 'N/A'),
        'Revenue Per Share': stock.info.get('revenuePerShare', 'N/A'),
        'Quarterly Revenue Growth': stock.info.get('revenueGrowth', 'N/A'),
        'Gross Profits': stock.info.get('grossProfits', 'N/A'),
        'Operating Cash Flow': stock.info.get('operatingCashflow', 'N/A')
    }
    return pd.DataFrame([stats])

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

def compute_greeks(S, K, T, r, sigma, option_type="call"):
    """
    Computes the Greeks for an option using the Black-Scholes model.
    
    Parameters:
    S : float : Current stock price
    K : float : Strike price
    T : float : Time to expiration in years
    r : float : Risk-free interest rate
    sigma : float : Implied volatility
    option_type : str : Type of the option ('call' or 'put')
    
    Returns:
    dict : A dictionary containing Delta, Gamma, Theta, Vega, and Rho
    """
    d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
    d2 = d1 - sigma * np.sqrt(T)
    
    if option_type == "call":
        delta = si.norm.cdf(d1, 0.0, 1.0)
        theta = (-S * si.norm.pdf(d1, 0.0, 1.0) * sigma / (2 * np.sqrt(T)) - r * K * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0)) / 365
        rho = K * T * np.exp(-r * T) * si.norm.cdf(d2, 0.0, 1.0) / 100
    elif option_type == "put":
        delta = -si.norm.cdf(-d1, 0.0, 1.0)
        theta = (-S * si.norm.pdf(d1, 0.0, 1.0) * sigma / (2 * np.sqrt(T)) + r * K * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0)) / 365
        rho = -K * T * np.exp(-r * T) * si.norm.cdf(-d2, 0.0, 1.0) / 100
    
    gamma = si.norm.pdf(d1, 0.0, 1.0) / (S * sigma * np.sqrt(T))
    vega = S * si.norm.pdf(d1, 0.0, 1.0) * np.sqrt(T) / 100
    
    return {"delta": delta, "gamma": gamma, "theta": theta, "vega": vega, "rho": rho}

def calculate_leverage(options_data, stock_price):
    """
    Adds a leverage factor column to the options data DataFrame.
    
    Parameters:
    options_data : DataFrame : The options data DataFrame
    stock_price : float : Current stock price
    
    Returns:
    DataFrame : The options data DataFrame with an additional 'Leverage' column
    """
    # Ensure that the premium (lastPrice) and delta are in the DataFrame
    options_data['Leverage'] = (options_data['delta'] * stock_price) / options_data['lastPrice']
    return options_data

def add_greeks_to_options_data(options_data, stock_price, risk_free_rate=0.01):
    """
    Adds Greek metrics to the options DataFrame.
    
    Parameters:
    options_data : DataFrame : The options data DataFrame
    stock_price : float : Current stock price
    risk_free_rate : float : Risk-free interest rate (default is 1%)
    
    Returns:
    DataFrame : The options data DataFrame with additional Greek metrics
    """
    greeks = []
    for index, row in options_data.iterrows():
        greeks.append(compute_greeks(
            S=stock_price,
            K=row['strike'],
            T=row['Time to Expiration'],
            r=risk_free_rate,
            sigma=row['impliedVolatility'],
            option_type=row['Type'].lower()
        ))
    
    greeks_df = pd.DataFrame(greeks)
    options_data = pd.concat([options_data.reset_index(drop=True), greeks_df], axis=1)
    return options_data

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
ticker = st.text_input('Enter ticker to be studied, e.g. MA,META,V,AMZN,JPM,BA', '').upper()

if ticker:
    col1, col2, col3 = st.columns([0.2, 0.6, 0.2])
    with col2:
        # Using Markdown with inline styles for centering text
        st.markdown("""
            <style>
            .big-font {
                font-size:30px; 
                text-align:center;
            }
            </style>
            <p class="big-font">Stock Price Evolution</p>
            """, unsafe_allow_html=True)
        candle_chart = plot_stock(ticker)
        st.plotly_chart(candle_chart, use_container_width=True)
        options_data, last_price = get_options_data(ticker)
    # Create tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Market Sentiment", "Greeks", "Volatility Surface", "Key Stats"])
    # Tab 1: Market Sentiment
    with tab1:
        
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

    # Tab 2: Selected Contract Details
    with tab2:
        st.subheader("Greeks Parameters")
        
        # Create a row for input fields using columns
        col1, col2, col3, col4 = st.columns(4)
        
        # Place the risk-free rate input in the first column
        with col1:
            risk_free_rate = st.number_input('Set risk free rate', value=0.04, step=0.001)
        
        # Update options data with Greeks and leverage
        options_data_with_greeks = add_greeks_to_options_data(options_data, last_price, risk_free_rate)
        options_data_with_greeks = calculate_leverage(options_data_with_greeks, last_price)
        
        # Assume options_data is already populated with required data
        expiration_dates = sorted(options_data_with_greeks['Expiration'].unique())
        
        # Place the expiration date selector in the second column
        with col2:
            expiration = st.selectbox("Expiration Date", expiration_dates)
        
        # Place the contract type selector in the third column
        with col3:
            option_type = st.selectbox("Contract Type", ["Call", "Put"])
        
        # Once a type is selected, show available strikes in the next row
        available_contracts = options_data_with_greeks[(options_data_with_greeks['Expiration'] == expiration) & (options_data_with_greeks['Type'] == option_type)]
        
        if available_contracts.empty:
            st.write("No contracts available for the selected type and date.")
        else:
            strikes = sorted(available_contracts['strike'].unique())
            with col4:
                strike = st.selectbox("Strike Price", strikes)
                
            selected_contract = available_contracts[available_contracts['strike'] == strike].iloc[0]
            # Display the selected contract's details in a new section
            st.subheader("Selected Contract Details")
            st.write(f"**Volume:** {selected_contract['volume']}")
            st.write(f"**Open Interest:** {selected_contract['openInterest']}")
            st.write(f"**Implied Volatility:** {selected_contract['impliedVolatility']}")
            st.write(f"**Delta:** {selected_contract['delta']}")
            st.write(f"**Gamma:** {selected_contract['gamma']}")
            st.write(f"**Theta:** {selected_contract['theta']}")
            st.write(f"**Vega:** {selected_contract['vega']}")
            st.write(f"**Rho:** {selected_contract['rho']}")
            st.write(f"**Leverage:** {round(selected_contract['Leverage'], 1)}")

    # Tab 3: Volatility Surface
    with tab3:
        st.header("Volatility Surface")
        st.subheader("Parameters for the Volatility Surfaces")
        min_volume = st.number_input('Set minimum volume', value=1000, step=25)
        min_strike = int(last_price * 0.8)
        max_strike = int(last_price * 1.2)
        step = int(last_price * 0.01)
        min_strike = st.slider('Select minimum strike price', 0, int(last_price*2), value=min_strike, step=step)
        max_strike = st.slider('Select maximum strike price', 0, int(last_price*2), value=max_strike, step=step)
        filtered_data_calls = options_data[(options_data["Type"] == "Call") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]
        filtered_data_puts = options_data[(options_data["Type"] == "Put") & (options_data["volume"] >= min_volume) & (options_data["strike"] >= min_strike) & (options_data["strike"] <= max_strike)]
            
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Call Volatility Surface")
            if not filtered_data_calls.empty:
                fig_1 = compute_volatility_surface_plotly(filtered_data_calls, last_price)
                st.plotly_chart(fig_1, use_container_width=True)
        with col2:
            st.subheader("Put Volatility Surface")
            if not filtered_data_puts.empty:
                fig_2 = compute_volatility_surface_plotly(filtered_data_puts, last_price)
                st.plotly_chart(fig_2, use_container_width=True)

    # Tab 4: Additional Info
    with tab5:
        st.subheader("Financial Key Stats")
        financial_stats_df = get_financial_stats(ticker)
    
        # Convert DataFrame to HTML and ensure styles are properly scoped
        df_html = financial_stats_df.to_html(index=False, classes="table table-striped", border=0)
        styled_html = f"""
        <style>
            .table {{
                width: 100%;
                margin-bottom: 1rem;
                color: #212529;
            }}
            .table-striped tbody tr:nth-of-type(odd) {{
                background-color: rgba(0,0,0,.05);
            }}
            .table td, .table th {{
                padding: .75rem;
                vertical-align: top;
                border-top: 1px solid #dee2e6;
            }}
            .table thead th {{
                vertical-align: bottom;
                border-bottom: 2px solid #dee2e6;
            }}
        </style>
        {df_html}
        """
        st.markdown(styled_html, unsafe_allow_html=True)

else:
    st.write("Please use the interactive window on the left to provide the ticker and some required values.")

# Hide streamlit branding
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)
