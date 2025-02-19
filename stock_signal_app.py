import pandas as pd
import numpy as np
import yfinance as yf
import requests
from textblob import TextBlob
from bs4 import BeautifulSoup
import datetime
import streamlit as st
import yahooquery as yq

# Streamlit App Setup
st.title("Stock Buy/Sell Signal App")
st.write("Enter a stock symbol to get a buy or sell signal based on technical indicators and news sentiment.")

# User Input for Stock Symbol
stock_symbol = st.text_input("Enter Stock Symbol:", "AAPL")

# Function to fetch valid stock ticker
def get_valid_ticker(symbol):
    stock = yq.Ticker(symbol)
    if stock.quote_type and symbol in stock.quote_type:
        return symbol
    else:
        return None

if stock_symbol:
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

        # Function to get news sentiment from Google News
        def get_news_sentiment(stock):
            url = f'https://news.google.com/search?q={stock}&hl=en-US&gl=US&ceid=US:en'
            response = requests.get(url)
            if response.status_code != 200:
                return 0  # Return neutral sentiment if request fails
            
            soup = BeautifulSoup(response.text, 'html.parser')
            headlines = [h.text for h in soup.find_all('h3')]
            
            sentiment_scores = []
            for headline in headlines:
                analysis = TextBlob(headline)
                sentiment_scores.append(analysis.sentiment.polarity)
            
            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
            return avg_sentiment

        # Function to get news sentiment from Seeking Alpha
        def get_seeking_alpha_sentiment(stock):
            url = f'https://seekingalpha.com/symbol/{stock}'
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            if response.status_code != 200:
                return 0  # Return neutral sentiment if request fails
            
            soup = BeautifulSoup(response.text, 'html.parser')
            headlines = [h.text for h in soup.find_all('h3')]
            
            sentiment_scores = []
            for headline in headlines:
                analysis = TextBlob(headline)
                sentiment_scores.append(analysis.sentiment.polarity)
            
            avg_sentiment = np.mean(sentiment_scores) if sentiment_scores else 0
            return avg_sentiment

        # Fetch news sentiment from both sources
        google_news_sentiment = get_news_sentiment(valid_ticker)
        seeking_alpha_sentiment = get_seeking_alpha_sentiment(valid_ticker)
        
        # Average both sentiment scores
        news_sentiment = (google_news_sentiment + seeking_alpha_sentiment) / 2

        # Define buy/sell logic
        def generate_signal(data, news_sentiment):
            signals = []
            for i in range(len(data)):
                if i < 200:  # Avoid issues with NaN values in moving averages
                    signals.append("HOLD")
                elif data['SMA_50'].iloc[i] > data['SMA_200'].iloc[i] and data['RSI'].iloc[i] < 70 and news_sentiment > 0:
                    signals.append("BUY")
                elif data['SMA_50'].iloc[i] < data['SMA_200'].iloc[i] and data['RSI'].iloc[i] > 30 and news_sentiment < 0:
                    signals.append("SELL")
                else:
                    signals.append("HOLD")
            return signals

        # Generate buy/sell signals
        data['Signal'] = generate_signal(data, news_sentiment)

        # Display results in Streamlit
        st.write("Stock Buy/Sell Signals:")
        st.dataframe(data[['Close', 'SMA_50', 'SMA_200', 'RSI', 'Signal']].dropna())
    else:
        st.write("Invalid stock symbol. Please enter a valid ticker.")
