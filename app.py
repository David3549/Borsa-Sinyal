import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="Öncü Balina & Nasdaq 100 Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Nasdaq 100 Radarı")

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
    
    return [
        "NVDA", "AAPL", "MSFT", "AMZN", "GOOGL", "META", "TSLA", "AVGO", "COST", "ASML",
        "PEP", "TMUS", "LIN", "AMD", "CSCO", "NFLX", "AZN", "INTC", "ADBE", "QCOM"
    ]

NASDAQ_100_TICKERS = get_nasdaq100_tickers()

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- ÖZEL OPSİYON ÇEKİCİ (Crumble & Cookie Bypass) ---
def get_direct_options(ticker_symbol):
    """Yahoo IP Engelini Doğrudan v8 API ve Cookie İle Aşar"""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
        
        # 1. Aşama: Cookie & Crumb Alımı
        sess = requests.Session()
        sess.headers.update(headers)
        
        # Doğrudan query6 v8 endpoint sorgusu
        url = f"https://query6.finance.yahoo.com/v7/finance/options/{ticker_symbol}"
        res = sess.get(url, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            result = data['optionChain']['result'][0]
            options = result['options'][0]
            
            calls = pd.DataFrame(options.get('calls', []))
            puts = pd.DataFrame(options.get('puts', []))
            exp_date = result.get('expirationDates', [0])[0]
            
            return calls, puts, str(exp_date)
    except Exception:
        pass
    
    return pd.DataFrame(), pd.DataFrame(), ""

def get_complete_analysis(ticker_symbol):
    try:
        clean_symbol = ticker_symbol.strip().upper().replace('.', '-')
        tk = yf.Ticker(clean_symbol)
        hist = tk.history(period="1mo")
        
        if hist.empty or len(hist) < 3:
            return None

        current_price = hist['Close'].iloc[-1]
        prev_price = hist['Close'].iloc[-2]
        price_change = ((current_price - prev_price) / prev_price) * 100
        rsi = calculate_rsi(hist).iloc[-1] if len(hist) >= 14 else 50.0

        call_vol, put_vol = 0, 0
        call_oi, put_oi = 0, 0
        avg_iv = 0
        max_strike_call = None
        max_strike_put = None
        data_mode = "Veri Yok"

        # TIKANIKLIK AŞICI DÖNGÜ
        calls, puts, exp_date = get_direct_options(clean_symbol)
        
        # Eğer Doğrudan v8 Çalışmazsa Yfinance 'options' Taraması Yap
        if calls.empty and puts.empty:
            try:
                expirations = tk.expirations
                for exp in expirations[:3]:
                    opt = tk.option_chain(exp)
                    c = opt.calls
                    p = opt.puts
                    if not c.empty or not p.empty:
                        calls, puts = c, p
                        exp_date = exp
                        break
            except Exception:
                pass

        if not calls.empty or not puts.empty:
            call_vol = calls['volume'].fillna(0).sum() if not calls.empty else 0
            put_vol = puts['volume'].fillna(0).sum() if not puts.empty else 0
            call_oi = calls['openInterest'].fillna(0).sum() if not calls.empty else 0
            put_oi = puts['openInterest'].fillna(0).sum() if not puts.empty else 0

            iv_c = calls['impliedVolatility'].dropna().mean() if ('impliedVolatility' in calls.columns and not calls.empty) else 0
            iv_p = puts['impliedVolatility'].dropna().mean() if ('impliedVolatility' in puts.columns and not puts.empty) else 0
            avg_iv = round(((iv_c + iv_p) / 2) * 100, 1)

            if not calls.empty:
                calls['score'] = calls['openInterest'].fillna(0) + calls['volume'].fillna(0)
                max_strike_call = calls.sort_values(by='score', ascending=False).iloc[0]['strike']

            if not puts.empty:
                puts['score'] = puts['openInterest'].fillna(0) + puts['volume'].fillna(0)
                max_strike_put = puts.sort_values(by='score', ascending=False).iloc[0]['strike']

            data_mode = f"Aktif Vade ({exp_date})"

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

        # --- SPOT HİSSE SİNYALİ ---
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

        # --- OPSİYON SİNYALİ ---
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

        # Yorumlar
        if call_ratio >= 58:
            whale_action = f"🚀 YUKARI OLTASI: Balinalar %{int(call_ratio)} oranında CALL pozisyonuna yığılmış."
            target_comment = f"En yüksek kontrat yığılması **${max_strike_call}** hedef seviyesinde." if max_strike_call else "Yüksek Call ağırlıklı pozisyonlanma."
        elif put_ratio >= 58:
            whale_action = f"🔻 DÜŞÜŞ / KORUMA OLTASI: Balinalar %{int(put_ratio)} oranında PUT pozisyonuna yığılmış."
            target_comment = f"En yüksek koruma/düşüş yığılması **${max_strike_put}** seviyesinde." if max_strike_put else "Yüksek Put ağırlıklı koruma."
        else:
            whale_action = f"⚖️ NÖTR / KARARSIZ: Dağılım %{int(call_ratio)} Call - %{int(put_ratio)} Put olarak dengeli."
            target_comment = "Balinalar şu an net bir yön seçmemiş, yatay veya belirsiz bir bekleyiş var."

        if avg_iv > 70:
            iv_comment = f"⚠️ **Yüksek Oynaklık Uyarısı (IV %{avg_iv}):** Hissede yakın zamanda çok sert bir patlama bekleniyor!"
        else:
            iv_comment = f"Sakin volatilite ortamı (IV %{avg_iv})."

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
            "Beklenen Oynaklık (IV)": f"%{avg_iv}",
            "RSI": round(rsi, 1),
            "Call Hedef Fiyatı": f"${max_strike_call}" if max_strike_call is not None else "Veri Yok",
            "Put Koruma Fiyatı": f"${max_strike_put}" if max_strike_put is not None else "Veri Yok",
            "Balina Eylemi": whale_action,
            "Hedef Detayı": target_comment,
            "Volatilite Beklentisi": iv_comment,
            "Veri Durumu": data_mode
        }

    except Exception:
        return None

# Sekmeli Arayüz
tab1, tab2 = st.tabs(["🔍 Tek Hisse Olta Sorgula", "🚀 Nasdaq 100 Toplu Tarama"])

# --- TAB 1: ARAMA KUTUSU ---
with tab1:
    st.subheader("Hisse Kodu Arayın (Tüm Veriler & Balina Oltası)")
    search_ticker = st.text_input("Hisse Kodu Girin (Örn: NVDA, TSLA, AAPL, COP...)", "NVDA")
    
    if st.button("🔎 Hisseyi Analiz Et", type="primary"):
        with st.spinner(f"{search_ticker.upper()} inceleniyor..."):
            res = get_complete_analysis(search_ticker)
            if res:
                st.success(f"{res['Hisse']} - Balina & Teknik Analiz Raporu")
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Son Fiyat ($)", f"${res['Fiyat ($)']}", f"%{res['Günlük %']}")
                col2.metric("Hisse Yönü", res['Hisse Yönü (Spot)'])
                col3.metric("Opsiyon Yönü", res['Opsiyon Yönü'])
                col4.metric("Sıra Dışı Kat", res['Sıra Dışı Kat (Vol/OI)'])

                st.divider()
                st.subheader("🧠 Balinalar Nereye Olta Attı?")
                st.info(f"**Durum:** {res['Balina Eylemi']}")
                st.write(f"🎯 **Hedef Detayı:** {res['Hedef Detayı']}")
                st.warning(res['Volatilite Beklentisi'])
                
                st.divider()
                col_a, col_b = st.columns(2)
                col_a.write(f"📌 **En Çok Yığılan Call Hedefi (Strike):** {res['Call Hedef Fiyatı']}")
                col_b.write(f"📌 **En Çok Yığılan Put Seviyesi (Strike):** {res['Put Koruma Fiyatı']}")
                
                st.divider()
                st.write("📋 **Tüm Ham Veri & Detaylar:**")
                st.json(res)
            else:
                st.error("Hisse bulunamadı veya veri alınamadı. Lütfen geçerli bir hisse kodu girin.")

# --- TAB 2: NASDAQ 100 TOPLU TARAMA ---
with tab2:
    st.subheader(f"Nasdaq 100 Toplu Tarama ({len(NASDAQ_100_TICKERS)} Hisse)")
    
    scan_limit = st.slider("Taranacak Hisse Sayısı", min_value=10, max_value=len(NASDAQ_100_TICKERS), value=30, step=10)
    
    if st.button("🚀 Seçilen Hisseleri Tara", type="primary"):
        signals = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        target_tickers = NASDAQ_100_TICKERS[:scan_limit]
        total = len(target_tickers)

        for idx, t in enumerate(target_tickers):
            status_text.text(f"Nasdaq 100 Taranıyor ({idx+1}/{total}): {t}")
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
