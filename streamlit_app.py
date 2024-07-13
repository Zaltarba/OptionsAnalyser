import streamlit as st
import yfinance as yf
import pandas as pd

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

    options_data["Type"] = options_data["contractSymbol"]
    options_data["Type"] = options_data["Type"].apply(lambda x:x.split(ticker)[1][6]).map({"C":"Call", "P":"Put"})
    
    return all_options

ticker = st.text_input('Enter ticker to be studied, e.g. MA,META,V,AMZN,JPM,BA', '').upper()

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True) 
