import streamlit as st
import pandas as pd
import numpy as np
import requests
import json

st.set_page_config(page_title="Öncü Balina & Nasdaq 100 Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Nasdaq 100 Radarı")

st.write("Streamlit Cloud IP engeli, proxy bypass katmanı ile aşılmıştır. API Key gerekmez.")

# --- NASDAQ 100 HİSSELERİ ---
@st.cache_data(ttl=86400)
def get_nasdaq100_tickers():
    return [
        "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "ASML",
        "PEP", "TMUS", "LIN", "AMD", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM"
    ]

NASDAQ_100_TICKERS = get_nasdaq100_tickers()

def get_options_via_proxy(ticker_symbol):
    """Yahoo Finance isteğini Cloudflare/Allorigins Proxy üzerinden geçirerek IP engelini aşar."""
    target_url = f"https://query1.finance.yahoo.com/v7/finance/options/{ticker_symbol}"
    proxy_url = f"https://api.allorigins.win/get?url={requests.utils.quote(target_url)}"
    
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    
    try:
        # Önce doğrudan dene
        res = requests.get(target_url, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            return extract_data(data)
    except Exception:
        pass

    try:
        # Doğrudan istek engellendiyse Proxy üzerinden çek
        res = requests.get(proxy_url, timeout=10)
        if res.status_code == 200:
            contents = res.json().get('contents')
            if contents:
                data = json.loads(contents)
                return extract_data(data)
    except Exception:
        pass

    return None

def extract_data(data):
    try:
        result = data['optionChain']['result'][0]
        quote = result.get('quote', {})
        options = result['options'][0]
        
        calls = pd.DataFrame(options.get('calls', []))
        puts = pd.DataFrame(options.get('puts', []))
        
        current_price = quote.get('regularMarketPrice', 0)
        prev_close = quote.get('regularMarketPreviousClose', current_price)
        
        return calls, puts, current_price, prev_close
    except Exception:
        return None

def calculate_rsi(prices, window=14):
    if len(prices) < window:
        return 50.0
    delta = pd.Series(prices).diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return (100 - (100 / (1 + rs))).iloc[-1]

def analyze_ticker(ticker_symbol):
    clean_symbol = ticker_symbol.strip().upper().replace('.', '-')
    
    opt_data = get_options_via_proxy(clean_symbol)
    if not opt_data:
        return None
        
    calls, puts, current_price, prev_close = opt_data
    
    price_change = ((current_price - prev_close) / prev_close) * 100 if prev_close else 0.0
    
    call_vol = calls['volume'].fillna(0).sum() if not calls.empty and 'volume' in calls.columns else 0
    put_vol = puts['volume'].fillna(0).sum() if not puts.empty and 'volume' in puts.columns else 0
    call_oi = calls['openInterest'].fillna(0).sum() if not calls.empty and 'openInterest' in calls.columns else 0
    put_oi = puts['openInterest'].fillna(0).sum() if not puts.empty and 'openInterest' in puts.columns else 0
    
    max_strike_call = None
    max_strike_put = None
    
    if not calls.empty:
        calls['score'] = calls.get('openInterest', 0).fillna(0) + calls.get('volume', 0).fillna(0)
        if not calls[calls['score'] > 0].empty:
            max_strike_call = calls.sort_values(by='score', ascending=False).iloc[0]['strike']
            
    if not puts.empty:
        puts['score'] = puts.get('openInterest', 0).fillna(0) + puts.get('volume', 0).fillna(0)
        if not puts[puts['score'] > 0].empty:
            max_strike_put = puts.sort_values(by='score', ascending=False).iloc[0]['strike']
            
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
        "Call Hedef Fiyatı": f"${max_strike_call}" if max_strike_call else "Veri Yok",
        "Put Koruma Fiyatı": f"${max_strike_put}" if max_strike_put else "Veri Yok",
        "Balina Eylemi": whale_action,
        "Hedef Detayı": target_comment,
        "Veri Durumu": "Proxy bypass ile çekildi"
    }

# Arayüz
tab1, tab2 = st.tabs(["🔍 Tek Hisse Olta Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

with tab1:
    st.subheader("Hisse Kodu Arayın")
    search_ticker = st.text_input("Hisse Kodu Girin (Örn: NVDA, TSLA, AAPL)", "NVDA")
    
    if st.button("🔎 Hisseyi Analiz Et", type="primary"):
        with st.spinner(f"{search_ticker.upper()} inceleniyor..."):
            res = analyze_ticker(search_ticker)
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
                st.error("Veri alınamadı. Lütfen geçerli bir hisse kodu girin veya sayfayı yenileyip tekrar deneyin.")

with tab2:
    st.subheader("Nasdaq 100 Toplu Tarama")
    scan_limit = st.slider("Taranacak Hisse Sayısı", 5, len(NASDAQ_100_TICKERS), 10)
    
    if st.button("🚀 Seçilen Hisseleri Tara", type="primary"):
        signals = []
        progress_bar = st.progress(0)
        target_tickers = NASDAQ_100_TICKERS[:scan_limit]
        
        for idx, t in enumerate(target_tickers):
            progress_bar.progress((idx + 1) / len(target_tickers))
            res = analyze_ticker(t)
            if res:
                signals.append(res)
        
        progress_bar.empty()
        if signals:
            st.dataframe(pd.DataFrame(signals), use_container_width=True)
        else:
            st.error("Veri çekilemedi.")
