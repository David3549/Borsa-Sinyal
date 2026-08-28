import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Öncü Balina & Opsiyon Radarı", layout="wide")
st.title("🐋 Öncü Balina Akışı & Net Yön Radarı")

st.write("""
Bu radarda amaç standart teknik analiz değil; **balinaların ve kurumsal fonların opsiyon piyasasında nereye olta attığını (Call/Put), hedef fiyatlarını ve potansiyel patlama yönünü** hareket başlamadan önce önden haber almaktır.
""")

# Popüler Dev Şirketler Listesi
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

        call_vol, put_vol = 0, 0
        call_oi, put_oi = 0, 0
        avg_iv = 0
        max_strike_call = 0
        max_strike_put = 0

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
                    
                    # En çok pozisyon yığılan Call hedef fiyatı (Strike)
                    sorted_calls = calls.sort_values(by=['openInterest', 'volume'], ascending=False)
                    if not sorted_calls.empty:
                        max_strike_call = sorted_calls.iloc[0]['strike']
                else:
                    iv_c = 0

                if not puts.empty:
                    put_vol = puts['volume'].fillna(0).sum()
                    put_oi = puts['openInterest'].fillna(0).sum()
                    iv_p = puts['impliedVolatility'].dropna().mean()
                    
                    # En çok pozisyon yığılan Put seviyesi (Strike)
                    sorted_puts = puts.sort_values(by=['openInterest', 'volume'], ascending=False)
                    if not sorted_puts.empty:
                        max_strike_put = sorted_puts.iloc[0]['strike']
                else:
                    iv_p = 0

                iv_c = 0 if np.isnan(iv_c) else iv_c
                iv_p = 0 if np.isnan(iv_p) else iv_p
                avg_iv = round(((iv_c + iv_p) / 2) * 100, 1)

        except Exception:
            pass

        total_vol = call_vol + put_vol
        total_oi = call_oi + put_oi

        # Hafta içi canlı hacim, hafta sonu kapanış OI takibi
        if total_vol > 0:
            call_ratio = (call_vol / total_vol) * 100
            put_ratio = (put_vol / total_vol) * 100
            vol_oi_ratio = round(total_vol / total_oi, 2) if total_oi > 0 else 1.0
            data_mode = "Canlı İşlem Akışı"
        elif total_oi > 0:
            call_ratio = (call_oi / total_oi) * 100
            put_ratio = (put_oi / total_oi) * 100
            vol_oi_ratio = 1.0
            data_mode = "Son Kapanış OI (Hafta Sonu)"
        else:
            call_ratio, put_ratio = 50.0, 50.0
            vol_oi_ratio = 1.0
            data_mode = "Veri Yok"

        # Net Türkçe Yorum Üretici
        if call_ratio >= 60:
            whale_action = f"🚀 YUKARI OLTASI: Balinalar %{int(call_ratio)} oranında CALL pozisyonuna yığılmış."
            if max_strike_call > current_price:
                target_comment = f"Özellikle **{max_strike_call}$** hedef fiyatlı kontratlara devasa alım yapılmış. Fiyatı buraya taşımak istiyorlar."
            else:
                target_comment = "Kaldıraçlı yükseliş bahisleri çok baskın."
        elif put_ratio >= 60:
            whale_action = f"🔻 DÜŞÜŞ / KORUMA OLTASI: Balinalar %{int(put_ratio)} oranında PUT pozisyonuna yığılmış."
            if max_strike_put < current_price:
                target_comment = f"Özellikle **{max_strike_put}$** seviyesine doğru bir düşüş beklentisi veya sert korunma pozisyonu var."
            else:
                target_comment = "Aşağı yönlü baskı veya hedge alımları ağırlıkta."
        else:
            whale_action = f"⚖️ NÖTR / KARARSIZ: Hacim %{int(call_ratio)} Call - %{int(put_ratio)} Put olarak dengeli kalmış."
            target_comment = "Balinalar şu an net bir yön seçmemiş, yatay veya belirsiz bir bekleyiş var."

        if avg_iv > 70:
            iv_comment = f"⚠️ **Yüksek Oynaklık Uyarısı (IV %{avg_iv}):** Hissede yakın zamanda çok sert bir patlama bekleniyor!"
        else:
            iv_comment = f"Sakin volatilite ortamı (IV %{avg_iv})."

        return {
            "Hisse": clean_symbol,
            "Fiyat ($)": round(current_price, 2),
            "Günlük %": round(price_change, 2),
            "RSI": round(rsi, 1),
            "Call Oranı": f"%{int(call_ratio)}",
            "Put Oranı": f"%{int(put_ratio)}",
            "Call Hedef Fiyatı": f"${max_strike_call}" if max_strike_call else "Bilinmiyor",
            "Put Koruma Fiyatı": f"${max_strike_put}" if max_strike_put else "Bilinmiyor",
            "Balina Eylemi": whale_action,
            "Hedef Detayı": target_comment,
            "Volatilite Beklentisi": iv_comment,
            "Sıra Dışı Kat": f"{vol_oi_ratio}x",
            "Veri Durumu": data_mode
        }

    except Exception:
        return None

# Sekmeli Arayüz
tab1, tab2 = st.tabs(["🔍 Tek Hisse Olta Sorgula", "🚀 Toplu Balina Taraması"])

# --- TAB 1: ARAMA KUTUSU ---
with tab1:
    st.subheader("Hisse Kodu Arayın (Balinalar Nereye Olta Attı?)")
    search_ticker = st.text_input("Hisse Kodu Girin (Örn: NVDA, TSLA, AAPL, COP...)", "NVDA")
    
    if st.button("🔎 Balina Pozisyonlarını Açıkla", type="primary"):
        with st.spinner(f"{search_ticker.upper()} inceleniyor..."):
            res = get_complete_analysis(search_ticker)
            if res:
                st.success(f"{res['Hisse']} - Balina Analiz Raporu")
                
                col1, col2, col3 = st.columns(3)
                col1.metric("Son Fiyat", f"${res['Fiyat ($)']}", f"%{res['Günlük %']}")
                col2.metric("Call (Yükseliş) Ağırlığı", res['Call Oranı'])
                col3.metric("Put (Düşüş) Ağırlığı", res['Put Oranı'])
                
                st.divider()
                st.subheader("🧠 Balinalar Nereye Olta Attı?")
                st.info(f"**Durum:** {res['Balina Eylemi']}")
                st.write(f"🎯 **Hedef Detayı:** {res['Hedef Detayı']}")
                st.warning(res['Volatilite Beklentisi'])
                
                st.divider()
                col_a, col_b = st.columns(2)
                col_a.write(f"📌 **En Çok Yığılan Call Hedefi (Strike):** {res['Call Hedef Fiyatı']}")
                col_b.write(f"📌 **En Çok Yığılan Put Seviyesi (Strike):** {res['Put Koruma Fiyatı']}")
                st.caption(f"Veri Durumu: {res['Veri Durumu']} | RSI: {res['RSI']}")
            else:
                st.error("Hisse bulunamadı veya veri alınamadı. Lütfen geçerli bir hisse kodu girin.")

# --- TAB 2: TOPLU TARAMA ---
with tab2:
    st.subheader("Toplu Balina Taraması & Yön Açıklamaları")
    if st.button("🚀 Tüm Listeyi Tara ve Yorumla"):
        signals = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        total = len(DEFAULT_TICKERS)

        for idx, t in enumerate(DEFAULT_TICKERS):
            status_text.text(f"Balina oltaları taranıyor ({idx+1}/{total}): {t}")
            progress_bar.progress((idx + 1) / total)
            res = get_complete_analysis(t)
            if res:
                signals.append({
                    "Hisse": res["Hisse"],
                    "Fiyat ($)": res["Fiyat ($)"],
                    "Günlük %": res["Günlük %"],
                    "Call/Put Dağılımı": f"{res['Call Oranı']} Call / {res['Put Oranı']} Put",
                    "Balina Yorumu & Olta Yönü": res["Balina Eylemi"],
                    "Call Hedef Strike": res["Call Hedef Fiyatı"],
                    "RSI": res["RSI"],
                    "Veri Durumu": res["Veri Durumu"]
                })

        status_text.empty()
        progress_bar.empty()

        if signals:
            df = pd.DataFrame(signals)
            st.dataframe(df, use_container_width=True)
        else:
            st.error("Veri çekilemedi.")
