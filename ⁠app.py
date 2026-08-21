import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Stock Scanner Pro", layout="wide")

# --- פונקציות עזר ---
@st.cache_data(ttl=3600)
def get_all_tickers():
    # רשימה ממוקדת של מניות ישראליות מובילות
    israel = ["TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA", "ICL.TA", "MZTF.TA", "ESLT.TA"]
    # מניות ארה"ב מובילות
    us = ["AAPL", "NVDA", "TSLA", "AMZN", "MSFT", "AMD", "META", "PLTR", "ARM", "SMCI"]
    return israel + us

def analyze_ticker(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1mo", auto_adjust=False)
        if df.empty or len(df) < 20: return None
        
        price = float(df['Close'].iloc[-1])
        # סינון בסיסי למניעת NaN
        if pd.isna(price) or price <= 0: return None
        
        return {
            "מניה": ticker,
            "מחיר": price,
            "RSI": 50, # דוגמה לחישוב
            "ציון": 8 if price > 100 else 5 # דוגמה לציון
        }
    except:
        return None

# --- ממשק משתמש ---
st.title("📈 Stock Scanner Pro")

if st.button("🚀 הפעל סריקה"):
    tickers = get_all_tickers()
    results = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(analyze_ticker, t) for t in tickers]
        for f in as_completed(futures):
            res = f.result()
            if res: results.append(res)
    
    df = pd.DataFrame(results)
    
    # --- התיקון שביקשת: סינון NaN ---
    df = df.dropna() 
    
    st.session_state["df"] = df

if "df" in st.session_state:
    st.subheader("מניות שנמצאו:")
    st.dataframe(st.session_state["df"], use_container_width=True)
    
    # --- ניהול תיק וירטואלי ---
    if "portfolio" not in st.session_state:
        st.session_state["portfolio"] = []
        
    with st.form("add_trade"):
        t = st.selectbox("בחר מניה", st.session_state["df"]["מניה"].tolist())
        qty = st.number_input("כמות", value=1)
        if st.form_submit_button("הוסף לתיק"):
            st.session_state["portfolio"].append({"ticker": t, "qty": qty})
            st.success("נוסף!")

    if st.session_state["portfolio"]:
        st.subheader("💼 התיק שלך:")
        st.write(pd.DataFrame(st.session_state["portfolio"]))
