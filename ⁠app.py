import streamlit as st
import yfinance as yf
import numpy as np
import pandas as pd

st.set_page_config(page_title="Stock Scanner Pro", page_icon="📈", layout="wide")

# פונקציית התחברות
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
    st.title("📈 Stock Scanner Pro - Top 5 Opportunities")
    st.markdown("סורק ומדרג את **5 ההזדמנויות המובילות** מתוך רשימת המעקב לפי פוטנציאל תשואה/סיכון.")

    DEFAULT_TICKERS = ["AAPL", "AMD", "NVDA", "MSFT", "TSLA", "AMZN", "GOOGL", "META", "NFLX", "INTC"]

    def calculate_rsi(series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    if st.button("🚀 הרץ סריקה מתקדמת"):
        with st.spinner("סורק ומדרג מניות..."):
            try:
                # הורדת נתונים מרוכזת לכל המניות ביחד
                data = yf.download(DEFAULT_TICKERS, period="6mo", group_by="ticker", progress=False)
                results = []

                for ticker in DEFAULT_TICKERS:
                    try:
                        df = data[ticker].dropna()
                        if len(df) > 30:
                            close_prices = df['Close']
                            current_price = float(close_prices.iloc[-1])
                            
                            # חישוב RSI
                            rsi_series = calculate_rsi(close_prices)
                            rsi = float(rsi_series.iloc[-1])
                            
                            # חישוב ATR בסיסי
                            high_low = df['High'] - df['Low']
                            atr = float(high_low.rolling(14).mean().iloc[-1])
                            
                            stop_loss = round(current_price - (1.5 * atr), 2)
                            target = round(current_price + (3.0 * atr), 2)
                            
                            potential_gain_pct = round(((target - current_price) / current_price) * 100, 2)
                            risk_pct = round(((current_price - stop_loss) / current_price) * 100, 2)
                            ratio = round(potential_gain_pct / risk_pct, 2) if risk_pct > 0 else 0
                            
                            results.append({
                                "מניה": ticker,
                                "מחיר ($)": round(current_price, 2),
                                "RSI": round(rsi, 1),
                                "סטופ לוס ($)": stop_loss,
                                "מחיר יעד ($)": target,
                                "פוטנציאל רווח (%)": potential_gain_pct,
                                "סיכון (%)": risk_pct,
                                "יחס סיכוי/סיכון": ratio
                            })
                    except Exception:
                        continue

                if results:
                    res_df = pd.DataFrame(results)
                    res_df = res_df.sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)
                    
                    st.success("🎯 5 ההזדמנויות המובילות שנמצאו:")
                    st.dataframe(res_df.style.background_gradient(subset=['פוטנציאל רווח (%)'], cmap='Greens'), use_container_width=True)

                    st.markdown("---")
                    st.subheader("📊 פירוט מניות נבחרות")
                    for index, row in res_df.iterrows():
                        with st.expander(f"📌 {row['מניה']} - פוטנציאל רווח: {row['פוטנציאל רווח (%)']}%"):
                            st.write(f"**מחיר נוכחי:** ${row['מחיר ($)']}")
                            st.write(f"**מדד RSI:** {row['RSI']}")
                            st.write(f"**יעד רווח:** ${row['מחיר יעד ($)']}")
                            st.write(f"**קץ סיכון (Stop Loss):** ${row['סטופ לוס ($)']}")
                else:
                    st.error("לא ניתן היה לחשב את הנתונים, נסה שנית בעוד מספר רגעים.")
            except Exception as e:
                st.error("אירעה שגיאה בטעינת הנתונים מ-Yahoo Finance.")
