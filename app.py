import pandas as pd
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Borsa & Opsiyon Sinyal Paneli", page_icon="📈", layout="wide"
)

st.title("📈 Canlı Borsa ve Opsiyon Takip Paneli")
st.markdown("S&P 500 / Nasdaq Devleri & Opsiyon Duygu Analizi")

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
    ["🚀 Opsiyon Duygu Analizi (P/C)", "📊 Hisse Trend & Sinyaller"]
)

with tab1:
  st.subheader("En Yakın Vade Opsiyon P/C Oranları")
  if st.button("Opsiyon Verilerini Güncelle"):
    with st.spinner("Opsiyon zincirleri taranıyor..."):
      opt_results = []
      for ticker_symbol in option_tickers:
        try:
          stock = yf.Ticker(ticker_symbol)
          exp_dates = stock.options
          if not exp_dates:
            continue
          nearest_date = exp_dates[0]
          opt_chain = stock.option_chain(nearest_date)
          calls = opt_chain.calls
          puts = opt_chain.puts

          total_call_vol = calls["volume"].fillna(0).sum()
          total_put_vol = puts["volume"].fillna(0).sum()
          pc_ratio = (
              round(total_put_vol / total_call_vol, 2)
              if total_call_vol > 0
              else 0
          )
          current_price = stock.history(period="1d")["Close"].iloc[-1]

          opt_results.append({
              "Hisse": ticker_symbol,
              "Fiyat ($)": round(current_price, 2),
              "İlk Vade": nearest_date,
              "Call Hacim": int(total_call_vol),
              "Put Hacim": int(total_put_vol),
              "P/C Oranı": pc_ratio,
          })
        except Exception as e:
          st.error(f"{ticker_symbol} Hata: {e}")

      df_options = pd.DataFrame(opt_results)
      st.dataframe(df_options, use_container_width=True)

with tab2:
  st.subheader("Teknik Sinyaller (SMA 20 / 50)")
  if st.button("Hisseleri Tara"):
    with st.spinner("Hisse verileri indiriliyor..."):
      results = []
      for ticker in stock_tickers:
        try:
          data = yf.download(ticker, period="3mo", interval="1d", progress=False)
          if data.empty:
            continue
          if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.get_level_values(0)

          close = data["Close"]
          sma20 = close.rolling(window=20).mean()
          sma50 = close.rolling(window=50).mean()

          current_price = float(close.iloc[-1])
          curr_sma20 = float(sma20.iloc[-1])
          curr_sma50 = float(sma50.iloc[-1])
          trend = (
              "Yükseliş (AL)" if current_price > curr_sma20 else "Düşüş / Yatay"
          )

          results.append({
              "Hisse": ticker,
              "Fiyat ($)": round(current_price, 2),
              "SMA 20": round(curr_sma20, 2),
              "SMA 50": round(curr_sma50, 2),
              "Durum": trend,
          })
        except Exception as e:
          pass

      df_results = pd.DataFrame(results)
      st.dataframe(df_results, use_container_width=True)
