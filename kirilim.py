import streamlit as st
import pandas as pd
import requests
import io
import datetime

st.set_page_config(page_title="Nasdaq 100 Kırılım ve Mum Radarı", layout="wide")
st.title("📊 Nasdaq 100 Mum & Hacim Kırılım Radarı")

bugun = datetime.date.today()
if bugun.weekday() >= 5:
    st.warning("⚠️ PİYASALAR KAPALI. GÖSTERİLEN FİYATLAR SON İŞLEM GÜNÜNÜN KAPANIŞ VERİLERİDİR.")

NASDAQ_100_TICKERS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD",
    "PEP", "TMUS", "LIN", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM", "TXN"
]

@st.cache_data(ttl=300)
def get_stock_data(ticker):
    url = f"https://stooq.com/q/d/l/?s={ticker.lower()}.us&i=d"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200 or len(response.text) < 50:
            return None
            
        df = pd.read_csv(io.StringIO(response.text))
        if df.empty or 'Close' not in df.columns:
            return None
            
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
        
        df = df.dropna(subset=['Close'])
        if len(df) < 2:
            return None
            
        current_price = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])
        
        highs = df['High'].tail(15).max()
        lows = df['Low'].tail(15).min()
        
        volumes = df['Volume'].tail(11)
        last_vol = float(volumes.iloc[-1]) if len(volumes) > 0 else 0
        avg_vol = float(volumes.iloc[:-1].mean()) if len(volumes) > 1 else 1
        vol_multiplier = round(last_vol / avg_vol, 2) if avg_vol > 0 else 1.0
        
        change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)
        
        if current_price > highs:
            breakout_status = "🚀 DİRENÇ NET KIRILDI"
            action = "🟢 ALIM YÖNLÜ (Long)"
        elif current_price < lows:
            breakout_status = "🔻 DESTEK NET KIRILDI"
            action = "🔴 SATIM YÖNLÜ (Short)"
        else:
            breakout_status = "🔒 Kanal İçinde"
            action = "⚪ BEKLE"
            
        return {
            "Hisse": ticker,
            "Son Fiyat ($)": round(current_price, 2),
            "Günlük Değişim %": change_pct,
            "Kritik Direnç": round(highs, 2),
            "Kritik Destek": round(lows, 2),
            "Hacim Durumu": f"{vol_multiplier}x Ort.",
            "Kırılım Durumu": breakout_status,
            "Net Karar": action
        }
    except Exception:
        return None

tab_tek, tab_toplu = st.tabs(["🔍 Tek Hisse Kırılım Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

with tab_tek:
    st.subheader("Özel Hisse Kırılım ve Mum Analizi")
    search_ticker = st.text_input("Hisse Kodu (Örn: AAPL, NVDA, TSLA)", "AAPL").strip().upper()
    
    if st.button("🔎 Hisse Kırılımını İncele", type="primary"):
        with st.spinner("Veriler yükleniyor..."):
            res = get_stock_data(search_ticker)
            if res:
                st.success(f"{res['Hisse']} - Raporu")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Son Fiyat ($)", f"${res['Son Fiyat ($)']}", f"%{res['Günlük Değişim %']}")
                col2.metric("Net Karar", res['Net Karar'])
                col3.metric("Hacim Durumu", res['Hacim Durumu'])
                col4.metric("Kırılım Durumu", res['Kırılım Durumu'])
            else:
                st.error("Veri alınamadı, hisse kodunu kontrol edin.")

with tab_toplu:
    st.subheader("Nasdaq 100 Otomatik Tarayıcı")
    scan_count = st.slider("Taranacak Hisse Adedi", 5, len(NASDAQ_100_TICKERS), 15)
    
    if st.button("🔍 Mum ve Kırılımları Tara", type="primary"):
        results = []
        my_bar = st.progress(0)
        selected_tickers = NASDAQ_100_TICKERS[:scan_count]
        
        for i, t in enumerate(selected_tickers):
            my_bar.progress((i + 1) / len(selected_tickers))
            res = get_stock_data(t)
            if res:
                results.append(res)
        my_bar.empty()
        
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.error("Toplu tarama verileri alınamadı.")
