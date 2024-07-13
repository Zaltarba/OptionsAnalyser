import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(
    page_title="Options Analysis",
    page_icon="📈", 
)

st.write("# Is now the to buy ?")
st.write("If you are looking for greeks, volatility surface, and other usefull metrics not available on your current broker you are on the right place")
st.write("All stock data are fetch from yfinance")

def get_options_data(ticker):
    # Load the ticker data
    stock = yf.Ticker(ticker)
    
    # Get available options expirations
    expirations = stock.options
    
    # Initialize an empty DataFrame to hold all options data
    all_options = pd.DataFrame()
    
    # Loop through all available expiration dates and get the options data
    for date in expirations:
        # Fetch the call and put data for the current expiration date
        opt = stock.option_chain(date)
        
        # Combine the call and put data
        current_options = pd.concat([opt.calls, opt.puts])
        current_options['Expiration'] = date  # Add the expiration date to the DataFrame
        
        # Append the current options data to the all_options DataFrame
        all_options = pd.concat([all_options, current_options])

    all_options["Type"] = all_options["contractSymbol"]
    all_options["Type"] = all_options["Type"].apply(lambda x:x.split(ticker)[1][6]).map({"C":"Call", "P":"Put"})
    
    return all_options

ticker = st.text_input('Enter ticker to be studied, e.g. MA,META,V,AMZN,JPM,BA', '').upper()

def compute_volatility_surface_plotly(options_data):
    # Convert expiration date to 'Time to Expiration' in years
    options_data['Time to Expiration'] = pd.to_datetime(options_data['Expiration']) - pd.Timestamp.today()
    options_data['Time to Expiration'] = options_data['Time to Expiration'].dt.days / 365
    
    # Prepare the grid
    x = options_data['Time to Expiration']
    y = options_data['strike']
    z = options_data['impliedVolatility'] * 100

    # Create grid spaces
    xi = np.linspace(x.min(), x.max(), 100)
    yi = np.linspace(y.min(), y.max(), 100)
    xi, yi = np.meshgrid(xi, yi)
    zi = griddata((x, y), z, (xi, yi), method='cubic')

    # Prepare the figure
    fig = go.Figure(data=[go.Surface(x=xi, y=yi, z=zi)])

    # Update layout of the plot
    fig.update_layout(
        title='Volatility Surface',
        scene=dict(
            xaxis_title='Time to Expiration (Years)',
            yaxis_title='Strike Price ($)',
            zaxis_title='Implied Volatility (%)',
            xaxis=dict(tickformat='.2f'),
            yaxis=dict(tickformat='$,.0f'),
            zaxis=dict(tickformat='.2%'),
        ),
        autosize=True,
        margin=dict(l=0, r=0, b=0, t=30)
    )
    return fig

if ticker != "":
    options_data = get_options_data(ticker)
    fig = compute_volatility_surface_plotly(options_data)
    st.plotly_chart(fig, use_container_width=True)

else:
    st.write("No options data available.")

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
