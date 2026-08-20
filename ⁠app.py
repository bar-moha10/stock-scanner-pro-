import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Scanner Pro", page_icon="📈", layout="wide")

HEBREW_TICKERS = {
    "בזן": "ORL.TA",
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

SEARCH_OPTIONS = [
    "",
    "בזק",
    "בזן / בתי זיקוק",
    "דלק / קבוצת דלק",
    "טבע",
    "לאומי",
    "פועלים",
    "נייס",
    "כיל / אייסיאל",
    "הראל",
    "מזרחי טפחות",
    "ליברה",
    "אלביט",
    "AAPL - Apple",
    "NVDA - Nvidia",
    "TSLA - Tesla",
    "AMZN - Amazon",
    "GOOGL - Google",
    "MSFT - Microsoft",
    "AMD - AMD",
    "META - Meta",
    "NFLX - Netflix",
    "INTC - Intel"
]

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

def detect_candlestick_pattern(df):
    if len(df) < 2:
        return "אין מספיק נתונים", "neutral", "אין מספיק נתוני מסחר כדי לזהות תבנית."

    curr = df.iloc[-1]
    prev = df.iloc[-2]

    c_open, c_close, c_high, c_low = curr['Open'], curr['Close'], curr['High'], curr['Low']
    p_open, p_close = prev['Open'], prev['Close']

    body = abs(c_close - c_open)
    lower_shadow = min(c_open, c_close) - c_low
    upper_shadow = c_high - max(c_open, c_close)

    # 1. פטיש (Hammer)
    if lower_shadow > (2 * body) and upper_shadow < (body * 0.5) and body > 0:
        return (
            "🔨 נר פטיש (איתות עליות)",
            "bullish",
            "נר פטיש מציג צל ישר וארוך למטה. המשמעות: המוכרים ניסו להוריד את המחיר חזק, אך הקונים השתלטו מחדש ודחפו אותו חזרה למעלה. איתות שורי חזק להיפוך עליות."
        )

    # 2. בליעה שורית (Bullish Engulfing)
    if p_close < p_open and c_close > c_open and c_open <= p_close and c_close >= p_open:
        return (
            "🟢 בליעה שורית (איתות עליות חזק)",
            "bullish",
            "הגוף של הנר הירוק הנוכחי 'בולע' לחלוטין את הנר האדום שלפניו. המשמעות: הקונים נכנסו בעוצמה רבה ושלטו לחלוטין במסחר."
        )

    # 3. בליעה דובית (Bearish Engulfing)
    if p_close > p_open and c_close < c_open and c_open >= p_close and c_close <= p_open:
        return (
            "🔴 בליעה דובית (איתות ירידות)",
            "bearish",
            "הגוף של הנר האדום הנוכחי בולע לחלוטין את הנר הירוק שלפניו. המשמעות: לחץ מכירות כבד והשתלטות של המוכרים בשוק."
        )

    # 4. נר ירוק / אדום רגיל
    if c_close > c_open:
        return (
            "🕯️ נר ירוק רגיל",
            "neutral",
            "מחיר הסגירה גבוה ממחיר הפתיחה. הקונים היו חזקים יותר מהמוכרים ביום הזה, והמניה סיימה בעלייה ללא תבנית היפוך מיוחדת."
        )
    else:
        return (
            "🕯️ נר אדום רגיל",
            "neutral",
            "מחיר הסגירה נמוך ממחיר הפתיחה. המוכרים שלטו ביום המסחר והמניה סיימה בירידה ללא תבנית היפוך מיוחדת."
        )

def evaluate_trade_recommendation(pattern_type, rsi, ratio):
    score = 0

    if pattern_type == "bullish":
        score += 3
    elif pattern_type == "bearish":
        score -= 3

    if rsi < 35:
        score += 2
    elif 35 <= rsi <= 65:
        score += 1
    elif rsi > 70:
        score -= 2

    if ratio >= 2.0:
        score += 2
    elif ratio < 1.2:
        score -= 2

    if score >= 4:
        return "✅ שווה כניסה (איתות שורי חזק)", 3, "המניה מציגה שילוב מצוין של תבנית נרות, מומנטום חיובי ויחס סיכוי/סיכון משתלם."
    elif score >= 1:
        return "🟡 להמתין / כניסה בזהירות", 2, "יש סימנים חיוביים, אך מומלץ להמתין לאישור נוסף או להגדיר סטופ לוס הדוק."
    else:
        return "❌ לא מומלץ כרגע", 1, "הנתונים מעידים על לחץ מוכרים, RSI גבוה או יחס סיכוי/סיכון לא אטרקטיבי."

def analyze_ticker(user_input, period="6mo"):
    clean_input = user_input.split("-")[0].split("/")[0].strip().replace('"', '').replace("'", "")
    ticker = HEBREW_TICKERS.get(clean_input, clean_input).upper()
    is_israeli = ticker.endswith(".TA")

    raw_live_price = get_live_price(ticker)
    t = yf.Ticker(ticker)
    df = t.history(period=period, auto_adjust=False)

    if raw_live_price is None and not df.empty:
        raw_live_price = float(df['Close'].iloc[-1])

    if not raw_live_price or df.empty:
        return None, f"לא נמצאו נתונים עבור '{user_input}'."

    if is_israeli:
        price_ils = raw_live_price / 100.0 if raw_live_price > 50 else raw_live_price
        price_agorot = price_ils * 100.0

        display_price = f"₪{price_ils:.2f} ({int(price_agorot):,} אג')"
        calc_price = price_ils
        prefix = "₪"

        history_df = df[['Open', 'High', 'Low', 'Close']].copy()
        if history_df['Close'].iloc[-1] > 50:
            history_df = history_df / 100.0
    else:
        display_price = f"${raw_live_price:.2f}"
        calc_price = raw_live_price
        prefix = "$"
        history_df = df[['Open', 'High', 'Low', 'Close']].copy()

    candle_pattern, pattern_type, candle_desc = detect_candlestick_pattern(history_df)

    delta = history_df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if not loss.empty and loss.iloc[-1] != 0 else 50.0

    high_low = history_df['High'] - history_df['Low']
    atr = float(high_low.rolling(14).mean().iloc[-1]) if len(high_low) >= 14 else calc_price * 0.02

    if pd.isna(atr) or atr <= 0 or atr > (calc_price * 0.2):
        atr = calc_price * 0.02

    stop_loss = round(calc_price - (1.5 * atr), 2)
    target = round(calc_price + (3.0 * atr), 2)

    potential_gain_pct = round(((target - calc_price) / calc_price) * 100, 2)
    risk_pct = round(((calc_price - stop_loss) / calc_price) * 100, 2)
    ratio = round(potential_gain_pct / risk_pct, 2) if risk_pct > 0 else 0

    rec_title, rec_rank, rec_desc = evaluate_trade_recommendation(pattern_type, rsi, ratio)

    analysis = {
        "מניה": ticker,
        "מחיר עדכני": display_price,
        "RSI": round(rsi, 1),
        "תבנית נר": candle_pattern,
        "הסבר נר": candle_desc,
        "המלצה": rec_title,
        "דירוג המלצה": rec_rank,
        "הסבר המלצה": rec_desc,
        "סטופ לוס": f"{prefix}{stop_loss}",
        "מחיר יעד": f"{prefix}{target}",
        "פוטנציאל רווח (%)": potential_gain_pct,
        "סיכון (%)": risk_pct,
        "יחס סיכוי/סיכון": ratio,
        "df": history_df,
        "prefix": prefix
    }

    return analysis, None

def plot_interactive_chart(df, ticker, prefix):
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        mode='lines', 
        name='מחיר',
        line=dict(color='#0066cc', width=2.5),
        hovertemplate='%{x|%d/%m/%Y}<br>מחיר: ' + prefix + '%{y:.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=5, r=5, t=10, b=10),
        height=300,
        dragmode=False,
        xaxis=dict(
            showgrid=True, 
            zeroline=False, 
            fixedrange=True,
            showspikes=True,
            spikethickness=1.5,
            spikecolor="#e63946",
            spikemode="across"
        ),
        yaxis=dict(
            showgrid=True, 
            zeroline=False, 
            fixedrange=True,
            showspikes=True,
            spikethickness=1.5,
            spikecolor="#e63946",
            spikemode="across"
        )
    )
    return fig

if check_password():
    st.title("📈 Stock Scanner Pro")
    
    st.sidebar.header("⚙️ הגדרות תצוגה")
    selected_period = st.sidebar.select_slider(
        "טווח זמן לגרפים:",
        options=["1mo", "3mo", "6mo", "1y"],
        value="6mo",
        format_func=lambda x: {"1mo": "חודש", "3mo": "3 חודשים", "6mo": "חצי שנה", "1y": "שנה"}[x]
    )

    st.subheader("🔍 חיפוש וניתוח מניה ספציפית")
    col_search1, col_search2 = st.columns([3, 1])
    
    with col_search1:
        searched_ticker = st.selectbox(
            "הקלד שם מניה או סימול (למשל: ב...):",
            options=SEARCH_OPTIONS,
            index=0
        )
    
    with col_search2:
        st.write("")
        st.write("")
        search_btn = st.button("פתח ניתוח 📊")

    if searched_ticker and search_btn:
        with st.spinner(f"מנתח את {searched_ticker}..."):
            res, err = analyze_ticker(searched_ticker, period=selected_period)
            if err:
                st.error(err)
            else:
                st.success(f"תוצאות ניתוח עבור {res['מניה']}:")
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.metric("מחיר עדכני", res['מחיר עדכני'])
                    
                    c_rec, c_rec_info = st.columns([4, 1])
                    c_rec.markdown(f"**כדאיות כניסה:** {res['המלצה']}")
                    with c_rec_info.popover("ℹ️"):
                        st.write(res['הסבר המלצה'])

                    c_candle, c_candle_info = st.columns([4, 1])
                    c_candle.markdown(f"**תבנית נר:** {res['תבנית נר']}")
                    with c_candle_info.popover("ℹ️"):
                        st.write(res['הסבר נר'])

                    c_rsi, c_rsi_info = st.columns([4, 1])
                    c_rsi.markdown(f"**מדד RSI:** {res['RSI']}")
                    with c_rsi_info.popover("ℹ️"):
                        st.write("מדד עוצמה יחסית (1-100). מראה מומנטום קונים מול מוכרים.")

                    c_tp, c_tp_info = st.columns([4, 1])
                    c_tp.markdown(f"**מחיר יעד:** {res['מחיר יעד']}")
                    with c_tp_info.popover("ℹ️"):
                        st.write("מחיר יציאה מומלץ למכירה ולקיחת רווחים.")

                    c_sl, c_sl_info = st.columns([4, 1])
                    c_sl.markdown(f"**קץ סיכון:** {res['סטופ לוס']}")
                    with c_sl_info.popover("ℹ️"):
                        st.write("מחיר הגנה לחיתוך הפסד בזמן.")

                    c_rr, c_rr_info = st.columns([4, 1])
                    c_rr.markdown(f"**יחס סיכוי/סיכון:** {res['יחס סיכוי/סיכון']}")
                    with c_rr_info.popover("ℹ️"):
                        st.write("יחס הרווח מול הסיכון. 2.0 ומעלה נחשב יחס מצוין.")

                with c2:
                    st.caption("גרף אינטראקטיבי (העבר אצבע לזיהוי מחיר ותאריך)")
                    fig = plot_interactive_chart(res['df'], res['מניה'], res['prefix'])
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    ISRAEL_TICKERS = ["TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA", "ICL.TA", "HARL.TA", "MZTF.TA"]
    USA_TICKERS = ["AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "AMD", "META", "NFLX", "INTC"]
    ALL_TICKERS = ISRAEL_TICKERS + USA_TICKERS

    with st.spinner("מביא מחירי אמת ומעדכן את ה-Top 5..."):
        results_israel = []
        results_usa = []
        histories_df = {}
        prefixes = {}

        for ticker in ALL_TICKERS:
            res, err = analyze_ticker(ticker, period=selected_period)
            if res:
                is_israeli = ticker.endswith(".TA")
                item = {
                    "מניה": res["מניה"],
                    "כדאיות": res["המלצה"],
                    "דירוג המלצה": res["דירוג המלצה"],
                    "מחיר עדכני": res["מחיר עדכני"],
                    "תבנית נר": res["תבנית נר"],
                    "הסבר נר": res["הסבר נר"],
                    "הסבר המלצה": res["הסבר המלצה"],
                    "RSI": res["RSI"],
                    "סטופ לוס": res["סטופ לוס"],
                    "מחיר יעד": res["מחיר יעד"],
                    "פוטנציאל רווח (%)": res["פוטנציאל רווח (%)"],
                    "יחס סיכוי/סיכון": res["יחס סיכוי/סיכון"]
                }
                if is_israeli:
                    results_israel.append(item)
                else:
                    results_usa.append(item)
                histories_df[ticker] = res["df"]
                prefixes[ticker] = res["prefix"]

        st.subheader("🇮🇱 Top 5 הזדמנויות - הבורסה בתל אביב")
        df_il = pd.DataFrame()
        if results_israel:
            # מיון כפול: קודם לפי דירוג הכדאיות (מהגבוה לנמוך) ואז לפי פוטנציאל הרווח
            df_il = pd.DataFrame(results_israel).sort_values(by=["דירוג המלצה", "פוטנציאל רווח (%)"], ascending=[False, False]).head(5).reset_index(drop=True)
            df_il["מקום"] = [f"#{i+1}" for i in range(len(df_il))]
            display_cols = ["מקום", "מניה", "כדאיות", "מחיר עדכני", "תבנית נר", "RSI", "מחיר יעד", "סטופ לוס", "פוטנציאל רווח (%)"]
            st.dataframe(df_il[display_cols], use_container_width=True, hide_index=True)

        st.markdown("---")

        st.subheader("🇺🇸 Top 5 הזדמנויות - בורסת ארה\"ב")
        df_us = pd.DataFrame()
        if results_usa:
            # מיון כפול: קודם לפי דירוג הכדאיות (מהגבוה לנמוך) ואז לפי פוטנציאל הרווח
            df_us = pd.DataFrame(results_usa).sort_values(by=["דירוג המלצה", "פוטנציאל רווח (%)"], ascending=[False, False]).head(5).reset_index(drop=True)
            df_us["מקום"] = [f"#{i+1}" for i in range(len(df_us))]
            display_cols = ["מקום", "מניה", "כדאיות", "מחיר עדכני", "תבנית נר", "RSI", "מחיר יעד", "סטופ לוס", "פוטנציאל רווח (%)"]
            st.dataframe(df_us[display_cols], use_container_width=True, hide_index=True)

        st.markdown("---")

        st.subheader("📊 פירוט וגרפים - 10 המניות הנבחרות")
        all_top = pd.concat([df_il, df_us], ignore_index=True)

        if not all_top.empty:
            for index, row in all_top.iterrows():
                ticker_name = row['מניה']
                rank_str = row['מקום']
                with st.expander(f"📌 {rank_str} {ticker_name} - {row['כדאיות']} | פוטנציאל: {row['פוטנציאל רווח (%)']}%"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown(f"**מחיר עדכני:** {row['מחיר עדכני']}")
                        
                        c_rec, c_rec_info = st.columns([4, 1])
                        c_rec.markdown(f"**כדאיות כניסה:** {row['כדאיות']}")
                        with c_rec_info.popover("ℹ️"):
                            st.write(row['הסבר המלצה'])

                        c_candle, c_candle_info = st.columns([4, 1])
                        c_candle.markdown(f"**תבנית נר:** {row['תבנית נר']}")
                        with c_candle_info.popover("ℹ️"):
                            st.write(row['הסבר נר'])

                        c_rsi, c_rsi_info = st.columns([4, 1])
                        c_rsi.markdown(f"**מדד RSI:** {row['RSI']}")
                        with c_rsi_info.popover("ℹ️"):
                            st.write("מדד עוצמה יחסית (1-100). מראה את מומנטום הקונים מול המוכרים.")

                        c_tp, c_tp_info = st.columns([4, 1])
                        c_tp.markdown(f"**יעד רווח:** {row['מחיר יעד']}")
                        with c_tp_info.popover("ℹ️"):
                            st.write("מחיר יציאה מומלץ למימוש רווחים בעסקה.")

                        c_sl, c_sl_info = st.columns([4, 1])
                        c_sl.markdown(f"**קץ סיכון:** {row['סטופ לוס']}")
                        with c_sl_info.popover("ℹ️"):
                            st.write("מחיר הגנה קריטי (Stop Loss) לחיתוך הפסד בזמן.")

                        c_rr, c_rr_info = st.columns([4, 1])
                        c_rr.markdown(f"**יחס סיכוי/סיכון:** {row['יחס סיכוי/סיכון']}")
                        with c_rr_info.popover("ℹ️"):
                            st.write("יחס הרווח מול הסיכון. 2.0 ומעלה נחשב יחס מצוין לעסקה.")

                    with col2:
                        fig = plot_interactive_chart(histories_df[ticker_name], ticker_name, prefixes[ticker_name])
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
