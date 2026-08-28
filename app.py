import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Hisse & Opsiyon Çift Yönlü Analiz Paneli", layout="wide")
st.title("🎯 Hisse (Al/Sat) & Opsiyon (Call/Put) Sinyal Radarı")

st.write("""
Bu panel; hisselerin **Spot Fiyat Yönünü (Yükseliş/Düşüş)** ve **Opsiyon Eğilimini (Call/Put)** 
fiyat akışı ve teknik indikatörleri (RSI) harmanlayarak hesaplar.
""")

OPTION_TICKERS = [
    "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "MSFT", "PLTR", "META", 
    "GOOGL", "NFLX", "SPY", "QQQ", "COIN", "MARA", "BABA", "INTC"
]

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def analyze_stock_and_options(tickers):
    signals = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    total = len(tickers)

    for idx, ticker_symbol in enumerate(tickers):
        status_text.text(f"Analiz Ediliyor ({idx+1}/{total}): {ticker_symbol}")
        progress_bar.progress((idx + 1) / total)

        try:
            tk = yf.Ticker(ticker_symbol)
            hist = tk.history(period="1mo")
            if hist.empty or len(hist) < 5:
                continue

            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            # RSI Güvenli Hesaplama
            if len(hist) >= 14:
                hist['RSI'] = calculate_rsi(hist)
                rsi = hist['RSI'].iloc[-1]
            else:
                rsi = 50.0

            # 1. Opsiyon Akışı
            call_vol, put_vol = 0, 0
            try:
                expirations = tk.expirations
                if expirations:
                    nearest_exp = expirations[0]
                    opt = tk.option_chain(nearest_exp)
                    
                    if opt.calls is not None and not opt.calls.empty and 'volume' in opt.calls:
                        call_vol = opt.calls['volume'].fillna(0).sum()
                    
                    if opt.puts is not None and not opt.puts.empty and 'volume' in opt.puts:
                        put_vol = opt.puts['volume'].fillna(0).sum()
            except Exception:
                pass

            total_opt_vol = call_vol + put_vol
            if total_opt_vol > 0:
                call_ratio = (call_vol / total_opt_vol) * 100
                put_ratio = (put_vol / total_opt_vol) * 100
            else:
                call_ratio, put_ratio = 50.0, 50.0

            # 2. HİSSE YÖNÜ HESAPLAMA (Spot Fiyat)
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

            # 3. OPSİYON YÖNÜ HESAPLAMA
            option_score = 50
            if call_ratio > 58: option_score += 30
            elif put_ratio > 58: option_score -= 30

            if stock_score >= 65: option_score += 10
            elif stock_score <= 35: option_score -= 10

            if option_score >= 65:
                option_signal = "🟢 CALL"
            elif option_score <= 35:
                option_signal = "🔴 PUT"
            else:
                option_signal = "⚖️ KARARSIZ"

            signals.append({
                "Hisse": ticker_symbol,
                "Hisse Yönü": stock_signal,
                "Opsiyon Yönü": option_signal,
                "Fiyat ($)": round(current_price, 2),
                "Günlük %": round(price_change, 2),
                "RSI": round(rsi, 1),
                "Opsiyon Hacim Dağılımı": f"%{int(call_ratio)} Call / %{int(put_ratio)} Put"
            })

        except Exception as e:
            continue

    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(signals)

if st.button("🚀 Hisse & Opsiyon Analizini Başlat", type="primary"):
    with st.spinner("Piyasa verileri analiz ediliyor..."):
        df = analyze_stock_and_options(OPTION_TICKERS)
        if not df.empty:
            st.success(f"Analiz tamamlandı! Toplam {len(df)} hisse tarandı.")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Veri çekilemedi. Lütfen bağlantınızı kontrol edip tekrar deneyin.")
