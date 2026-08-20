import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="Stock Scanner Pro", page_icon="📈", layout="wide")

# מילון תרגום משמות בעברית לסימולים של Yahoo Finance
HEBREW_TICKERS = {
    "בזן": "ORL.TA",
    "בז"ן": "ORL.TA",
    "בתי זיקוק": "ORL.TA",
    "דלק": "DLEKG.TA",
    "קבוצת דלק": "DLEKG.TA",
    "בזק": "BEZQ.TA",
    "טבע": "TEVA.TA",
    "לאומי": "LUMI.TA",
    "פועלים": "POLI.TA",
    "נייס": "NICE.TA",
    "כיל": "ICL.TA",
    "אייסיאל": "ICL.TA",
    "הראל": "HARL.TA",
    "מזרחי": "MZTF.TA",
    "מזרחי טפחות": "MZTF.TA",
    "ליברה": "LBRT.TA",
    "אלביט": "ESLT.TA"
}

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
    """שליפת מחיר אמת ישירות מ-Yahoo Query API"""
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

def analyze_ticker(user_input):
    """פונקציה שמבצעת ניתוח טכני מלא למניה בודדת כולל המרה מעברית"""
    clean_input = user_input.strip()
    
    # בדיקה אם המשתמש הקליד שם בעברית מהמילון
    ticker = HEBREW_TICKERS.get(clean_input, clean_input).upper()
    
    is_israeli = ticker.endswith(".TA")

    raw_live_price = get_live_price(ticker)
    t = yf.Ticker(ticker)
    df = t.history(period="3mo", auto_adjust=False)

    if raw_live_price is None and not df.empty:
        raw_live_price = float(df['Close'].iloc[-1])

    if not raw_live_price or df.empty:
        return None, f"לא נמצאו נתונים עבור '{user_input}'. ודא שהטיקר נכון (למשל ORL.TA, AAPL או 'בזן')."

    if is_israeli:
        if raw_live_price > 1000:
            price_ils = raw_live_price / 100.0
            price_agorot = raw_live_price
        elif raw_live_price > 100:
            price_ils = raw_live_price
            price_agorot = raw_live_price * 100.0
        else:
            price_ils = raw_live_price / 100.0
            price_agorot = raw_live_price

        display_price = f"₪{price_ils:.2f} ({int(price_agorot):,} אג')"
        calc_price = price_ils
        prefix = "₪"

        hist_last = df['Close'].iloc[-1]
        divider = 100.0 if hist_last > 100 else 1.0

        history_series = df['Close'] / divider
        high_series = df['High'] / divider
        low_series = df['Low'] / divider
    else:
        display_price = f"${raw_live_price:.2f}"
        calc_price = raw_live_price
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

    if pd.isna(atr) or atr <= 0 or atr > (calc_price * 0.2):
        atr = calc_price * 0.02

    stop_loss = round(calc_price - (1.5 * atr), 2)
    target = round(calc_price + (3.0 * atr), 2)

    potential_gain_pct = round(((target - calc_price) / calc_price) * 100, 2)
    risk_pct = round(((calc_price - stop_loss) / calc_price) * 100, 2)
    ratio = round(potential_gain_pct / risk_pct, 2) if risk_pct > 0 else 0

    analysis = {
        "מניה": ticker,
        "מחיר עדכני": display_price,
        "RSI": round(rsi, 1),
        "סטופ לוס": f"{prefix}{stop_loss}",
        "מחיר יעד": f"{prefix}{target}",
        "פוטנציאל רווח (%)": potential_gain_pct,
        "סיכון (%)": risk_pct,
        "יחס סיכוי/סיכון": ratio,
        "history": history_series
    }

    return analysis, None

if check_password():
    st.title("📈 Stock Scanner Pro")
    st.markdown("סורק ומדרג בזמן אמת מניות בארץ ובארה\"ב, ומאפשר ניתוח מותאם אישית.")

    # 🔍 אזור חיפוש מניה אישית
    st.subheader("🔍 חיפוש וניתוח מניה ספציפית")
    col_search1, col_search2 = st.columns([3, 1])
    
    with col_search1:
        searched_ticker = st.text_input("הכנס שם מניה (למשל: בזן, דלק, MSFT, או DLEKG.TA):", value="")
    
    with col_search2:
        st.write("")
        st.write("")
        search_btn = st.button("פתח ניתוח 📊")

    if searched_ticker and search_btn:
        with st.spinner(f"מנתח את {searched_ticker}..."):
            res, err = analyze_ticker(searched_ticker)
            if err:
                st.error(err)
            else:
                st.success(f"תוצאות ניתוח עבור {res['מניה']}:")
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("מחיר עדכני", res['מחיר עדכני'])
                    st.write(f"**מדד RSI:** {res['RSI']}")
                    st.write(f"**מחיר יעד (Take Profit):** {res['מחיר יעד']}")
                    st.write(f"**קץ סיכון (Stop Loss):** {res['סטופ לוס']}")
                    st.write(f"**פוטנציאל רווח:** {res['פוטנציאל רווח (%)']}%")
                    st.write(f"**יחס סיכוי/סיכון:** {res['יחס סיכוי/סיכון']}")
                with c2:
                    st.caption("גרף מחירים מנורמל")
                    st.line_chart(res['history'])

    st.markdown("---")

    # 🇮🇱🇺🇸 סריקה כללית (Top 5)
    ISRAEL_TICKERS = ["TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA", "ICL.TA", "HARL.TA", "MZTF.TA"]
    USA_TICKERS = ["AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "AMD", "META", "NFLX", "INTC"]
    ALL_TICKERS = ISRAEL_TICKERS + USA_TICKERS

    with st.spinner("מביא מחירי אמת ומעדכן את ה-Top 5..."):
        results_israel = []
        results_usa = []
        histories = {}

        for ticker in ALL_TICKERS:
            res, err = analyze_ticker(ticker)
            if res:
                is_israeli = ticker.endswith(".TA")
                item = {
                    "מניה": res["מניה"],
                    "מחיר עדכני": res["מחיר עדכני"],
                    "RSI": res["RSI"],
                    "סטופ לוס": res["סטופ לוס"],
                    "מחיר יעד": res["מחיר יעד"],
                    "פוטנציאל רווח (%)": res["פוטנציאל רווח (%)"],
                    "סיכון (%)": res["סיכון (%)"],
                    "יחס סיכוי/סיכון": res["יחס סיכוי/סיכון"]
                }
                if is_israeli:
                    results_israel.append(item)
                else:
                    results_usa.append(item)
                histories[ticker] = res["history"]

        # 🇮🇱 Top 5 ישראל
        st.subheader("🇮🇱 Top 5 הזדמנויות - הבורסה בתל אביב")
        df_il = pd.DataFrame()
        if results_israel:
            df_il = pd.DataFrame(results_israel).sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)
            st.dataframe(df_il, use_container_width=True)

        st.markdown("---")

        # 🇺🇸 Top 5 ארה"ב
        st.subheader("🇺🇸 Top 5 הזדמנויות - בורסת ארה\"ב")
        df_us = pd.DataFrame()
        if results_usa:
            df_us = pd.DataFrame(results_usa).sort_values(by="פוטנציאל רווח (%)", ascending=False).head(5)
            st.dataframe(df_us, use_container_width=True)

        st.markdown("---")

        # פירוט וגרפים ל-Top 10
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
                        st.caption("גרף מחירים בשקלים / דולרים")
                        st.line_chart(histories[ticker_name])
