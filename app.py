import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

nltk.download('vader_lexicon', quiet=True)

st.set_page_config(page_title="ABD Borsa Sinyal & Haber Paneli", layout="wide")
st.title("📈 ABD Borsaları Anlık Haber & Yükseliş Sinyal Paneli")

st.header("🔍 Erken Sinyal Tarayıcı (Smart Money Tracker)")

TICKERS = ["AAPL", "NVDA", "TSLA", "AMD", "AMZN", "MSFT", "PLTR", "META"]

def get_stock_signals(tickers):
    signals = []
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if df.empty or len(df) < 14:
                continue
            
            avg_volume = df['Volume'][:-1].mean().values[0]
            current_volume = df['Volume'].iloc[-1].values[0]
            
            current_price = df['Close'].iloc[-1].values[0]
            prev_price = df['Close'].iloc[-2].values[0]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            volume_spike = current_volume > (avg_volume * 1.8)
            
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            latest_rsi = rsi.iloc[-1].values[0]

            signal_type = "Nötr"
            if volume_spike and latest_rsi < 60 and price_change > 0:
                signal_type = "🔥 GÜÇLÜ BOĞA (Yükseliş Öncesi Hacim Girdi)"
            elif latest_rsi < 30:
                signal_type = "🟢 Aşırı Satış (Dip Avı)"
            elif latest_rsi > 70:
                signal_type = "🔴 Aşırı Alım (Düzeltme Riski)"

            signals.append({
                "Hisse": ticker,
                "Fiyat ($)": round(current_price, 2),
                "Günlük Değişim (%)": round(price_change, 2),
                "Hacim Katı": round(current_volume / avg_volume, 2),
                "RSI (14)": round(latest_rsi, 2),
                "Sinyal": signal_type
            })
        except Exception:
            pass
    return pd.DataFrame(signals)

if st.button("Sinyalleri Tara"):
    with st.spinner("ABD Hisseleri Taranıyor..."):
        signal_df = get_stock_signals(TICKERS)
        st.dataframe(signal_df.sort_values(by="Hacim Katı", ascending=False), use_container_width=True)

st.header("📰 Anlık ABD Borsa Haberleri & AI Duygu Skoru")

def fetch_and_analyze_news():
    sia = SentimentIntensityAnalyzer()
    sample_news = [
        {"ticker": "NVDA", "title": "Nvidia expands AI chip production lines as demand surges beyond expectations."},
        {"ticker": "TSLA", "title": "Tesla faces regulatory delay on new software update in Europe."},
        {"ticker": "AAPL", "title": "Apple reports record revenue growth in services sector."},
    ]
    
    news_data = []
    for item in sample_news:
        score = sia.polarity_scores(item["title"])['compound']
        sentiment = "Nötr"
        if score > 0.1:
            sentiment = "🟢 Pozitif (Yükseliş Eğilimi)"
        elif score < -0.1:
            sentiment = "🔴 Negatif (Düşüş Eğilimi)"
            
        news_data.append({
            "Hisse": item["ticker"],
            "Haber Başlığı": item["title"],
            "Duygu Durumu": sentiment,
            "Skor": score
        })
    return pd.DataFrame(news_data)

st.dataframe(fetch_and_analyze_news(), use_container_width=True)
