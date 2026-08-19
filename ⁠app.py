import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

st.set_page_config(page_title="Stock Scanner Pro", page_icon="📈", layout="centered")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 התחברות למערכת הסורק")
        username = st.text_input("שם משתמש")
        password = st.text_input("סיסמה", type="password")
        
        if st.button("התחבר"):
            if username == "admin" and password == "1234":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")
        return False
    return True

if check_password():
    st.title("📈 Stock Scanner Pro")
    st.write("סורק הזדמנויות מסחר מבוסס RSI ו-ATR")
    
    if st.sidebar.button("התנתק"):
        st.session_state["authenticated"] = False
        st.rerun()

    market_list = ["ZIM", "NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "AMD", "PYPL"]

    if st.button("🚀 הרץ סריקה עכשיו", type="primary"):
        with st.spinner("סורק את השוק... מיד מציג תוצאות"):
            results = []
            for symbol in market_list:
                try:
                    data = yf.Ticker(symbol).history(period="1mo")
                    if len(data) < 14:
                        continue
                    price = round(data["Close"].iloc[-1], 2)
                    
                    delta = data["Close"].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                    rsi = round(100 - (100 / (1 + (gain.iloc[-1] / loss.iloc[-1]))), 1)
                    
                    high_low = data["High"] - data["Low"]
                    high_close = np.abs(data["High"] - data["Close"].shift())
                    low_close = np.abs(data["Low"] - data["Close"].shift())
                    ranges = np.maximum(high_low, np.maximum(high_close, low_close))
                    atr = round(ranges.rolling(14).mean().iloc[-1], 2)
                    
                    score = round(100 - rsi, 1)
                    if rsi < 50:
                        results.append({
                            "מנייה": symbol,
                            "מחיר ($)": price,
                            "RSI": rsi,
                            "Stop Loss ($)": round(price - (1.5 * atr), 2),
                            "Target ($)": round(price + (3.0 * atr), 2),
                            "ציון": score
                        })
                except Exception:
                    pass

            if results:
                df = pd.DataFrame(results).sort_values(by="ציון", ascending=False).drop(columns=["ציון"])
                st.success("מצאנו את ההזדמנויות הבאות:")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("לא נמצאו מניות בטווח RSI נמוך כרגע.")
