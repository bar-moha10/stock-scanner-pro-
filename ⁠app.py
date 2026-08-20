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

    ISRAEL_TICKERS = ["TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA", "ICL.TA", "HARL.TA", "MZTF.TA"]
    USA_TICKERS = ["AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "AMD", "META", "NFLX", "INTC"]

    ALL_TICKERS = ISRAEL_TICKERS + USA_TICKERS

    with st.spinner("מביא מחירי אמת עדכניים מבורסות תל אביב וארה\"ב..."):
        results_israel = []
        results_usa = []
        histories = {}

        try:
            # הורדה מרוכזת אחת לכל הטיקרים כדי למנוע חסימות וטבלאות ריקות
            data = yf.download(ALL_TICKERS, period="3mo", auto_adjust=False, progress=False)

            for ticker in ALL_TICKERS:
                try:
                    # שליפת סדרת Close ללא התאמות
                    if len(ALL_TICKERS) > 1:
                        close_series = data['Close'][ticker].dropna()
                        high_series_raw = data['High'][ticker].dropna()
                        low_series_raw = data['Low'][ticker].dropna()
                    else:
                        close_series = data['Close'].dropna()
                        high_series_raw = data['High'].dropna()
                        low_series_raw = data['Low'].dropna()

                    if not close_series.empty and len(close_series) > 20:
                        last_price = float(close_series.iloc[-1])
                        is_israeli = ticker.endswith(".TA")

                        if is_israeli:
                            # בורסת ת"א מציגה אגורות ב-Yahoo (למשל 8615)
                            price_agorot = last_price
                            price_ils = last_price / 100.0

                            display_price = f"₪{price_ils:.2f} ({int(price_agorot):,} אג')"
                            calc_price = price_ils
                            prefix = "₪"

                            history_series = close_series / 100.0
                            high_series = high_series_raw / 100.0
                            low_series = low_series_raw / 100.0
                        else:
                            display_price = f"${last_price:.2f}"
                            calc_price = last_price
                            prefix = "$"

                            history_series = close_series
                            high_series = high_series_raw
                            low_series = low_series_raw

                        # חישוב RSI
                        delta = history_series.diff()
                        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                        rs = gain / loss
                        rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if not loss.empty and loss.iloc[-1] != 0 else 50.0

                        # חישוב ATR
                        high_low = high_series - low_series
                        atr = float(high_low.rolling(14).mean().iloc[-1]) if len(high_low) >= 14 else calc_price * 0.02

                        stop_loss = round(calc_price - (1.5 * atr), 2)
                        target = round(calc_price + (3.0 * atr), 2)

                        potential_gain_pct = round(((target - calc_price) / calc_price) * 100, 2)
                        risk_pct = round(((calc_price - stop_loss) / calc_price) * 100, 2)
                        ratio = round(potential_gain_pct / risk_pct, 2) if risk_pct > 0 else 0

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
        except Exception:
            st.error("שגיאה במשיכת הנתונים מ-Yahoo Finance.")

        # 🇮🇱 Top 5 ישראל
        st.subheader("🇮🇱 Top 5 הזדמנויות - הבורסה בתל אביב")
        df_il = pd.DataFrame()
        if results_israel:
            df_il = pd.DataFrame(results_israel).sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)
            st.dataframe(df_il, use_container_width=True)
        else:
            st.info("לא נמצאו נתונים עבור מניות ישראליות.")

        st.markdown("---")

        # 🇺🇸 Top 5 ארה"ב
        st.subheader("🇺🇸 Top 5 הזדמנויות - בורסת ארה\"ב")
        df_us = pd.DataFrame()
        if results_usa:
            df_us = pd.DataFrame(results_usa).sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)
            st.dataframe(df_us, use_container_width=True)
        else:
            st.info("לא נמצאו נתונים עבור מניות אמריקאיות.")

        st.markdown("---")

        # פירוט וגרפים
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
                        st.caption("גרף מחירים")
                        st.line_chart(histories[ticker_name])
