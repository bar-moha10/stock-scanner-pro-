import streamlit as st
import yfinance as yf
import pandas as pd
import requests

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

def get_live_price(ticker):
    """שליפת מחיר אמת ישירות מ-Yahoo Query API למעקף באגים של התאמות"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        data = r.json()
        meta = data['chart']['result'][0]['meta']
        price = meta.get('regularMarketPrice') or meta.get('chartPreviousClose')
        return float(price)
    except Exception:
        return None

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

        for ticker in ALL_TICKERS:
            try:
                is_israeli = ticker.endswith(".TA")
                
                # 1. שליפת מחיר אמת נוכחי בלייב עוקף התאמות
                live_price = get_live_price(ticker)
                
                # 2. שליפת היסטוריה לצורך חישובי RSI ו-ATR
                t = yf.Ticker(ticker)
                df = t.history(period="3mo", auto_adjust=False)

                if live_price is None and not df.empty:
                    live_price = float(df['Close'].iloc[-1])

                if live_price and not df.empty:
                    if is_israeli:
                        # בורסת ת"א מדווחת באגורות ב-Yahoo (למשל 8615)
                        if live_price > 1000:
                            price_agorot = live_price
                            price_ils = live_price / 100.0
                        elif live_price > 100:
                            price_ils = live_price
                            price_agorot = live_price * 100.0
                        else:
                            price_ils = live_price / 100.0
                            price_agorot = live_price

                        display_price = f"₪{price_ils:.2f} ({int(price_agorot):,} אג')"
                        calc_price = price_ils
                        prefix = "₪"

                        scale = 100.0 if df['Close'].iloc[-1] > 100 else 1.0
                        history_series = df['Close'] / scale
                        high_series = df['High'] / scale
                        low_series = df['Low'] / scale
                    else:
                        display_price = f"${live_price:.2f}"
                        calc_price = live_price
                        prefix = "$"

                        history_series = df['Close']
                        high_series = df['High']
                        low_series = df['Low']

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
