
import streamlit as st
import requests
import pandas as pd
import math
from datetime import datetime

st.set_page_config(layout="wide")
st.title("Simple Put-Call Parity Arbitrage Monitor")

st.markdown("Data Source: NSE Option Chain (Unofficial Public API)")
st.markdown("Note: Dividend impact is NOT adjusted. Check upcoming dividends before execution.")

# ---- User Inputs ----
symbol = st.selectbox("Select Stock", ["RELIANCE", "SBIN", "INFY"])
risk_free_rate = st.number_input("Risk Free Rate (%)", value=6.5) / 100
borrow_spread = st.number_input("Additional Borrowing Spread (%)", value=1.0) / 100
expiry_days = st.number_input("Days to Expiry", value=30)

T = expiry_days / 365
effective_rate = risk_free_rate + borrow_spread

# ---- Fetch Option Chain ----
def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-equities?symbol={symbol}"
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br"
    }
    session = requests.Session()
    session.get("https://www.nseindia.com", headers=headers)
    response = session.get(url, headers=headers)
    data = response.json()
    return data

try:
    data = fetch_option_chain(symbol)
    records = data["records"]["data"]
    spot_price = data["records"]["underlyingValue"]

    results = []

    for item in records:
        if "CE" in item and "PE" in item:
            strike = item["strikePrice"]
            call_price = item["CE"]["lastPrice"]
            put_price = item["PE"]["lastPrice"]

            lhs = call_price - put_price
            rhs = spot_price - strike * math.exp(-effective_rate * T)

            arbitrage = lhs - rhs

            results.append({
                "Strike": strike,
                "Call Price": call_price,
                "Put Price": put_price,
                "Parity Difference": round(arbitrage, 4)
            })

    df = pd.DataFrame(results)
    df["Abs Profit"] = df["Parity Difference"].abs()
    df = df.sort_values(by="Abs Profit", ascending=False)

    st.subheader(f"Spot Price: {spot_price}")
    st.dataframe(df.head(15), use_container_width=True)

    st.markdown(f"Last Refreshed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

except Exception:
    st.error("Error fetching data from NSE. Try again later.")

st.markdown("---")
st.markdown("### Execution Logic (Simplified)")
st.markdown("If (Call - Put) > (Spot - PV(Strike)) : Sell Call, Buy Put, Buy Spot")
st.markdown("If (Call - Put) < (Spot - PV(Strike)) : Buy Call, Sell Put, Short Spot")
st.markdown("PV(Strike) = Strike * e^(-(risk-free + borrowing spread) * T)")
