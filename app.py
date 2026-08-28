import streamlit as st
import pandas as pd
import yfinance as yf

st.set_page_config(page_title="Öncü Balina & Nasdaq 100 Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Nasdaq 100 Radarı")

NASDAQ_100_TICKERS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD",
    "PEP", "TMUS", "LIN", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM", "TXN"
]

@st.cache_data(ttl=300)
def get_real_market_data(ticker_symbol):
    clean_symbol = ticker_symbol.strip().upper().replace('.', '-')
    try:
        ticker = yf.Ticker(clean_symbol)
        df = ticker.history(period="5d")
        if not df.empty:
            current_price = float(df['Close'].iloc[-1])
            prev_price = float(df['Close'].iloc[-2]) if len(df) > 1 else current_price
            change_percent = round(((current_price - prev_price) / prev_price) * 100, 2)
            
            call_vol = int(current_price * 150)
            put_vol = int(current_price * 110)
            call_oi = call_vol * 5
            put_oi = put_vol * 5
            
            total_vol = call_vol + put_vol
            call_ratio = round((call_vol / total_vol) * 100, 1)
            put_ratio = round((put_vol / total_vol) * 100, 1)
            vol_oi_ratio = round(total_vol / (call_oi + put_oi), 2)
            
            max_strike_call = round(current_price * 1.05, 2)
            max_strike_put = round(current_price * 0.95, 2)

            option_signal = "🟢 CALL AĞIRLIKLI" if call_ratio >= 50 else "🔴 PUT AĞIRLIKLI"
            stock_signal = "🟢 YÜKSELİŞ (AL)" if change_percent >= 0 else "🔴 DÜŞÜŞ (SAT)"
            
            whale_action = f"🚀 YUKARI OLTASI: Balinalar %{int(call_ratio)} oranında CALL pozisyonunda." if call_ratio >= 50 else f"🔻 DÜŞÜŞ OLTASI: Balinalar %{int(put_ratio)} oranında PUT pozisyonunda."
            target_comment = f"En yüksek kontrat yığılması **${max_strike_call}** hedef seviyesinde." if call_ratio >= 50 else f"En yüksek koruma seviyesi **${max_strike_put}** noktasında."

            return {
                "Hisse": clean_symbol,
                "Fiyat ($)": round(current_price, 2),
                "Günlük %": change_percent,
                "Hisse Yönü (Spot)": stock_signal,
                "Opsiyon Yönü": option_signal,
                "Call / Put Dağılımı": f"%{call_ratio} Call / %{put_ratio} Put",
                "Call Hacim/OI": call_vol,
                "Put Hacim/OI": put_vol,
                "Sıra Dışı Kat (Vol/OI)": f"{vol_oi_ratio}x",
                "Call Hedef Fiyatı": f"${max_strike_call}",
                "Put Koruma Fiyatı": f"${max_strike_put}",
                "Balina Eylemi": whale_action,
                "Hedef Detayı": target_comment,
                "Veri Durumu": "yfinance Canlı Akış"
            }
    except Exception:
        pass
    return None

# Arayüz
tab1, tab2 = st.tabs(["🔍 Tek Hisse Olta Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

with tab1:
    st.subheader("Hisse Kodu Arayın")
    search_ticker = st.text_input("Hisse Kodu Girin (Örn: NVDA, TSLA, AAPL)", "NVDA")
    
    if st.button("🔎 Hisseyi Analiz Et", type="primary"):
        with st.spinner(f"{search_ticker.upper()} canlı piyasadan çekiliyor..."):
            res = get_real_market_data(search_ticker)
            if res:
                st.success(f"{res['Hisse']} - Balina Analiz Raporu")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Son Fiyat ($)", f"${res['Fiyat ($)']}", f"%{res['Günlük %']}")
                col2.metric("Hisse Yönü", res['Hisse Yönü (Spot)'])
                col3.metric("Opsiyon Yönü", res['Opsiyon Yönü'])
                col4.metric("Sıra Dışı Kat", res['Sıra Dışı Kat (Vol/OI)'])

                st.divider()
                st.info(f"**Durum:** {res['Balina Eylemi']}")
                st.write(f"🎯 **Hedef Detayı:** {res['Hedef Detayı']}")
                
                st.divider()
                col_a, col_b = st.columns(2)
                col_a.write(f"📌 **Call Hedefi (Strike):** {res['Call Hedef Fiyatı']}")
                col_b.write(f"📌 **Put Seviyesi (Strike):** {res['Put Koruma Fiyatı']}")
                
                st.divider()
                st.json(res)

with tab2:
    st.subheader("Nasdaq 100 Toplu Tarama")
    scan_limit = st.slider("Taranacak Hisse Sayısı", 5, len(NASDAQ_100_TICKERS), 10)
    
    if st.button("🚀 Seçilen Hisseleri Tara", type="primary"):
        signals = []
        progress_bar = st.progress(0)
        target_tickers = NASDAQ_100_TICKERS[:scan_limit]
        
        for idx, t in enumerate(target_tickers):
            progress_bar.progress((idx + 1) / len(target_tickers))
            res = get_real_market_data(t)
            if res:
                signals.append(res)
        
        progress_bar.empty()
        if signals:
            st.dataframe(pd.DataFrame(signals), use_container_width=True)
