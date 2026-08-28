import streamlit as st
import yfinance as yf
import pandas as pd
import requests
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import nltk

nltk.download('vader_lexicon', quiet=True)

st.set_page_config(page_title="ABD Borsa & Opsiyon Sinyal Paneli", layout="wide")
st.title("📈 ABD Borsaları Hisse & Opsiyon Sinyal Paneli")

# Sekme Yapısı
tab1, tab2 = st.tabs(["📊 Nasdaq 100 Hisse Sinyalleri", "⚡ Olağandışı Opsiyon Sinyalleri"])

# --- NASDAQ 100 HİSSE LİSTESİ ---
@st.cache_data
def get_nasdaq100_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        for table in tables:
            if 'Ticker' in table.columns:
                return table['Ticker'].tolist()
            elif 'Symbol' in table.columns:
                return table['Symbol'].tolist()
    except Exception:
        return ["AAPL", "NVDA", "TSLA", "AMD", "AMZN", "MSFT", "PLTR", "META", "GOOGL", "NFLX", "INTC", "AVGO", "COST", "PEP"]

TICKERS = get_nasdaq100_tickers()

# ==================== SEKME 1: HİSSE TARAYICI ====================
with tab1:
    st.header("🔍 Erken Hisse Sinyal Tarayıcı (Nasdaq 100)")
    st.info(f"Toplam {len(TICKERS)} Nasdaq 100 hissesi tarama listesinde.")

    def get_stock_signals(tickers):
        signals = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total = len(tickers)
        
        for idx, ticker in enumerate(tickers):
            status_text.text(f"Hisse Taranıyor ({idx+1}/{total}): {ticker}")
            progress_bar.progress((idx + 1) / total)
            
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
                
                # RSI Hesaplama
                delta = df['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                rsi = 100 - (100 / (1 + rs))
                latest_rsi = rsi.iloc[-1].values[0]

                signal_type = "Nötr"
                if volume_spike and latest_rsi < 60 and price_change > 0:
                    signal_type = "🔥 GÜÇLÜ BOĞA (Hacim Patlaması)"
                elif latest_rsi < 30:
                    signal_type = "🟢 Aşırı Satış (Dip Avı)"
                elif latest_rsi > 70:
                    signal_type = "🔴 Aşırı Alım (Düzeltme Riski)"

                if signal_type != "Nötr" or volume_spike:
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
                
        status_text.empty()
        progress_bar.empty()
        return pd.DataFrame(signals)

    if st.button("Nasdaq 100 Hisselerini Tara"):
        with st.spinner("Hisseler Taranıyor..."):
            signal_df = get_stock_signals(TICKERS)
            if not signal_df.empty:
                st.dataframe(signal_df.sort_values(by="Hacim Katı", ascending=False), use_container_width=True)
            else:
                st.warning("Şu anda güçlü sinyal veren hisse bulunamadı.")

# ==================== SEKME 2: OPSİYON TARAYICI ====================
with tab2:
    st.header("⚡ Olağandışı Opsiyon Hareketleri (Smart Money Tracker)")
    st.write("Hacmi (Volume), Açık Pozisyon (Open Interest) sayısını aşan ve primlenme ihtimali yüksek olan kontratlar taranır.")

    # Opsiyon taraması için en popüler likit hisseler
    OPTION_TICKERS = ["NVDA", "TSLA", "AAPL", "AMD", "AMZN", "MSFT", "PLTR", "META", "GOOGL", "NFLX", "SPY", "QQQ"]

    def scan_unusual_options(tickers):
        unusual_options = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total = len(tickers)

        for idx, ticker_symbol in enumerate(tickers):
            status_text.text(f"Opsiyonlar Taranıyor ({idx+1}/{total}): {ticker_symbol}")
            progress_bar.progress((idx + 1) / total)

            try:
                tk = yf.Ticker(ticker_symbol)
                expirations = tk.expirations
                if not expirations:
                    continue
                
                # En yakın vade tarihini al (Yakın vadeli sert hareketler için)
                nearest_exp = expirations[0]
                opt = tk.option_chain(nearest_exp)
                
                # CALL ve PUT kontratlarını incele
                for opt_type, data in [("CALL (Yükseliş)", opt.calls), ("PUT (Düşüş)", opt.puts)]:
                    for _, row in data.iterrows():
                        volume = row.get('volume', 0)
                        open_interest = row.get('openInterest', 0)
                        strike = row.get('strike', 0)
                        last_price = row.get('lastPrice', 0)
                        implied_vol = row.get('impliedVolatility', 0)

                        # Filtre: Hacim > 200 VE Hacim / Açık Pozisyon > 1.5
                        if pd.notnull(volume) and pd.notnull(open_interest) and open_interest > 0:
                            if volume > 200 and (volume / open_interest) > 1.5:
                                unusual_options.append({
                                    "Hisse": ticker_symbol,
                                    "Tip": opt_type,
                                    "Vade": nearest_exp,
                                    "Grev Fiyatı ($)": strike,
                                    "Kontrat Fiyatı ($)": last_price,
                                    "İşlem Hacmi": int(volume),
                                    "Açık Pozisyon": int(open_interest),
                                    "Hacim / Açık Poz.": round(volume / open_interest, 2),
                                    "Oynaklık (IV)": f"%{round(implied_vol * 100, 1)}"
                                })
            except Exception:
                pass

        status_text.empty()
        progress_bar.empty()
        return pd.DataFrame(unusual_options)

    if st.button("Olağandışı Opsiyonları Tara"):
        with st.spinner("Opsiyon Zincirleri Taranıyor..."):
            opt_df = scan_unusual_options(OPTION_TICKERS)
            if not opt_df.empty:
                st.dataframe(opt_df.sort_values(by="Hacim / Açık Poz.", ascending=False), use_container_width=True)
            else:
                st.warning("Şu anda sıra dışı hacim yakalayan bir opsiyon kontratı bulunamadı.")
