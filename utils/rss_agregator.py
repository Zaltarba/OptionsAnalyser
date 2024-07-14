from enum import Enum
import feedparser
import re
from html import unescape

class DataProvider(Enum):
    CNBC = "CNBC"
    MARKETWATCH = "MarketWatch"
    NYT = "New York Times"
    COINTELEGRAPH = "Coin Telegraph"
    BLOCKCHAINNEWS = "Blockchain News"
    SEEKINGALPHA = "Seeking Alpha"
    SEC = "US Securities Exchange Commision"

feeds = {
    DataProvider.SEC:{
        "Press Release":"https://www.sec.gov/news/pressreleases.rss", 
    },
    DataProvider.CNBC:{
        "Top News": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "World News": "https://www.cnbc.com/id/100727362/device/rss/rss.html",
        "US News": "https://www.cnbc.com/id/15837362/device/rss/rss.html",
        "Asian News":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=19832390", 
        "Finance": "https://www.cnbc.com/id/10000664/device/rss/rss.html",
        "Investing":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839069",
        "Financial Advisors":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100646281",
        "Market Insider":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20409666", 
        "Charting Asia":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=23103686", 
        "Earnings":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=15839135",
        "Economy":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=20910258", 
        "Autos":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000101", 
        "Real Estate":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=10000115",
        "Energy":"https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&ids=19836768",
        }, 
    DataProvider.MARKETWATCH:{    
        "Top Stories":"http://feeds.marketwatch.com/marketwatch/topstories/",
        "Market Pulse":"http://feeds.marketwatch.com/marketwatch/marketpulse/",
        "Stock to Watch":"http://feeds.marketwatch.com/marketwatch/stocktowatch/",
        "Automobile":"http://feeds.marketwatch.com/marketwatch/Autoreviews/",
        },
    DataProvider.NYT:{
        "World News": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "US News": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml",
        "Asian News":"https://rss.nytimes.com/services/xml/rss/nyt/AsiaPacific.xml", 
        "European News":"https://rss.nytimes.com/services/xml/rss/nyt/Europe.xml", 
        "Economy":"https://rss.nytimes.com/services/xml/rss/nyt/Economy.xml", 
        "Buisness":"https://rss.nytimes.com/services/xml/rss/nyt/Business.xml", 
        "Real Estate":"https://rss.nytimes.com/services/xml/rss/nyt/RealEstate.xml", 
        "Most Shared":"https://rss.nytimes.com/services/xml/rss/nyt/MostShared.xml", 
        "Most Viewed":"https://rss.nytimes.com/services/xml/rss/nyt/MostViewed.xml", 
        },
    DataProvider.COINTELEGRAPH:{
        "Altcoin":"https://cointelegraph.com/rss/tag/altcoin",
        "Bitcoin": "https://cointelegraph.com/rss/tag/bitcoin", 
        "Blockchain":"https://cointelegraph.com/rss/tag/blockchain",
        "Ethereum":"https://cointelegraph.com/rss/tag/ethereum",
        "Litecoin":"https://cointelegraph.com/rss/tag/litecoin",
        "Monero":"https://cointelegraph.com/rss/tag/monero",
        "Regulation":"https://cointelegraph.com/rss/tag/regulation", 
    },
    DataProvider.BLOCKCHAINNEWS: {
        "Bitcoin":"https://blockchain.news/RSS?key=0HM0B8QFN3GEO",
        "Analysis":"https://Blockchain.News/RSS?key=0HM9E1QNN797D",
        "Interviews":"https://blockchain.news/RSS?key=0HLM7O77P8TQ9",
    }, 
    DataProvider.SEEKINGALPHA: {
        "Apple":"https://seekingalpha.com/api/sa/combined/AAPL.xml",
        "Tesla":"https://seekingalpha.com/api/sa/combined/TSLA.xml", 
        "General Electric Compagny":"https://seekingalpha.com/api/sa/combined/GE.xml",
        "Latest Analysis":"https://seekingalpha.com/feed.xml", 
        "Currencies":"https://seekingalpha.com/tag/forex.xml", 
        "Financials":"https://seekingalpha.com/sector/financial.xml", 
        "IPO Analysis":"https://seekingalpha.com/tag/ipo-analysis.xml", 
        "Long Ideas":"https://seekingalpha.com/tag/long-ideas.xml", 
        "ETFs":"https://seekingalpha.com/tag/etf-portfolio-strategy.xml", 
        "Healthcare":"https://seekingalpha.com/sector/healthcare.xml",
        "Utilities":"https://seekingalpha.com/sector/utilities.xml", 
        "Most Popular":"https://seekingalpha.com/listing/most-popular-articles.xml", 

    },
}

icons_path = {
    "CNBC": "pics/CNBC_icon.png",
    "MarketWatch": "pics/MW_icon.jpg",
    "New York Times": "pics/NYT_icon.png",
    "Coin Telegraph":"pics/COINTELEGRAPH_icon.jpg",
    "Blockchain News":"pics/BLOCKCHAINNEWS_icon.jpg",
    "Seeking Alpha":"pics/SEEKINGALPHA_icon.png", 
    "US Securities Exchange Commision":"pics/SEC_icon.png",
    # Add more as needed
}

def clean_html(raw_html):
    """
    This function removes HTML tags and decodes HTML entities.
    
    Args:
    - raw_html (str): A string containing HTML.

    Returns:
    - text (str): A clean string without HTML tags and entities.
    """
    # Remove HTML tags
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, '', raw_html)
    
    # Decode HTML entities
    cleantext = unescape(cleantext)
    
    return cleantext

class BaseFeedParser:

    def __init__(self, url):
        self.url = url
    
    source = "Generic"
    available_fields = {
        "title": True,
        "summary":True, 
        "links": True,
        "date":True,
        }
    
    def parse_feed(self):
        feed = feedparser.parse(self.url)
        cleaned_feed = []
        for entry in feed.entries:
            cleaned_entry = {
                'source': self.source.value,
                'title': entry.title if 'title' in entry else None,
                'link': entry.link if 'link' in entry else None,
                'date': entry.published if 'published' in entry else None,
            }
            # Check for both 'summary' and 'description' keys
            if 'summary' in entry:
                content = entry.summary
            elif 'description' in entry:
                content = entry.description
            else:
                content = None
            # Clean the content of HTML tags and entities
            if content:
                cleaned_entry['summary'] = clean_html(content)
            cleaned_feed.append(cleaned_entry)
        return cleaned_feed
    
class CNBCFeedParser(BaseFeedParser):
    source = DataProvider.CNBC
    available_fields = BaseFeedParser.available_fields.copy()
    # Additional CNBC-specific methods or overrides

class MarketWatchFeedParser(BaseFeedParser):
    source = DataProvider.MARKETWATCH
    available_fields = BaseFeedParser.available_fields.copy()
    # Additional MarketWatch-specific methods or overrides

class NewYorkTimesFeedParser(BaseFeedParser):
    source = DataProvider.NYT
    available_fields = BaseFeedParser.available_fields.copy()
    # Additional New York Times-specific methods or overrides

class CoinTelegraphFeedParser(BaseFeedParser):
    source = DataProvider.COINTELEGRAPH
    available_fields = BaseFeedParser.available_fields.copy()
    # Additional New York Times-specific methods or overrides

class BlockChainNewsFeedParser(BaseFeedParser):
    source = DataProvider.COINTELEGRAPH
    available_fields = BaseFeedParser.available_fields.copy()
    # Additional New York Times-specific methods or overrides

class SeekingAlphaFeedParser(BaseFeedParser):
    source = DataProvider.COINTELEGRAPH
    available_fields = BaseFeedParser.available_fields.copy()
    # Additional New York Times-specific methods or overrides

class SECFeedParser(BaseFeedParser):
    source = DataProvider.SEC
    available_fields = BaseFeedParser.available_fields.copy()
    # Additional New York Times-specific methods or overrides

class FeedManager:
    def __init__(self, feeds):
        self.feeds = feeds
        self.parsers = {
            DataProvider.CNBC: CNBCFeedParser,
            DataProvider.MARKETWATCH: MarketWatchFeedParser,
            DataProvider.NYT: NewYorkTimesFeedParser,
            DataProvider.COINTELEGRAPH: CoinTelegraphFeedParser, 
            DataProvider.BLOCKCHAINNEWS: BlockChainNewsFeedParser, 
            DataProvider.SEEKINGALPHA: SeekingAlphaFeedParser,
            DataProvider.SEC: SECFeedParser, 
        }

    def fetch_all_feeds(self):
        all_feeds = {}
        for source, categories in self.feeds.items():
            all_feeds[source] = {}
            for category, url in categories.items():
                parser = self.parsers[source](url)
                feed_data = parser.parse_feed()
                all_feeds[source][category] = feed_data
        return all_feeds
