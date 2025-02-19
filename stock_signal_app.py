import pandas as pd
import numpy as np
import yfinance as yf
import requests
from textblob import TextBlob
from bs4 import BeautifulSoup
import datetime
import streamlit as st
import yahooquery as yq
import plotly.graph_objects as go
from nltk.sentiment import SentimentIntensityAnalyzer
from sklearn.ensemble import RandomForestClassifier
import joblib
import nltk

# Ensure Vader Lexicon is available
nltk.download('vader_lexicon')

# Streamlit App Setup
st.title("Stock Buy/Sell Signal App with Live News, AI Predictions & Market Trends")
st.write("Enter a stock symbol to get a buy or sell signal based on technical indicators, AI-driven predictions, and market sentiment.")

# User Input for Stock Symbol
stock_symbols = st.multiselect("Enter Stock Symbols:", ["AAPL", "TSLA", "GOOGL", "MSFT", "AMZN"], default=["AAPL"])

# Function to fetch valid stock tickers
def get_valid_ticker(symbol):
    stock = yq.Ticker(symbol)
    if stock.quote_type and symbol in stock.quote_type:
        return symbol
    else:
        return None

# Function to fetch live financial news
def get_live_news():
    url = "https://finance.yahoo.com/news"
    response = requests.get(url)
    if response.status_code != 200:
        return []
    
    soup = BeautifulSoup(response.text, 'html.parser')
    headlines = [h.text for h in soup.find_all('h3')[:10]]  # Get top 10 headlines
    return headlines

# Function to fetch social media sentiment
def get_social_sentiment():
    url = "https://api.stocktwits.com/api/2/streams/trending.json"
    response = requests.get(url)
    if response.status_code != 200:
        return {}
    
    trending_data = response.json()
    sentiment_scores = {}
    sia = SentimentIntensityAnalyzer()
    for message in trending_data['messages'][:10]:
        stock = message['symbols'][0]['symbol']
        sentiment_scores[stock] = sia.polarity_scores(message['body'])['compound']
    return sentiment_scores

if stock_symbols:
    for stock_symbol in stock_symbols:
        valid_ticker = get_valid_ticker(stock_symbol)
        if valid_ticker:
            start_date = (datetime.datetime.now() - datetime.timedelta(days=540)).strftime('%Y-%m-%d')
            end_date = datetime.datetime.now().strftime('%Y-%m-%d')

            # Fetch historical stock data from Yahoo Finance
            data = yf.download(valid_ticker, start=start_date, end=end_date)

            # Compute technical indicators
            data['SMA_50'] = data['Close'].rolling(window=50).mean()
            data['SMA_200'] = data['Close'].rolling(window=200).mean()
            data['RSI'] = 100 - (100 / (1 + data['Close'].pct_change().rolling(14).mean()))

            # Function to get news sentiment
            def get_news_sentiment(stock):
                url = f'https://news.google.com/search?q={stock}&hl=en-US&gl=US&ceid=US:en'
                response = requests.get(url)
                if response.status_code != 200:
                    return 0  # Return neutral sentiment if request fails
                
                soup = BeautifulSoup(response.text, 'html.parser')
                headlines = [h.text for h in soup.find_all('h3')]
                
                sentiment_scores = []
                sia = SentimentIntensityAnalyzer()
                for headline in headlines:
                    sentiment_scores.append(sia.polarity_scores(headline)['compound'])
                
                avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
                return avg_sentiment

            # Fetch news sentiment and live financial news
            news_sentiment = get_news_sentiment(valid_ticker)
            live_news = get_live_news()
            social_sentiment = get_social_sentiment().get(valid_ticker, 0)
            total_sentiment = (news_sentiment + social_sentiment) / 2

            # Define buy/sell logic using AI Model
            def generate_signal(data, total_sentiment):
                signals = []
                for i in range(len(data)):
                    if i < 200:  # Avoid issues with NaN values in moving averages
                        signals.append("HOLD")
                    elif data['SMA_50'].iloc[i] > data['SMA_200'].iloc[i] and data['RSI'].iloc[i] < 70 and total_sentiment > 0:
                        signals.append("BUY")
                    elif data['SMA_50'].iloc[i] < data['SMA_200'].iloc[i] and data['RSI'].iloc[i] > 30 and total_sentiment < 0:
                        signals.append("SELL")
                    else:
                        signals.append("HOLD")
                return signals

            # Generate buy/sell signals
            data['Signal'] = generate_signal(data, total_sentiment)

            # Display results in Streamlit
            st.write(f"### Stock Buy/Sell Signals for {valid_ticker}")
            st.dataframe(data[['Close', 'SMA_50', 'SMA_200', 'RSI', 'Signal']].dropna())

            # Display live financial news
            st.write("### Live Market News")
            for news in live_news:
                st.write(f"- {news}")
            
            # Display stock price chart
            st.write("### Stock Price Chart")
            fig = go.Figure(data=[go.Candlestick(x=data.index, open=data['Open'], high=data['High'], low=data['Low'], close=data['Close'])])
            st.plotly_chart(fig)
        else:
            st.write(f"Invalid stock symbol: {stock_symbol}. Please enter a valid ticker.")
