import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="Stock Scanner Pro", page_icon="📈", layout="wide")

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
    st.markdown("סורק ומדרג את **5 ההזדמנויות המובילות** מתוך רשימת מעקב גלובלית וישראלית.")

    # רשימה משולבת: ארה"ב + מניות מובילות מתל אביב (.TA)
    DEFAULT_TICKERS = [
        "AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "AMD",
        "TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA"
    ]

    if st.button("🚀 הרץ סריקה מתקדמת"):
        with st.spinner("סורק ומדרג מניות..."):
            results = []
            histories = {}

            for ticker in DEFAULT_TICKERS:
                try:
                    t = yf.Ticker(ticker)
                    df = t.history(period="3mo")
                    if len(df) > 20:
                        close_prices = df['Close']
                        current_price = float(close_prices.iloc[-1])

                        # חישוב RSI
                        delta = close_prices.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = float((100 - (100 / (1 + rs))).iloc[-1])

                        # חישוב תנודתיות ATR
                        high_low = df['High'] - df['Low']
                        atr = float(high_low.rolling(14).mean().iloc[-1])

                        stop_loss = round(current_price - (1.5 * atr), 2)
                        target = round(current_price + (3.0 * atr), 2)

                        potential_gain_pct = round(((target - current_price) / current_price) * 100, 2)
                        risk_pct = round(((current_price - stop_loss) / current_price) * 100, 2)
                        ratio = round(potential_gain_pct / risk_pct, 2) if risk_pct > 0 else 0

                        results.append({
                            "מניה": ticker,
                            "מחיר": round(current_price, 2),
                            "RSI": round(rsi, 1),
                            "סטופ לוס": stop_loss,
                            "מחיר יעד": target,
                            "פוטנציאל רווח (%)": potential_gain_pct,
                            "סיכון (%)": risk_pct,
                            "יחס סיכוי/סיכון": ratio
                        })
                        histories[ticker] = close_prices
                except Exception:
                    continue

            if results:
                res_df = pd.DataFrame(results)
                res_df = res_df.sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)

                st.success("🎯 5 ההזדמנויות המובילות שנמצאו:")
                st.dataframe(res_df, use_container_width=True)

                st.markdown("---")
                st.subheader("📊 פירוט וגרפים לכל מניה")
                for index, row in res_df.iterrows():
                    ticker_name = row['מניה']
                    with st.expander(f"📌 {ticker_name} - פוטנציאל רווח: {row['פוטנציאל רווח (%)']}%"):
                        col1, col2 = st.columns([1, 2])
                        with col1:
                            st.write(f"**מחיר נוכחי:** {row['מחיר']}")
                            st.write(f"**מדד RSI:** {row['RSI']}")
                            st.write(f"**יעד רווח:** {row['מחיר יעד']}")
                            st.write(f"**קץ סיכון (Stop Loss):** {row['סטופ לוס']}")
                            st.write(f"**יחס סיכוי/סיכון:** {row['יחס סיכוי/סיכון']}")
                        with col2:
                            st.caption("גרף מחירים - 3 חודשים אחרונים")
                            st.line_chart(histories[ticker_name])
            else:
                st.error("לא ניתן היה להוציא נתונים כעת, נסה שוב בעוד דקה.")
