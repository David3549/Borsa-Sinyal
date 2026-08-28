import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Öncü Balina & Opsiyon Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Sıra Dışı Opsiyon Radarı")

st.write("""
Bu radarda amaç standart teknik analiz değil; **balinaların ve kurumsal fonların önceden aldığı pozisyonları (Unusual Volume/OI, Yüksek IV ve Hacim Patlamaları)** tespit ederek hareket başlamadan önce önden haber almaktır.
""")

# Opsiyon Hareketliliği En Yüksek 40 Şirket
TICKERS = [
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

def scan_whale_signals(tickers):
    signals = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(tickers)

    for idx, ticker_symbol in enumerate(tickers):
        status_text.text(f"Balina Pozisyonları Taranıyor ({idx+1}/{total}): {ticker_symbol}")
        progress_bar.progress((idx + 1) / total)

        try:
            tk = yf.Ticker(ticker_symbol)
            hist = tk.history(period="1mo")
            if hist.empty or len(hist) < 5:
                continue

            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            rsi = calculate_rsi(hist).iloc[-1] if len(hist) >= 14 else 50.0

            # --- OPSİYON VE BALİNA ANALİZİ ---
            expirations = tk.expirations
            if not expirations:
                continue

            nearest_exp = expirations[0]
            opt = tk.option_chain(nearest_exp)

            calls = opt.calls.dropna(subset=['volume', 'openInterest']) if opt.calls is not None else pd.DataFrame()
            puts = opt.puts.dropna(subset=['volume', 'openInterest']) if opt.puts is not None else pd.DataFrame()

            call_vol = calls['volume'].sum() if not calls.empty else 0
            put_vol = puts['volume'].sum() if not puts.empty else 0
            total_vol = call_vol + put_vol

            if total_vol == 0:
                continue

            call_ratio = (call_vol / total_vol) * 100
            put_ratio = (put_vol / total_vol) * 100

            # Implied Volatility (Ortalama Oynaklık Beklentisi)
            avg_iv_calls = calls['impliedVolatility'].mean() if not calls.empty else 0
            avg_iv_puts = puts['impliedVolatility'].mean() if not puts.empty else 0
            avg_iv = round(((avg_iv_calls + avg_iv_puts) / 2) * 100, 1)

            # Vol / OI Oranı (Sıra Dışı Akış Hesabı)
            calls_vol_oi = (calls['volume'] / calls['openInterest'].replace(0, np.nan)).mean() if not calls.empty else 0
            puts_vol_oi = (puts['volume'] / puts['openInterest'].replace(0, np.nan)).mean() if not puts.empty else 0
            max_vol_oi = round(max(calls_vol_oi if not np.isnan(calls_vol_oi) else 0, 
                                   puts_vol_oi if not np.isnan(puts_vol_oi) else 0), 2)

            # --- SİNYAL ÜRETME ---
            whale_status = "⚪ normal Akış"
            
            # Sınıflandırma
            if max_vol_oi > 1.2 or avg_iv > 80:
                if call_ratio >= 65:
                    whale_status = "🚨 OLAĞANDIŞI BULLISH BALİNA"
                elif put_ratio >= 65:
                    whale_status = "🚨 OLAĞANDIŞI BEARISH BALİNA"
                else:
                    whale_status = "⚡ YÜKSEK VOLATİLİTE SİNYALİ"
            elif call_ratio >= 68:
                whale_status = "🟢 CALL AĞIRLIKLI"
            elif put_ratio >= 68:
                whale_status = "🔴 PUT AĞIRLIKLI"

            signals.append({
                "Hisse": ticker_symbol,
                "Balina Sinyali": whale_status,
                "Fiyat ($)": round(current_price, 2),
                "Günlük %": round(price_change, 2),
                "Call/Put Dağılımı": f"%{int(call_ratio)} Call / %{int(put_ratio)} Put",
                "Vol / OI (Sıra Dışı Katı)": f"{max_vol_oi}x",
                "Beklenen Volatolite (IV)": f"%{avg_iv}",
                "RSI": round(rsi, 1)
            })

        except Exception:
            continue

    status_text.empty()
    progress_bar.empty()
    
    df_res = pd.DataFrame(signals)
    if not df_res.empty:
        # Önceliği Olağanüstü Balina Akışlarına Ver
        df_res['Öncelik'] = df_res['Balina Sinyali'].apply(lambda x: 0 if '🚨' in x else (1 if '⚡' in x else 2))
        df_res = df_res.sort_values(by=['Öncelik', 'Vol / OI (Sıra Dışı Katı)'], ascending=[True, False]).drop(columns=['Öncelik'])
    
    return df_res

if st.button("🚨 Öncü Balina ve Opsiyon Akışını Tara", type="primary"):
    with st.spinner("Balina kontratları ve sıra dışı hacimler taranıyor..."):
        df = scan_whale_signals(TICKERS)
        if not df.empty:
            st.success("Öncü analiz tamamlandı! Sıra dışı balina hareketleri en üstte listelenmiştir.")
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("Veri çekilemedi veya kapalı piyasa nedeniyle veri bulunamadı.")
