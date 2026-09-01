import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Borsa & Trend Takip Paneli", page_icon="📈", layout="wide"
)

st.title("📈 Canlı Borsa ve Trend Takip Paneli")
st.markdown("S&P 500 / Nasdaq Devleri Canlı Fiyat, Hacim ve Teknik Sinyaller")

stock_tickers = [
    "NVDA",
    "AAPL",
    "MSFT",
    "AMZN",
    "GOOGL",
    "META",
    "TSLA",
    "AVGO",
    "AMD",
    "NFLX",
]

# Sekmeler
tab1, tab2 = st.tabs(["📊 Canlı Fiyat & Hacim Takibi", "⚙️ Teknik Sinyaller (SMA)"])

with tab1:
  st.subheader("Piyasa Devleri Anlık Durum ve Hacimler")
  if st.button("Fiyatları ve Hacimleri Güncelle"):
    with st.spinner("Canlı piyasa verileri çekiliyor..."):
      live_results = []
      for ticker in stock_tickers:
        try:
          t = yf.Ticker(ticker)
          hist = t.history(period="2d")
          if hist.empty:
            continue

          current_price = hist["Close"].iloc[-1]
          prev_close = hist["Close"].iloc[-2]
          change_pct = ((current_price - prev_close) / prev_close) * 100
          volume = int(hist["Volume"].iloc[-1])

          live_results.append({
              "Hisse": ticker,
              "Fiyat ($)": round(current_price, 2),
              "Günlük Değişim (%)": round(change_pct, 2),
              "Günlük Hacim": volume,
          })
        except Exception as e:
          pass

      if live_results:
        df_live = pd.DataFrame(live_results)
        st.dataframe(df_live, use_container_width=True)
      else:
        st.warning(
            "Veriler alınamadı, lütfen birkaç saniye sonra tekrar deneyin."
        )

with tab2:
  st.subheader("Teknik Sinyaller (SMA 20 / 50)")
  if st.button("Hisseleri Tara ve Sinyal Al"):
    with st.spinner("Teknik göstergeler hesaplanıyor..."):
      results = []
      for ticker in stock_tickers:
        try:
          t = yf.Ticker(ticker)
          hist = t.history(period="3mo")
          if hist.empty:
            continue

          current_price = hist["Close"].iloc[-1]
          sma_20 = hist["Close"].rolling(window=20).mean().iloc[-1]
          sma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]

          if current_price > sma_20:
            durum = "🟢 Yükseliş (AL)"
          else:
            durum = "🔴 Düşüş / Yatay"

          results.append({
              "Hisse": ticker,
              "Fiyat ($)": round(current_price, 2),
              "SMA 20": round(sma_20, 2),
              "SMA 50": round(sma_50, 2),
              "Durum": durum,
          })
        except Exception as e:
          pass

      if results:
        df_signals = pd.DataFrame(results)
        st.dataframe(df_signals, use_container_width=True)
      else:
        st.warning("Teknik veriler şu an yüklenemedi.")
