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
    st.title("📈 Stock Scanner Pro")
    st.markdown("סורק ומדרג בזמן אמת את **5 ההזדמנויות המובילות בישראל** ו-**5 המובילות בארה\"ב**.")

    DEFAULT_TICKERS = [
        # מניות ארה"ב
        "AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "AMD", "META", "NFLX", "INTC",
        # מניות ישראל
        "TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA", "ICL.TA", "HARL.TA", "MZTF.TA"
    ]

    with st.spinner("סורק ומנתח את הנתונים בלייב..."):
        results_israel = []
        results_usa = []
        histories = {}

        for ticker in DEFAULT_TICKERS:
            try:
                t = yf.Ticker(ticker)
                df = t.history(period="3mo")

                if not df.empty and len(df) > 20:
                    is_israeli = ticker.endswith(".TA")
                    raw_last_price = float(df['Close'].iloc[-1])

                    if is_israeli:
                        # המרה קבועה מול נתוני אגורות/שקלים
                        if raw_last_price > 100:
                            price_ils = raw_last_price / 100.0
                            price_agorot = raw_last_price
                        else:
                            price_ils = raw_last_price
                            price_agorot = raw_last_price * 100.0

                        display_price = f"₪{round(price_ils, 2)} ({int(price_agorot)} אג')"
                        history_series = df['Close'] / 100.0 if raw_last_price > 100 else df['Close']
                        calc_price = price_ils
                    else:
                        display_price = f"${round(raw_last_price, 2)}"
                        history_series = df['Close']
                        calc_price = raw_last_price

                    # חישוב RSI
                    delta = history_series.diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss
                    rsi = float((100 - (100 / (1 + rs))).iloc[-1])

                    # חישוב ATR ותנודתיות
                    high_low = (df['High'] - df['Low']) / (100.0 if is_israeli and raw_last_price > 100 else 1.0)
                    atr = float(high_low.rolling(14).mean().iloc[-1])

                    stop_loss = round(calc_price - (1.5 * atr), 2)
                    target = round(calc_price + (3.0 * atr), 2)

                    potential_gain_pct = round(((target - calc_price) / calc_price) * 100, 2)
                    risk_pct = round(((calc_price - stop_loss) / calc_price) * 100, 2)
                    ratio = round(potential_gain_pct / risk_pct, 2) if risk_pct > 0 else 0

                    prefix = "₪" if is_israeli else "$"

                    item = {
                        "מניה": ticker,
                        "מחיר עדכני": display_price,
                        "RSI": round(rsi, 1),
                        "סטופ לוס": f"{prefix}{stop_loss}",
                        "מחיר יעד": f"{prefix}{target}",
                        "פוטנציאל רווח (%)": potential_gain_pct,
                        "סיכון (%)": risk_pct,
                        "יחס סיכוי/סיכון": ratio
                    }

                    if is_israeli:
                        results_israel.append(item)
                    else:
                        results_usa.append(item)

                    histories[ticker] = history_series
            except Exception:
                continue

        # 🇮🇱 top 5 ישראל
        st.subheader("🇮🇱 Top 5 הזדמנויות - הבורסה בתל אביב")
        df_il = pd.DataFrame()
        if results_israel:
            df_il = pd.DataFrame(results_israel).sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)
            st.dataframe(df_il, use_container_width=True)
        else:
            st.info("לא נמצאו נתונים עבור מניות ישראליות.")

        st.markdown("---")

        # 🇺🇸 top 5 ארה"ב
        st.subheader("🇺🇸 Top 5 הזדמנויות - בורסת ארה\"ב")
        df_us = pd.DataFrame()
        if results_usa:
            df_us = pd.DataFrame(results_usa).sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)
            st.dataframe(df_us, use_container_width=True)
        else:
            st.info("לא נמצאו נתונים עבור מניות אמריקאיות.")

        st.markdown("---")

        # פירוט וגרפים לכל 10 המניות הנבחרות
        st.subheader("📊 פירוט וגרפים - 10 המניות הנבחרות")
        all_top = pd.concat([df_il, df_us], ignore_index=True)

        if not all_top.empty:
            for index, row in all_top.iterrows():
                ticker_name = row['מניה']
                with st.expander(f"📌 {ticker_name} - פוטנציאל רווח: {row['פוטנציאל רווח (%)']}%"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.write(f"**מחיר עדכני:** {row['מחיר עדכני']}")
                        st.write(f"**מדד RSI:** {row['RSI']}")
                        st.write(f"**יעד רווח:** {row['מחיר יעד']}")
                        st.write(f"**קץ סיכון (Stop Loss):** {row['סטופ לוס']}")
                        st.write(f"**יחס סיכוי/סיכון:** {row['יחס סיכוי/סיכון']}")
                    with col2:
                        st.caption("גרף מחירים - 3 חודשים אחרונים")
                        st.line_chart(histories[ticker_name])
