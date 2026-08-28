import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Hisse & Opsiyon Analiz ve Arama Paneli", layout="wide")
st.title("🎯 Hisse & Opsiyon Arama ve Sinyal Radarı")

st.write("""
Bu panel ile ister **istediğin hisseyi aratarak** tüm Call/Put opsiyon akışını ve Hisse/Opsiyon sinyallerini inceleyebilir, 
ister **Toplu Tarama** ile piyasadaki öne çıkan fırsatları yakalayabilirsin.
""")

# Varsayılan Popüler Listemiz
DEFAULT_TICKERS = [
    "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "MSFT", "PLTR", "META", "GOOGL", "NFLX",
    "INTC", "AVGO", "COST", "COIN", "MARA", "BABA", "ARM", "MU", "PYPL", "BAC",
    "DIS", "BA", "SMCI", "ADBE", "CRWD", "PANW", "MRVL", "HOOD", "RBLX", "SQ"
]

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_complete_analysis(ticker_symbol):
    """Tek bir hissenin detaylı analizini yapar"""
    try:
        clean_symbol = ticker_symbol.strip().upper()
        tk = yf.Ticker(clean_symbol)
        hist = tk.history(period="1mo")
        
        if hist.empty or len(hist) < 3:
            return None

        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        price_change = ((current_price - prev_price) / prev_price) * 100
        
        rsi = calculate_rsi(hist).iloc[-1] if len(hist) >= 14 else 50.0

        # --- OPSİYON VE BALİNA ANALİZİ ---
        call_vol, put_vol = 0, 0
        call_oi, put_oi = 0, 0
        avg_iv = 0

        try:
            expirations = tk.expirations
            if expirations:
                nearest_exp = expirations[0]
                opt = tk.option_chain(nearest_exp)

                calls = opt.calls if opt.calls is not None else pd.DataFrame()
                puts = opt.puts if opt.puts is not None else pd.DataFrame()

                if not calls.empty:
                    call_vol = calls['volume'].fillna(0).sum()
                    call_oi = calls['openInterest'].fillna(0).sum()
                    iv_c = calls['impliedVolatility'].dropna().mean()
                else:
                    iv_c = 0

                if not puts.empty:
                    put_vol = puts['volume'].fillna(0).sum()
                    put_oi = puts['openInterest'].fillna(0).sum()
                    iv_p = puts['impliedVolatility'].dropna().mean()
                else:
                    iv_p = 0

                iv_c = 0 if np.isnan(iv_c) else iv_c
                iv_p = 0 if np.isnan(iv_p) else iv_p
                avg_iv = round(((iv_c + iv_p) / 2) * 100, 1)

        except Exception:
            pass

        total_vol = call_vol + put_vol
        total_oi = call_oi + put_oi

        if total_vol > 0:
            call_ratio = (call_vol / total_vol) * 100
            put_ratio = (put_vol / total_vol) * 100
            vol_oi_ratio = round(total_vol / total_oi, 2) if total_oi > 0 else 1.0
            data_mode = "Canlı Akış"
        elif total_oi > 0:
            call_ratio = (call_oi / total_oi) * 100
            put_ratio = (put_oi / total_oi) * 100
            vol_oi_ratio = 1.0
            data_mode = "Son Kapanış OI"
        else:
            call_ratio, put_ratio = 50.0, 50.0
            vol_oi_ratio = 1.0
            data_mode = "Veri Yok"

        # --- 1. HİSSE YÖN SİNYALİ (Spot Fiyat) ---
        stock_score = 50
        if rsi < 42: stock_score += 25
        elif rsi > 62: stock_score -= 25
        if price_change > 0.8: stock_score += 15
        elif price_change < -0.8: stock_score -= 15

        if stock_score >= 65:
            stock_signal = "🟢 YÜKSELİŞ (AL)"
        elif stock_score <= 35:
            stock_signal = "🔴 DÜŞÜŞ (SAT)"
        else:
            stock_signal = "⚖️ NÖTR / YATAY"

        # --- 2. OPSİYON YÖN SİNYALİ (Call / Put) ---
        if vol_oi_ratio > 1.2 or avg_iv > 75:
            if call_ratio >= 60:
                option_signal = "🚨 OLAĞANDIŞI CALL BALİNA"
            elif put_ratio >= 60:
                option_signal = "🚨 OLAĞANDIŞI PUT BALİNA"
            else:
                option_signal = "⚡ YÜKSEK VOLATİLİTE"
        elif call_ratio >= 60:
            option_signal = "🟢 CALL AĞIRLIKLI"
        elif put_ratio >= 60:
            option_signal = "🔴 PUT AĞIRLIKLI"
        else:
            option_signal = "⚖️ KARARSIZ / DENGELİ"

        return {
            "Hisse": clean_symbol,
            "Hisse Yönü (Spot)": stock_signal,
            "Opsiyon Yönü": option_signal,
            "Fiyat ($)": round(current_price, 2),
            "Günlük %": round(price_change, 2),
            "Call / Put Dağılımı": f"%{int(call_ratio)} Call / %{int(put_ratio)} Put",
            "Call Hacim/OI": int(call_vol) if total_vol > 0 else int(call_oi),
            "Put Hacim/OI": int(put_vol) if total_vol > 0 else int(put_oi),
            "Sıra Dışı Kat (Vol/OI)": f"{vol_oi_ratio}x",
            "Beklenen Oynaklık (IV)": f"%{avg_iv}",
            "RSI": round(rsi, 1),
            "Veri Durumu": data_mode
        }

    except Exception:
        return None

# --- ARAYÜZ VE ARAMA SEKMELERİ ---
tab1, tab2 = st.tabs(["🔍 Tek Hisse Ara / Sorgula", "🚀 Toplu Liste Taraması"])

# --- SEKMELER 1: TEK HİSSE ARAMA ---
with tab1:
    st.subheader("Hisse Kodu Girin")
    search_ticker = st.text_input("Örn: NVDA, TSLA, AAPL, COP...", "NVDA")
    
    if st.button("🔎 Hisseyi Analiz Et", type="primary"):
        with st.spinner(f"{search_ticker.upper()} analiz ediliyor..."):
            res = get_complete_analysis(search_ticker)
            if res:
                st.success(f"{res['Hisse']} Analiz Sonuçları")
                
                # Özet Metrik Kutuları
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Son Fiyat ($)", f"${res['Fiyat ($)']}", f"%{res['Günlük %']}")
                col2.metric("Hisse Yönü", res['Hisse Yönü (Spot)'])
                col3.metric("Opsiyon Yönü", res['Opsiyon Yönü'])
                col4.metric("RSI Seviyesi", res['RSI'])
                
                st.divider()
                st.write("📋 **Detaylı Opsiyon & Teknik Tablosu:**")
                st.json(res)
            else:
                st.error("Hisse bulunamadı veya veri alınamadı. Hisse kodunu kontrol edin.")

# --- SEKMELER 2: TOPLU TARAMA ---
with tab2:
    st.subheader("Popüler Hisselerde Toplu Balina & Sinyal Radarı")
    if st.button("🚀 Tüm Listeyi Tara"):
        signals = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total = len(DEFAULT_TICKERS)

        for idx, t in enumerate(DEFAULT_TICKERS):
            status_text.text(f"Taranıyor ({idx+1}/{total}): {t}")
            progress_bar.progress((idx + 1) / total)
            res = get_complete_analysis(t)
            if res:
                signals.append(res)

        status_text.empty()
        progress_bar.empty()

        if signals:
            df = pd.DataFrame(signals)
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Veri çekilemedi.")
