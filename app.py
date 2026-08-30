import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="Öncü Balina Akışı & Nasdaq 100 Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Nasdaq 100 Radarı")

bugun = datetime.date.today()
if bugun.weekday() >= 5:
    st.warning("⚠️ PİYASALAR KAPALI. GÖSTERİLEN FİYATLAR EN SON İŞLEM GÜNÜNÜN KAPANIŞ VERİLERİDİR.")

NASDAQ_100_TICKERS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD",
    "PEP", "TMUS", "LIN", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM", "TXN"
]

@st.cache_data(ttl=60)
def fetch_stooq_data(ticker_input):
    raw = ticker_input.strip().upper()
    ticker_map = {
        "AAPLE": "AAPL", "APPLE": "AAPL", "MICROSOFT": "MSFT", 
        "TESLA": "TSLA", "AMAZON": "AMZN", "GOOGLE": "GOOGL", "NVIDIA": "NVDA",
        "META": "META", "AMD": "AMD", "NETFLIX": "NFLX"
    }
    clean = ticker_map.get(raw, raw)
    
    try:
        url = f"https://stooq.com/q/l/?s={clean.lower()}.us&f=sd2t2ohlcv&h&e=csv"
        df = pd.read_csv(url)
        
        if not df.empty and 'Close' in df.columns:
            close_val = df['Close'].values[0]
            open_val = df['Open'].values[0]
            high_val = df['High'].values[0]
            low_val = df['Low'].values[0]
            vol_val = df['Volume'].values[0]
            
            if pd.notna(close_val) and close_val != "N/D":
                current_price = float(close_val)
                prev_close = float(open_val) if pd.notna(open_val) and open_val != "N/D" else current_price
                
                direnc = round(float(high_val) * 1.01, 2) if pd.notna(high_val) and high_val != "N/D" else round(current_price * 1.03, 2)
                destek = round(float(low_val) * 0.99, 2) if pd.notna(low_val) and low_val != "N/D" else round(current_price * 0.97, 2)
                
                degisim = round(((current_price - prev_close) / prev_close) * 100, 2) if prev_close > 0 else 0.0
                
                if current_price > direnc:
                    durum = "🚀 DİRENÇ NET KIRILDI (Balina Alımı)"
                    karar = "🟢 ALIM YÖNLÜ (Long / Call)"
                elif current_price < destek:
                    durum = "🔻 DESTEK NET KIRILDI (Balina Satışı)"
                    karar = "🔴 SATIM YÖNLÜ (Short / Put)"
                else:
                    durum = "🔒 Kanal İçinde (Balina Beklemede)"
                    karar = "⚪ BEKLE"
                    
                return {
                    "Hisse": clean,
                    "Son Fiyat ($)": round(current_price, 2),
                    "Günlük Değişim %": degisim,
                    "Kritik Direnç": direnc,
                    "Kritik Destek": destek,
                    "Hacim Durumu": f"{int(vol_val):,}" if pd.notna(vol_val) else "1.0x",
                    "Kırılım Durumu": durum,
                    "Net Karar": karar
                }
    except Exception:
        pass
        
    return {
        "Hisse": clean,
        "Son Fiyat ($)": 0.0,
        "Günlük Değişim %": 0.0,
        "Kritik Direnç": 0.0,
        "Kritik Destek": 0.0,
        "Hacim Durumu": "Veri Yok",
        "Kırılım Durumu": "Bağlantı Hatası",
        "Net Karar": "⚪ BEKLE"
    }

tab_tek, tab_toplu = st.tabs(["🔍 Tek Hisse Olta Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

with tab_tek:
    st.subheader("Hisse Kodu Arayın")
    search_ticker = st.text_input("Hisse Kodu Girin (Örn: NVDA, TSLA, AAPL)", "NVDA")
    
    if st.button("🔎 Balina Kokusu Al", type="primary"):
        with st.spinner("Piyasa verileri taranıyor..."):
            res = fetch_stooq_data(search_ticker)
        st.success(f"{res['Hisse']} - Balina Akış Raporu")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Son Fiyat ($)", f"${res['Son Fiyat ($)']}", f"%{res['Günlük Değişim %']}")
        col2.metric("Net Karar", res['Net Karar'])
        col3.metric("Hacim Durumu", res['Hacim Durumu'])
        col4.metric("Kırılım Durumu", res['Kırılım Durumu'])

with tab_toplu:
    st.subheader("Nasdaq 100 Toplu Balina Radarı")
    scan_count = st.slider("Taranacak Hisse Adedi", 5, len(NASDAQ_100_TICKERS), 15)
    
    if st.button("🔍 Toplu Balina Tara", type="primary"):
        with st.spinner("Toplu liste taranıyor..."):
            results = [fetch_stooq_data(t) for t in NASDAQ_100_TICKERS[:scan_count]]
        st.dataframe(pd.DataFrame(results), use_container_width=True)
