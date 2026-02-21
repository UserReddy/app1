import streamlit as st
import requests
import pandas as pd
import math
import time
import yfinance as yf
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Multi-Arbitrage Monitor")

# ================= GLOBAL SETTINGS ================= #

refresh_seconds = st.slider("Auto Refresh (seconds)", 5, 60, 15)

# ================= ARBITRAGE TYPE ================= #

arbitrage_type = st.selectbox(
    "Select Arbitrage Type",
    ["Put-Call Parity", "Cash & Carry", "Interest Rate Parity"]
)

risk_free_rate = st.number_input("Risk Free Rate (%)", value=6.5) / 100
borrow_spread = st.number_input("Borrow Spread (%)", value=1.0) / 100
expiry_days = st.number_input("Days to Expiry", value=30)

T = expiry_days / 365
effective_rate = risk_free_rate + borrow_spread

data_source_used = "Unknown"

# ================= COMMON SPOT FETCH ================= #

def fetch_spot(symbol):
    try:
        mapping = {
            "NIFTY": "^NSEI",
            "BANKNIFTY": "^NSEBANK",
            "RELIANCE": "RELIANCE.NS",
            "SBIN": "SBIN.NS",
            "INFY": "INFY.NS"
        }
        ticker = yf.Ticker(mapping[symbol])
        return ticker.history(period="1d")["Close"].iloc[-1]
    except:
        return None

# ================= PUT CALL PARITY ================= #

if arbitrage_type == "Put-Call Parity":

    instrument = st.selectbox(
        "Select Stock / Index",
        ["RELIANCE", "SBIN", "INFY", "NIFTY", "BANKNIFTY"]
    )

    def fetch_nse_option_chain(symbol):
        try:
            if symbol in ["NIFTY", "BANKNIFTY"]:
                url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
            else:
                url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"

            headers = {"User-Agent": "Mozilla/5.0"}
            session = requests.Session()
            session.headers.update(headers)
            session.get("https://www.nseindia.com")
            response = session.get(url, timeout=10)

            if response.status_code == 200:
                return response.json()
            return None
        except:
            return None

    nse_data = fetch_nse_option_chain(instrument)

    if nse_data:
        data_source_used = "NSE Option Chain"
        records = nse_data["records"]["data"]
        spot_price = nse_data["records"]["underlyingValue"]
    else:
        data_source_used = "Yahoo Finance Spot"
        records = []
        spot_price = fetch_spot(instrument)

    results = []

    if spot_price:
        for item in records:
            if "CE" in item and "PE" in item:
                strike = item["strikePrice"]
                call_price = item["CE"].get("lastPrice", 0)
                put_price = item["PE"].get("lastPrice", 0)

                lhs = call_price - put_price
                rhs = spot_price - strike * math.exp(-effective_rate * T)
                diff = lhs - rhs

                direction = (
                    "Sell Call | Buy Put | Buy Spot"
                    if diff > 0
                    else "Buy Call | Sell Put | Short Spot"
                )

                results.append({
                    "Strike": strike,
                    "Call": call_price,
                    "Put": put_price,
                    "Parity Diff": round(diff, 4),
                    "Action": direction
                })

        if results:
            df = pd.DataFrame(results)
            df["Abs Dev"] = df["Parity Diff"].abs()
            df = df.sort_values(by="Abs Dev", ascending=False)

            st.subheader(f"Spot Price: {round(spot_price,2)}")
            st.dataframe(df.head(20), use_container_width=True)

# ================= CASH & CARRY ================= #

elif arbitrage_type == "Cash & Carry":

    instrument = st.selectbox(
        "Select Stock / Index",
        ["RELIANCE", "SBIN", "INFY", "NIFTY", "BANKNIFTY"]
    )

    spot_price = fetch_spot(instrument)
    data_source_used = "Yahoo Finance Spot (Futures Proxy)"

    if spot_price:
        futures_price = spot_price * 1.01  # simple proxy
        theoretical_future = spot_price * math.exp(effective_rate * T)
        diff = futures_price - theoretical_future

        st.write(f"Spot: {round(spot_price,2)}")
        st.write(f"Futures (Proxy): {round(futures_price,2)}")
        st.write(f"Theoretical Futures: {round(theoretical_future,2)}")
        st.write(f"Deviation: {round(diff,4)}")

        if diff > 0:
            st.success("Buy Spot | Sell Futures")
        else:
            st.success("Sell Spot | Buy Futures")

# ================= INTEREST RATE PARITY ================= #

elif arbitrage_type == "Interest Rate Parity":

    currency_pair = st.selectbox(
        "Select Currency Pair",
        ["USDINR", "EURINR", "GBPUSD"]
    )

    data_source_used = "Model-Based (Proxy Rates)"

    spot_rate = 83.0
    domestic_rate = risk_free_rate
    foreign_rate = 0.05

    forward_market = spot_rate * 1.01
    forward_theoretical = spot_rate * math.exp((domestic_rate - foreign_rate) * T)
    diff = forward_market - forward_theoretical

    st.write(f"Spot Rate: {spot_rate}")
    st.write(f"Market Forward: {round(forward_market,4)}")
    st.write(f"Theoretical Forward: {round(forward_theoretical,4)}")
    st.write(f"Deviation: {round(diff,4)}")

    if diff > 0:
        st.success("Borrow Foreign | Invest Domestic | Sell Forward")
    else:
        st.success("Borrow Domestic | Invest Foreign | Buy Forward")

# ================= FOOTER ================= #

st.markdown(f"### Data Source Used: **{data_source_used}**")
st.success(f"Last Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

time.sleep(refresh_seconds)
st.rerun()
