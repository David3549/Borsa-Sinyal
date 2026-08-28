import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Nasdaq 100 Hisse & Opsiyon Radarı", layout="wide")
st.title("🎯 Nasdaq 100 Hisse (Al/Sat) & Opsiyon (Call/Put) Radarı")

st.write("""
Bu panel; **Nasdaq 100** hisselerinin tümünü tarayarak **Spot Fiyat Yönünü (Yükseliş/Düşüş)** ve 
**Opsiyon Akış Eğilimini (Call/Put)** fiyat hareketleri, RSI indikatörü ve hacim dağılımına göre analiz eder.
""")

# --- NASDAQ 100 HİSSE LİSTESİNİ OTOMATİK ÇEKER ---
@st.cache_data
def get_nasdaq100_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url)
        for table in tables:
            if 'Ticker' in table.columns:
                return table['Ticker'].tolist()
            elif 'Symbol' in table.columns:
                return table['Symbol'].tolist()
    except Exception:
        # Bağlantı hatası olursa yedek geniş liste
        return [
            "NVDA", "TSLA", "AAPL", "AMD", "AMZN", "MSFT", "PLTR", "META", "GOOGL", "NFLX",
            "INTC", "AVGO", "COST", "PEP", "TMUS", "CSCO", "TMUS", "TXN", "QCOM", "AMAT"
        ]

TICKERS = get_nasdaq100_tickers()

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
        # Ticker sembollerindeki noktaları yfinance uyumlu tireye çevir (.) -> (-)
        clean_symbol = str(ticker_symbol).replace('.', '-')
        status_text.text(f"Nasdaq 100 Taranıyor ({idx+1}/{total}): {clean_symbol}")
        progress_bar.progress((idx + 1) / total)

        try:
            tk = yf.Ticker(clean_symbol)
            hist = tk.history(period="1mo")
            if hist.empty or len(hist) < 5:
                continue

            current_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            price_change = ((current_price - prev_price) / prev_price) * 100
            
            # RSI Hesaplama
            if len(hist) >= 14:
                hist['RSI'] = calculate_rsi(hist)
                rsi = hist['RSI'].iloc[-1]
            else:
                rsi = 50.0

            # 1. Opsiyon Akış Verisi
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
            if call_ratio > 55: option_score += 30
            elif put_ratio > 55: option_score -= 30

            if stock_score >= 65: option_score += 10
            elif stock_score <= 35: option_score -= 10

            if option_score >= 65:
                option_signal = "🟢 CALL"
            elif option_score <= 35:
                option_signal = "🔴 PUT"
            else:
                option_signal = "⚖️ KARARSIZ"

            signals.append({
                "Hisse": clean_symbol,
                "Hisse Yönü": stock_signal,
                "Opsiyon Yönü": option_signal,
                "Fiyat ($)": round(current_price, 2),
                "Günlük %": round(price_change, 2),
                "RSI": round(rsi, 1),
                "Opsiyon Dağılımı": f"%{int(call_ratio)} Call / %{int(put_ratio)} Put" if total_opt_vol > 0 else "Veri Yok / Kapalı"
            })

        except Exception:
            continue

    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(signals)

if st.button("🚀 Tüm Nasdaq 100 Hisselerini Tara", type="primary"):
    with st.spinner("Nasdaq 100 hisseleri ve opsiyon zincirleri taranıyor..."):
        df = analyze_stock_and_options(TICKERS)
        if not df.empty:
            st.success(f"Tarama tamamlandı! Toplam {len(df)} Nasdaq 100 hissesi analiz edildi.")
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Veri çekilemedi. Lütfen tekrar deneyin.")
