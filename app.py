import streamlit as st
import yfinance as yf
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

nltk.download('vader_lexicon', quiet=True)

st.set_page_config(page_title="Hisse & Opsiyon Çift Yönlü Analiz Paneli", layout="wide")
st.title("🎯 Hisse (Al/Sat) & Opsiyon (Call/Put) Sinyal Radarı")

st.write("""
Bu panel; hisselerin **Spot Fiyat Yönünü (Yükseliş/Düşüş)** ve **Opsiyon Eğilimini (Call/Put)** 
fiyat akışı, teknik indikatörler (RSI) ve anlık haber duygu analizini harmanlayarak hesaplar.
""")

OPTION_TICKERS = [
    "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "MSFT", "PLTR", "META", 
    "GOOGL", "NFLX", "SPY", "QQQ", "COIN", "MARA", "BABA", "INTC"
]

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_news_sentiment(ticker_symbol):
    sia = SentimentIntensityAnalyzer()
    try:
        tk = yf.Ticker(ticker_symbol)
        news_list = tk.news
        if not news_list:
            return 0, "Nötr / Haber Yok"
        
        total_score = 0
        count = 0
        latest_headline = ""
        
        for news in news_list[:3]:
            title = news.get('title', '')
            if title:
                if not latest_headline:
                    latest_headline = title
                score = sia.polarity_scores(title)['compound']
                total_score += score
                count += 1
                
        if count == 0:
            return 0, "Nötr / Haber Yok"
            
        avg_score = total_score / count
        return avg_score, latest_headline
    except Exception:
        return 0, "Haber Verisi Alınamadı"

def analyze_stock_and_options(tickers):
    signals = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(tickers)

    for idx, ticker_symbol in enumerate(tickers):
        status_text.text(f"Hisse ve Opsiyonlar Taranıyor ({idx+1}/{total}): {ticker_symbol}")
        progress_bar.progress((idx + 1) / total)

        try:
            tk = yf.Ticker(ticker_symbol)
            hist = tk.history(period="1mo")
            if hist.empty or len(hist) < 14:
                continue

            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            hist['RSI'] = calculate_rsi(hist)
            rsi = hist['RSI'].iloc[-1]

            # 1. Opsiyon Akışı
            expirations = tk.expirations
            if not expirations:
                continue

            nearest_exp = expirations[0]
            opt = tk.option_chain(nearest_exp)

            call_vol = opt.calls['volume'].sum() if 'volume' in opt.calls else 0
            put_vol = opt.puts['volume'].sum() if 'volume' in opt.puts else 0

            call_vol = 0 if pd.isna(call_vol) else call_vol
            put_vol = 0 if pd.isna(put_vol) else put_vol

            total_opt_vol = call_vol + put_vol
            if total_opt_vol == 0:
                continue

            call_ratio = (call_vol / total_opt_vol) * 100
            put_ratio = (put_vol / total_opt_vol) * 100

            # 2. Haber Analizi
            sentiment_score, son_haber = get_news_sentiment(ticker_symbol)

            # 3. HİSSE YÖNÜ HESAPLAMA (Spot Fiyat Yükseliş / Düşüş)
            stock_score = 50
            if rsi < 40: stock_score += 20  # Dipte, yükseliş potansiyeli
            elif rsi > 65: stock_score -= 20 # Tepede, düzeltme riski
            
            if price_change > 1.0: stock_score += 15
            elif price_change < -1.0: stock_score -= 15

            if sentiment_score > 0.15: stock_score += 15
            elif sentiment_score < -0.15: stock_score -= 15

            if stock_score >= 65:
                stock_signal = "🟢 YÜKSELİŞ (AL)"
            elif stock_score <= 35:
                stock_signal = "🔴 DÜŞÜŞ (SAT)"
            else:
                stock_signal = "⚖️ NÖTR / YATAY"

            # 4. OPSİYON YÖNÜ HESAPLAMA (Call / Put)
            option_score = 50
            if call_ratio > 60: option_score += 25
            elif put_ratio > 60: option_score -= 25

            if stock_score >= 65: option_score += 15
            elif stock_score <= 35: option_score -= 15

            if option_score >= 65:
                option_signal = "🟢 CALL"
            elif option_score <= 35:
                option_signal = "🔴 PUT"
            else:
                option_signal = "⚖️ KARARSIZ"

            news_status = "🟢 Pozitif" if sentiment_score > 0.15 else ("🔴 Negatif" if sentiment_score < -0.15 else "⚪ Nötr")

            signals.append({
                "Hisse": ticker_symbol,
                "Hisse Yönü": stock_signal,
                "Opsiyon Yönü": option_signal,
                "Fiyat ($)": round(current_price, 2),
                "Günlük %": round(price_change, 2),
                "RSI": round(rsi, 1),
                "Call/Put Oranı": f"%{round(call_ratio,0)} Call / %{round(put_ratio,0)} Put",
                "Haber Eğilimi": news_status,
                "Son Haber": son_haber[:60] + "..." if len(son_haber) > 60 else son_haber
            })

        except Exception:
            pass

    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(signals)

if st.button("🚀 Hisse & Opsiyon Analizini Başlat", type="primary"):
    with st.spinner("Tüm hisseler, teknik göstergeler ve opsiyon akışları analiz ediliyor..."):
        df = analyze_stock_and_options(OPTION_TICKERS)
        if not df.empty:
            st.success("Analiz tamamlandı!")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Veri çekilemedi. Lütfen tekrar deneyin.")
