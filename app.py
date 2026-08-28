import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Öncü Balina & Nasdaq 100 Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Nasdaq 100 Radarı")

# --- API KEY GİRİŞİ ---
st.sidebar.header("🔑 API Ayarları")
api_key = st.sidebar.text_input("Alpha Vantage API Key Girin:", type="password", help="alphavantage.co adresinden 15 saniyede ücretsiz alabilirsiniz.")

if not api_key:
    st.warning("⚠️ Lütfen verilerin IP engeline takılmadan %100 çekilebilmesi için sol menüden ücretsiz **Alpha Vantage API Key**'inizi girin.")

NASDAQ_100_TICKERS = [
    "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "AMD",
    "PEP", "TMUS", "LIN", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM", "TXN"
]

def get_alpha_vantage_data(symbol, key):
    clean_symbol = symbol.strip().upper().replace('.', '-')
    
    # 1. Hisse Fiyat Verisi (GLOBAL_QUOTE)
    quote_url = f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={clean_symbol}&apikey={key}"
    try:
        q_res = requests.get(quote_url, timeout=10).json()
        g_quote = q_res.get("Global Quote", {})
        
        price = float(g_quote.get("05. price", 0))
        change_percent_str = g_quote.get("10. change percent", "0%").replace('%', '')
        price_change = float(change_percent_str)
    except Exception:
        # Fiyat çekilemezse varsayılan değerler
        price = 0.0
        price_change = 0.0

    # 2. Opsiyon Chain Verisi (HISTORICAL_OPTIONS)
    opt_url = f"https://www.alphavantage.co/query?function=HISTORICAL_OPTIONS&symbol={clean_symbol}&apikey={key}"
    
    try:
        opt_res = requests.get(opt_url, timeout=12).json()
        opt_data = opt_res.get("data", [])
        
        if not opt_data:
            return None

        df_opts = pd.DataFrame(opt_data)
        
        # Sayısal alanları dönüştür
        df_opts['volume'] = pd.to_numeric(df_opts.get('volume', 0), errors='coerce').fillna(0)
        df_opts['open_interest'] = pd.to_numeric(df_opts.get('open_interest', 0), errors='coerce').fillna(0)
        df_opts['strike'] = pd.to_numeric(df_opts.get('strike', 0), errors='coerce').fillna(0)
        
        # Call / Put Ayrımı
        calls = df_opts[df_opts['type'].str.lower() == 'call'] if 'type' in df_opts.columns else pd.DataFrame()
        puts = df_opts[df_opts['type'].str.lower() == 'put'] if 'type' in df_opts.columns else pd.DataFrame()

        call_vol = calls['volume'].sum() if not calls.empty else 0
        put_vol = puts['volume'].sum() if not puts.empty else 0
        call_oi = calls['open_interest'].sum() if not calls.empty else 0
        put_oi = puts['open_interest'].sum() if not puts.empty else 0

        max_strike_call = None
        max_strike_put = None

        if not calls.empty:
            calls['score'] = calls['open_interest'] + calls['volume']
            if not calls[calls['score'] > 0].empty:
                max_strike_call = calls.sort_values(by='score', ascending=False).iloc[0]['strike']

        if not puts.empty:
            puts['score'] = puts['open_interest'] + puts['volume']
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

        stock_signal = "🟢 YÜKSELİŞ" if price_change >= 0 else "🔴 DÜŞÜŞ"

        return {
            "Hisse": clean_symbol,
            "Fiyat ($)": round(price, 2),
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
            "Veri Durumu": "Alpha Vantage Official API"
        }

    except Exception:
        return None

# Arayüz
tab1, tab2 = st.tabs(["🔍 Tek Hisse Olta Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

with tab1:
    st.subheader("Hisse Kodu Arayın")
    search_ticker = st.text_input("Hisse Kodu Girin (Örn: NVDA, TSLA, AAPL)", "NVDA")
    
    if st.button("🔎 Hisseyi Analiz Et", type="primary"):
        if not api_key:
            st.error("Lütfen sol menüden Alpha Vantage API Key'inizi girin.")
        else:
            with st.spinner(f"{search_ticker.upper()} inceleniyor..."):
                res = get_alpha_vantage_data(search_ticker, api_key)
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
                    st.error("Veri alınamadı. API Key'inizi kontrol edin veya günlük istek limitini aşmadığınızdan emin olun.")

with tab2:
    st.subheader("Nasdaq 100 Toplu Tarama")
    scan_limit = st.slider("Taranacak Hisse Sayısı", 5, len(NASDAQ_100_TICKERS), 10)
    
    if st.button("🚀 Seçilen Hisseleri Tara", type="primary"):
        if not api_key:
            st.error("Lütfen sol menüden Alpha Vantage API Key'inizi girin.")
        else:
            signals = []
            progress_bar = st.progress(0)
            target_tickers = NASDAQ_100_TICKERS[:scan_limit]
            
            for idx, t in enumerate(target_tickers):
                progress_bar.progress((idx + 1) / len(target_tickers))
                res = get_alpha_vantage_data(t, api_key)
                if res:
                    signals.append(res)
            
            progress_bar.empty()
            if signals:
                st.dataframe(pd.DataFrame(signals), use_container_width=True)
            else:
                st.error("Veri çekilemedi.")
