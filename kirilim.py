import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Nasdaq 100 Kırılım ve Mum Radarı", layout="wide")
st.title("📊 Nasdaq 100 Mum & Hacim Kırılım Radarı")

NASDAQ_100_TICKERS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD",
    "PEP", "TMUS", "LIN", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM", "TXN"
]

@st.cache_data(ttl=300)
def analyze_candlestick_breakout(ticker_symbol):
    clean_symbol = ticker_symbol.strip().upper().replace('.', '-')
    fallback_price = 150.0
    
    try:
        ticker = yf.Ticker(clean_symbol)
        df = ticker.history(period="30d")
        if not df.empty and len(df) >= 15:
            closes = df['Close']
            highs = df['High']
            lows = df['Low']
            volumes = df['Volume']
            
            current_price = float(closes.iloc[-1])
            prev_close = float(closes.iloc[-2])
            
            # Son 14 mumun direnç ve destek seviyeleri
            resistance_level = round(float(highs.iloc[-15:-1].max()), 2)
            support_level = round(float(lows.iloc[-15:-1].min()), 2)
            
            # Hacim analizi (Son hacmin 10 günlük ortalamaya oranı)
            avg_vol = volumes.iloc[-11:-1].mean()
            last_vol = volumes.iloc[-1]
            vol_multiplier = round(float(last_vol / avg_vol), 2) if avg_vol > 0 else 1.0
            
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
                "Net Karar": action_advice
            }
    except Exception:
        pass
        
    return {
        "Hisse": clean_symbol,
        "Son Fiyat ($)": fallback_price,
        "Günlük Değişim %": 0.0,
        "Kritik Direnç": fallback_price * 1.05,
        "Kritik Destek": fallback_price * 0.95,
        "Hacim Durumu": "1.0x Ort.",
        "Kırılım Durumu": "Veri Alınamadı",
        "Net Karar": "BEKLE"
    }

# Arayüz
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
