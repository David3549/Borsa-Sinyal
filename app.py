import pandas as pd
import streamlit as st
import yfinance as yf
from datetime import datetime

st.set_page_config(
    page_title="Borsa & Opsiyon Sinyal Paneli", page_icon="📈", layout="wide"
)

st.title("📈 Canlı Borsa ve Opsiyon Takip Paneli")
st.markdown("S&P 500 / Nasdaq Devleri & Ultra Kısa Vade (0DTE/1-3 Gün) Opsiyon Analizi")

# Ticker listesi
option_tickers = ["NVDA", "AAPL", "MSFT", "TSLA", "META", "AMZN"]
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
tab1, tab2 = st.tabs(
    ["🎯 0DTE & Kısa Vade Opsiyon Duygu Analizi", "📊 Hisse Trend & Sinyaller"]
)

with tab1:
  st.subheader("En Yakın Vade (0DTE / Yakın Tarih) Opsiyon Dağılımı ve Sinyal")
  if st.button("Opsiyon Verilerini Güncelle"):
    with st.spinner("Opsiyon zincirleri taranıyor..."):
      opt_results = []

      for ticker_symbol in option_tickers:
        try:
          stock = yf.Ticker(ticker_symbol)
          exp_dates = stock.options
          if not exp_dates:
            continue

          # Hacmi olan en yakın geçerli vadeyi bulmak için döngü
          valid_chain = None
          chosen_date = None

          for d in exp_dates[:3]:  # İlk 3 vadeyi kontrol et
            opt_chain = stock.option_chain(d)
            if (
                not opt_chain.calls.empty
                and opt_chain.calls["volume"].sum() > 0
            ):
              valid_chain = opt_chain
              chosen_date = d
              break

          # Eğer ilk vadelerde hacim yoksa ilk tarihi direkt baz al
          if valid_chain is None:
            chosen_date = exp_dates[0]
            valid_chain = stock.option_chain(chosen_date)

          calls = valid_chain.calls
          puts = valid_chain.puts

          total_call_vol = calls["volume"].fillna(0).sum()
          total_put_vol = puts["volume"].fillna(0).sum()

          pc_ratio = (
              round(total_put_vol / total_call_vol, 2)
              if total_call_vol > 0
              else 0
          )

          # Kısa vade / Yön Stratejisi
          if total_call_vol > total_put_vol:
            sinyal = "🟢 CALL AĞIRLIKLI (Yükseliş Beklentisi)"
          elif total_put_vol > total_call_vol:
            sinyal = "🔴 PUT AĞIRLIKLI (Düşüş/Koruma)"
          else:
            sinyal = "⚪ NÖTR / DENGELİ"

          # Güncel fiyatı güvenli çekme
          hist_data = stock.history(period="5d")
          if not hist_data.empty:
            current_price = hist_data["Close"].iloc[-1]
          else:
            current_price = 0.0

          opt_results.append({
              "Hisse": ticker_symbol,
              "Fiyat ($)": round(current_price, 2),
              "Vade": chosen_date,
              "Call Hacim": int(total_call_vol),
              "Put Hacim": int(total_put_vol),
              "P/C Oranı": pc_ratio,
              "0DTE/Kısa Vade Yönü": sinyal,
          })
        except Exception as e:
          st.error(f"{ticker_symbol} Hata: {e}")

      if opt_results:
        df_options = pd.DataFrame(opt_results)
        st.dataframe(df_options, use_container_width=True)
      else:
        st.warning(
            "Şu an gösterilecek opsiyon verisi bulunamadı. Lütfen piyasa"
            " saatlerinde tekrar deneyin."
        )

with tab2:
  st.subheader("Teknik Sinyaller (SMA 20 / 50)")
  if st.button("Hisseleri Tara"):
    with st.spinner("Hisse verileri indiriliyor..."):
      results = []
      for ticker_symbol in stock_tickers:
        try:
          stock = yf.Ticker(ticker_symbol)
          hist = stock.history(period="3mo")
          if hist.empty:
            continue

          current_price = hist["Close"].iloc[-1]
          sma_20 = hist["Close"].rolling(window=20).mean().iloc[-1]
          sma_50 = hist["Close"].rolling(window=50).mean().iloc[-1]

          if current_price > sma_20:
            durum = "Yükseliş (AL)"
          else:
            durum = "Düşüş / Yatay"

          results.append({
              "Hisse": ticker_symbol,
              "Fiyat ($)": round(current_price, 2),
              "SMA 20": round(sma_20, 2),
              "SMA 50": round(sma_50, 2),
              "Durum": durum,
          })
        except Exception as e:
          st.error(f"{ticker_symbol} Hata: {e}")

      df_signals = pd.DataFrame(results)
      st.dataframe(df_signals, use_container_width=True)
