import streamlit as st
import pandas as pd
import yfinance as yf
import datetime

st.set_page_config(page_title="Nasdaq 100 Kırılım ve Mum Radarı", layout="wide")
st.title("📊 Nasdaq 100 Mum & Hacim Kırılım Radarı")

# Hafta Sonu Bilgisi
bugun = datetime.date.today()
if bugun.weekday() >= 5:
    st.warning("⚠️ PİYASALAR KAPALI. GÖSTERİLEN FİYATLAR SON İŞLEM GÜNÜNÜN KAPANIŞ VERİLERİDİR.")

NASDAQ_100_TICKERS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD",
    "PEP", "TMUS", "LIN", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM", "TXN"
]

@st.cache_data(ttl=0) # Önbelleği tamamen devre dışı bırakarak her seferinde güncel veri çekilmesini sağlar
def analyze_candlestick_breakout(ticker_symbol):
    raw_input = ticker_symbol.strip().upper()
    
    ticker_map = {
        "AAPLE": "AAPL", "APPLE": "AAPL", "MICROSOFT": "MSFT", 
        "TESLA": "TSLA", "AMAZON": "AMZN", "GOOGLE": "GOOGL", "NVIDIA": "NVDA",
        "META": "META", "AMD": "AMD", "NETFLIX": "NFLX"
    }
    clean_symbol = ticker_map.get(raw_input, raw_input).replace('.', '-')
    
    current_price = 100.0
    prev_close = 99.0
    resistance_level = 105.0
    support_level = 95.0
    vol_multiplier = 1.0
    
    try:
        ticker = yf.Ticker(clean_symbol)
        df = ticker.history(period="1mo", interval="1d")
        if not df.empty and len(df) >= 2:
            closes = df['Close'].dropna()
            highs = df['High'].dropna()
            lows = df['Low'].dropna()
            volumes = df['Volume'].dropna()
            
            if len(closes) > 0:
                current_price = float(closes.iloc[-1])
            if len(closes) > 1:
                prev_close = float(closes.iloc[-2])
            
            if len(highs) >= 15:
                resistance_level = round(float(highs.iloc[-15:-1].max()), 2)
            else:
                resistance_level = round(current_price * 1.03, 2)
                
            if len(lows) >= 15:
                support_level = round(float(lows.iloc[-15:-1].min()), 2)
            else:
                support_level = round(current_price * 0.97, 2)
                
            if len(volumes) >= 11:
                avg_vol = volumes.iloc[-11:-1].mean()
                last_vol = volumes.iloc[-1]
                if avg_vol > 0:
                    vol_multiplier = round(float(last_vol / avg_vol), 2)
    except Exception as e:
        st.error(f"Veri çekme hatası ({clean_symbol}): {e}")
        
    # Kırılım ve Yön Tespiti
    if current_price > resistance_level:
        if vol_multiplier >= 1.2:
            breakout_status = "🚀 DİRENÇ NET KIRILDI (Hacimli Yükseliş)"
            action_advice = "🟢 ALIM YÖNLÜ (Long / Call)"
        else:
            breakout_status = "⚠️ Direnç Üstünde Ama Hacim Zayıf"
            action_advice = "🟡 TEMKİNLİ İZLE"
    elif current_price < support_level:
        if vol_multiplier >= 1.2:
            breakout_status = "🔻 DESTEK NET KIRILDI (Hacimli Düşüş)"
            action_advice = "🔴 SATIM YÖNLÜ (Short / Put)"
        else:
            breakout_status = "⚠️ Destek Altında Ama Hacim Zayıf"
            action_advice = "🟡 TEMKİNLİ İZLE"
    else:
        breakout_status = "🔒 Kanal İçinde (Kırılım Bekleniyor)"
        action_advice = "⚪ BEKLE"

    change_pct = round(((current_price - prev_close) / prev_close) * 100, 2)

    return {
        "Hisse": clean_symbol,
        "Son Fiyat ($)": round(current_price, 2),
        "Günlük Değişim %": change_pct,
        "Kritik Direnç": resistance_level,
        "Kritik Destek": support_level,
        "Hacim Durumu": f"{vol_multiplier}x Ort.",
        "Kırılım Durumu": breakout_status,
        "Net Karar": action_advice,
        "Detay Açıklama": f"Son kapanış ${round(current_price, 2)} seviyesinde. Direnç: ${resistance_level}, Destek: ${support_level}."
    }

tab_tek, tab_toplu = st.tabs(["🔍 Tek Hisse Kırılım Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

with tab_tek:
    st.subheader("Özel Hisse Kırılım ve Mum Analizi")
    search_ticker = st.text_input("Hisse Kodu veya Adı Girin (Örn: AAPL, NVDA, Tesla)", "AAPL")
    
    if st.button("🔎 Hisse Kırılımını İncele", type="primary"):
        with st.spinner(f"{search_ticker.upper()} verileri alınıyor..."):
            res = analyze_candlestick_breakout(search_ticker)
            if res:
                st.success(f"{res['Hisse']} - Mum & Kırılım Raporu")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Son Fiyat ($)", f"${res['Son Fiyat ($)']}", f"%{res['Günlük Değişim %']}")
                col2.metric("Net Karar", res['Net Karar'])
                col3.metric("Hacim Durumu", res['Hacim Durumu'])
                col4.metric("Kırılım Durumu", res['Kırılım Durumu'])

                st.divider()
                st.info(f"📌 **Durum Özeti:** {res['Detay Açıklama']}")
                
                col_a, col_b = st.columns(2)
                col_a.write(f"📈 **Kritik Direnç Seviyesi:** ${res['Kritik Direnç']}")
                col_b.write(f"📉 **Kritik Destek Seviyesi:** ${res['Kritik Destek']}")

with tab_toplu:
    st.subheader("Nasdaq 100 Otomatik Kırılım ve Mum Tarayıcısı")
    scan_count = st.slider("Taranacak Hisse Adedi", 5, len(NASDAQ_100_TICKERS), 15)
    
    if st.button("🔍 Mum ve Kırılımları Tara", type="primary"):
        results = []
        my_bar = st.progress(0)
        selected_tickers = NASDAQ_100_TICKERS[:scan_count]
        
        for i, t in enumerate(selected_tickers):
            my_bar.progress((i + 1) / len(selected_tickers))
            res = analyze_candlestick_breakout(t)
            if res:
                results.append(res)
                
        my_bar.empty()
        
        if results:
            df_res = pd.DataFrame(results)
            st.dataframe(df_res, use_container_width=True)
