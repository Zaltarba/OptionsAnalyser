import feedparser
import streamlit as st 
import matplotlib.pyplot as plt
from wordcloud import WordCloud
from textblob import TextBlob
from transformers import pipeline

def display_banner(headlines_url):
    feed = feedparser.parse(headlines_url)

    headline_str = ' - '.join(f'&#128200; {entry.title}' for entry in feed.entries)

    text_html = f"""
    <div style="
        width: 100%; 
        white-space: nowrap; 
        overflow: hidden; 
        box-sizing: border-box;">
        <div style="
            display: inline-block;
            padding-left: 100%;
            animation: ticker 30s linear infinite;">
            {headline_str}"""+"""
        </div>
    </div>
    <style>
    @keyframes ticker {
        0% { transform: translateX(0); }
        100% { transform: translateX(-100%); }
    }
    </style>
    """
    # Display the ticker
    st.markdown(text_html, unsafe_allow_html=True)

# Callback function to increment news count
def increment_news_count(key):
    st.session_state[key] += 5

# Initialize sentiment analysis model
sentiment_analyzer = pipeline("sentiment-analysis")

# Function to display a single feed
def display_feed(column, feed_url, feed_key):

    with st.spinner('Loading news feed...'):
        feed = feedparser.parse(feed_url)
        displayed_items = st.session_state[feed_key]

        # Process text for WordCloud
        text = "test "
        for entry in feed.entries[:displayed_items]:
            try:
                text += entry.title
            except AttributeError:
                pass
            try:
                text += entry.summary
            except AttributeError:
                pass

        col1, col2, col3 = st.columns([1, 2, 1])  # Adjust the ratio as needed
        with col2:
            with st.spinner('Generating word cloud...'):
                # Create a word cloud object with desired parameters
                wordcloud = WordCloud(width=1600, height=900, background_color='black', colormap='Pastel1').generate(text)            
                # Set up the figure size and layout with a black background
                fig, ax = plt.subplots(figsize=(4, 2.25))
                ax.imshow(wordcloud, interpolation='bilinear')
                ax.axis("off")
                ax.set_facecolor('black')  # Set the axis background color
                fig.set_facecolor('black')  # Set the figure background color
                st.pyplot(fig)
                # Clear the current figure to ensure it does not interfere with future plots
                plt.clf()

    # Display the limited number of feed entries
    for entry in feed.entries[:displayed_items]:
        try:
            column.subheader(entry.title)
            title_result = sentiment_analyzer(entry.title)[0]
            summary_result = sentiment_analyzer(entry.get("summary", ""))[0]

            title_sentiment = title_result['label']
            title_confidence = title_result['score']
            summary_sentiment = summary_result['label']
            summary_confidence = summary_result['score']

            # Display sentiment for title and summary
            column.markdown(f"<p style='color:green;'>Title Sentiment: {title_sentiment} ({title_confidence:.2f})</p>", unsafe_allow_html=True)
            column.markdown(f"<p style='color:blue;'>Summary Sentiment: {summary_sentiment} ({summary_confidence:.2f})</p>", unsafe_allow_html=True)

            try:
                column.write(entry.get("summary", ""))
            except AttributeError:
                pass
            column.markdown(f"[Read More]({entry.link})")
        except AttributeError:
            pass
    
    _, col4, _ = st.columns([1, 2, 1])  # Adjust the ratio as needed
    with col4:
        # Button to request more news
        if column.button("Show More", key=f"{feed_key}_btn"):
            st.session_state[f"{feed_key}_more"] = True
