import streamlit as st
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="Öncü Balina & Nasdaq 100 Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Nasdaq 100 Radarı")

# --- FINNHUB API KEY GİRİŞİ ---
st.sidebar.header("🔑 API Ayarları")
api_key = st.sidebar.text_input("Finnhub API Key Girin:", type="password", help="finnhub.io adresinden ücretsiz alabilirsiniz.")

if not api_key:
    st.info("💡 **Not:** Verilerin IP engeline takılmadan %100 kesintisiz çekilebilmesi için sol menüden ücretsiz **Finnhub API Key**'inizi girin. (finnhub.io)")

# --- NASDAQ 100 HİSSELERİ ---
@st.cache_data(ttl=86400)
def get_nasdaq100_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        for df in tables:
            if 'Ticker' in df.columns:
                return df['Ticker'].tolist()
            elif 'Symbol' in df.columns:
                return df['Symbol'].tolist()
    except Exception:
        pass
    return ["NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD"]

NASDAQ_100_TICKERS = get_nasdaq100_tickers()

def get_finnhub_analysis(ticker, key):
    clean_symbol = ticker.strip().upper().replace('.', '-')
    
    # 1. Hisse Fiyat Verisi
    quote_url = f"https://finnhub.io/api/v1/quote?symbol={clean_symbol}&token={key}"
    q_res = requests.get(quote_url).json()
    
    if not q_res or 'c' not in q_res or q_res['c'] == 0:
        return None
        
    current_price = q_res['c']
    prev_close = q_res['pc']
    price_change = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0
    
    # 2. Opsiyon Chain Verisi (Finnhub Official API)
    opt_url = f"https://finnhub.io/api/v1/stock/option-chain?symbol={clean_symbol}&token={key}"
    opt_res = requests.get(opt_url).json()
    
    call_vol, put_vol = 0, 0
    call_oi, put_oi = 0, 0
    max_strike_call, max_strike_put = None, None
    data_mode = "Finnhub API (Aktif Veri)"
    
    if 'data' in opt_res and len(opt_res['data']) > 0:
        # En yakın aktif opsiyon vadesini al
        first_exp = opt_res['data'][0]
        options_list = first_exp.get('options', {})
        
        calls = pd.DataFrame(options_list.get('CALL', []))
        puts = pd.DataFrame(options_list.get('PUT', []))
        
        if not calls.empty:
            call_vol = calls['volume'].fillna(0).sum() if 'volume' in calls.columns else 0
            call_oi = calls['openInterest'].fillna(0).sum() if 'openInterest' in calls.columns else 0
            calls['score'] = calls.get('openInterest', 0) + calls.get('volume', 0)
            if not calls[calls['score'] > 0].empty:
                max_strike_call = calls.sort_values(by='score', ascending=False).iloc[0].get('strike')
                
        if not puts.empty:
            put_vol = puts['volume'].fillna(0).sum() if 'volume' in puts.columns else 0
            put_oi = puts['openInterest'].fillna(0).sum() if 'openInterest' in puts.columns else 0
            puts['score'] = puts.get('openInterest', 0) + puts.get('volume', 0)
            if not puts[puts['score'] > 0].empty:
                max_strike_put = puts.sort_values(by='score', ascending=False).iloc[0].get('strike')
    
    total_vol = call_vol + put_vol
    total_oi = call_oi + put_oi
    
    if total_vol > 0:
        call_ratio = (call_vol / total_vol) * 100
        put_ratio = (put_vol / total_vol) * 100
        vol_oi_ratio = round(total_vol / total_oi, 2) if total_oi > 0 else 1.0
    elif total_oi > 0:
        call_ratio = (call_oi / total_oi) * 100
        put_ratio = (put_oi / total_oi) * 100
        vol_oi_ratio = 1.0
    else:
        call_ratio, put_ratio = 50.0, 50.0
        vol_oi_ratio = 1.0

    # Sinyaller ve Yorumlar
    if call_ratio >= 58:
        whale_action = f"🚀 YUKARI OLTASI: Balinalar %{int(call_ratio)} CALL pozisyonunda."
        target_comment = f"En yüksek yığılma **${max_strike_call}** hedef seviyesinde." if max_strike_call else "Call ağırlıklı pozisyonlanma."
        option_signal = "🟢 CALL AĞIRLIKLI"
    elif put_ratio >= 58:
        whale_action = f"🔻 DÜŞÜŞ OLTASI: Balinalar %{int(put_ratio)} PUT pozisyonunda."
        target_comment = f"En yüksek koruma **${max_strike_put}** seviyesinde." if max_strike_put else "Put ağırlıklı korunma."
        option_signal = "🔴 PUT AĞIRLIKLI"
    else:
        whale_action = f"⚖️ NÖTR: Dağılım %{int(call_ratio)} Call - %{int(put_ratio)} Put."
        target_comment = "Net bir balina yönü yok, yatay bekleyiş."
        option_signal = "⚖️ KARARSIZ"

    stock_signal = "🟢 YÜKSELİŞ" if price_change > 0 else "🔴 DÜŞÜŞ"

    return {
        "Hisse": clean_symbol,
        "Fiyat ($)": round(current_price, 2),
        "Günlük %": round(price_change, 2),
        "Hisse Yönü (Spot)": stock_signal,
        "Opsiyon Yönü": option_signal,
        "Call / Put Dağılımı": f"%{int(call_ratio)} Call / %{int(put_ratio)} Put",
        "Call Hacim/OI": int(call_vol) if total_vol > 0 else int(call_oi),
        "Put Hacim/OI": int(put_vol) if total_vol > 0 else int(put_oi),
        "Sıra Dışı Kat (Vol/OI)": f"{vol_oi_ratio}x",
        "Call Hedef Fiyatı": f"${max_strike_call}" if max_strike_call else "Belirsiz",
        "Put Koruma Fiyatı": f"${max_strike_put}" if max_strike_put else "Belirsiz",
        "Balina Eylemi": whale_action,
        "Hedef Detayı": target_comment,
        "Veri Durumu": data_mode
    }

# Arayüz
tab1, tab2 = st.tabs(["🔍 Tek Hisse Olta Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

with tab1:
    st.subheader("Hisse Kodu Arayın")
    search_ticker = st.text_input("Hisse Kodu Girin (Örn: NVDA, TSLA, AAPL)", "NVDA")
    
    if st.button("🔎 Hisseyi Analiz Et", type="primary"):
        if not api_key:
            st.error("Lütfen sol menüden Finnhub API Key'inizi girin.")
        else:
            with st.spinner(f"{search_ticker.upper()} inceleniyor..."):
                res = get_finnhub_analysis(search_ticker, api_key)
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
                else:
                    st.error("Veri alınamadı. API Key'inizi veya hisse kodunu kontrol edin.")

with tab2:
    st.subheader("Nasdaq 100 Toplu Tarama")
    scan_limit = st.slider("Taranacak Hisse Sayısı", 10, len(NASDAQ_100_TICKERS), 20)
    
    if st.button("🚀 Seçilen Hisseleri Tara", type="primary"):
        if not api_key:
            st.error("Lütfen sol menüden Finnhub API Key'inizi girin.")
        else:
            signals = []
            progress_bar = st.progress(0)
            target_tickers = NASDAQ_100_TICKERS[:scan_limit]
            
            for idx, t in enumerate(target_tickers):
                progress_bar.progress((idx + 1) / len(target_tickers))
                res = get_finnhub_analysis(t, api_key)
                if res:
                    signals.append(res)
            
            progress_bar.empty()
            if signals:
                st.dataframe(pd.DataFrame(signals), use_container_width=True)
