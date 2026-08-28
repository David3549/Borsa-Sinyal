import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Öncü Balina & Opsiyon Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Sıra Dışı Opsiyon Radarı")

st.write("""
Bu radarda amaç standart teknik analiz değil; **balinaların ve kurumsal fonların önceden aldığı pozisyonları (Unusual Volume/OI, Yüksek IV ve Hacim Patlamaları)** tespit ederek hareket başlamadan önce önden haber almaktır.
""")

# Opsiyon Hareketliliği En Yüksek 30 Dev Şirket
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
            if hist.empty or len(hist) < 3:
                continue

            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            rsi = calculate_rsi(hist).iloc[-1] if len(hist) >= 14 else 50.0

            # --- OPSİYON VE BALİNA ANALİZİ (Güvenli Çekim) ---
            call_vol, put_vol = 0, 0
            avg_iv = 0
            max_vol_oi = 1.0

            try:
                expirations = tk.expirations
                if expirations:
                    nearest_exp = expirations[0]
                    opt = tk.option_chain(nearest_exp)

                    calls = opt.calls if opt.calls is not None else pd.DataFrame()
                    puts = opt.puts if opt.puts is not None else pd.DataFrame()

                    if not calls.empty:
                        call_vol = calls['volume'].fillna(0).sum()
                        iv_c = calls['impliedVolatility'].dropna().mean()
                    else:
                        iv_c = 0

                    if not puts.empty:
                        put_vol = puts['volume'].fillna(0).sum()
                        iv_p = puts['impliedVolatility'].dropna().mean()
                    else:
                        iv_p = 0

                    # Ortalama Volatilite Beklentisi (IV)
                    iv_c = 0 if np.isnan(iv_c) else iv_c
                    iv_p = 0 if np.isnan(iv_p) else iv_p
                    avg_iv = round(((iv_c + iv_p) / 2) * 100, 1)

                    # Hacim / OI Hesabı (Hata vermeyen yöntem)
                    c_vol_sum = calls['volume'].fillna(0).sum() if 'volume' in calls else 0
                    c_oi_sum = calls['openInterest'].fillna(0).sum() if 'openInterest' in calls else 0
                    p_vol_sum = puts['volume'].fillna(0).sum() if 'volume' in puts else 0
                    p_oi_sum = puts['openInterest'].fillna(0).sum() if 'openInterest' in puts else 0

                    tot_oi = c_oi_sum + p_oi_sum
                    tot_v = c_vol_sum + p_vol_sum

                    if tot_oi > 0 and tot_v > 0:
                        max_vol_oi = round(tot_v / tot_oi, 2)
            except Exception:
                pass

            total_vol = call_vol + put_vol

            if total_vol > 0:
                call_ratio = (call_vol / total_vol) * 100
                put_ratio = (put_vol / total_vol) * 100
            else:
                call_ratio, put_ratio = 50.0, 50.0

            # --- SİNYAL ÜRETME ---
            whale_status = "⚪ Normal Akış"
            
            if max_vol_oi > 1.2 or avg_iv > 75:
                if call_ratio >= 60:
                    whale_status = "🚨 OLAĞANDIŞI BULLISH BALİNA"
                elif put_ratio >= 60:
                    whale_status = "🚨 OLAĞANDIŞI BEARISH BALİNA"
                else:
                    whale_status = "⚡ YÜKSEK VOLATİLİTE SİNYALİ"
            elif call_ratio >= 65:
                whale_status = "🟢 CALL AĞIRLIKLI"
            elif put_ratio >= 65:
                whale_status = "🔴 PUT AĞIRLIKLI"

            signals.append({
                "Hisse": ticker_symbol,
                "Balina Sinyali": whale_status,
                "Fiyat ($)": round(current_price, 2),
                "Günlük %": round(price_change, 2),
                "Call/Put Dağılımı": f"%{int(call_ratio)} Call / %{int(put_ratio)} Put" if total_vol > 0 else "Piyasa Kapalı",
                "Vol / OI (Sıra Dışı Katı)": f"{max_vol_oi}x" if total_vol > 0 else "1.0x",
                "Beklenen Volatilitik (IV)": f"%{avg_iv}",
                "RSI": round(rsi, 1)
            })

        except Exception:
            continue

    status_text.empty()
    progress_bar.empty()
    
    return pd.DataFrame(signals)

if st.button("🚨 Öncü Balina ve Opsiyon Akışını Tara", type="primary"):
    with st.spinner("Balina kontratları ve sıra dışı hacimler taranıyor..."):
        df = scan_whale_signals(TICKERS)
        if not df.empty:
            st.success(f"Analiz tamamlandı! Toplam {len(df)} hisse tarandı.")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Veri çekilemedi. Bağlantınızı kontrol edin.")
