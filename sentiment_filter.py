import requests
from textblob import TextBlob

class SentimentFilter:

    def __init__(self, news_api_key, twitter_api_key):
        self.news_api_key = news_api_key
        self.twitter_api_key = twitter_api_key

    def get_news_sentiment(self, query):
        url = f'https://newsapi.org/v2/everything?q={query}&apiKey={self.news_api_key}'
        response = requests.get(url)
        articles = response.json().get('articles', [])
        
        sentiments = []
        for article in articles:
            analysis = TextBlob(article['title'])
            sentiments.append(analysis.sentiment.polarity)
        
        return sum(sentiments) / len(sentiments) if sentiments else 0

    def get_twitter_sentiment(self, search_term):
        # Placeholder for Twitter API integration
        # This will require proper Twitter API setup
        tweets = [] # Assume you fetch tweets here
        sentiments = [TextBlob(tweet).sentiment.polarity for tweet in tweets]
        return sum(sentiments) / len(sentiments) if sentiments else 0

    def filter_signals(self, query):
        news_sentiment = self.get_news_sentiment(query)
        twitter_sentiment = self.get_twitter_sentiment(query)

        overall_sentiment = (news_sentiment + twitter_sentiment) / 2
        return overall_sentiment

if __name__ == "__main__":
    news_api_key = 'YOUR_NEWS_API_KEY'
    twitter_api_key = 'YOUR_TWITTER_API_KEY'
    sentiment_filter = SentimentFilter(news_api_key, twitter_api_key)
    trading_signal = sentiment_filter.filter_signals('example_stock')
    print(f'Trading Signal Sentiment: {trading_signal}')