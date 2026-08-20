import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go

st.set_page_config(page_title="Stock Scanner Pro - Golden Trade Edition", page_icon="📈", layout="wide")

# עיצוב CSS
st.markdown("""
    <style>
    div[data-testid="stDataFrame"] td {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #ffffff !important;
    }
    div[data-testid="stDataFrame"] th {
        font-size: 17px !important;
        font-weight: bold !important;
        color: #00d2ff !important;
    }
    </style>
""", unsafe_allow_html=True)

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

    if lower_shadow > (2 * body) and upper_shadow < (body * 0.5) and body > 0:
        return (
            "🔨 נר פטיש (איתות עליות)",
            "bullish",
            "נר פטיש מציג צל ישר וארוך למטה. הקונים השתלטו מחדש ודחפו את המחיר למעלה."
        )

    if p_close < p_open and c_close > c_open and c_open <= p_close and c_close >= p_open:
        return (
            "🟢 בליעה שורית (איתות עליות חזק)",
            "bullish",
            "הגוף של הנר הירוק הנוכחי בולע לחלוטין את הנר האדום שלפניו. הקונים נכנסו בעוצמה."
        )

    if p_close > p_open and c_close < c_open and c_open >= p_close and c_close <= p_open:
        return (
            "🔴 בליעה דובית (איתות ירידות)",
            "bearish",
            "הגוף של הנר האדום הנוכחי בולע לחלוטין את הנר הירוק שלפניו. לחץ מכירות כבד."
        )

    if c_close > c_open:
        return (
            "🕯️ נר ירוק רגיל",
            "neutral",
            "מחיר הסגירה גבוה ממחיר הפתיחה. הקונים היו חזקים יותר ביום זה."
        )
    else:
        return (
            "🕯️ נר אדום רגיל",
            "neutral",
            "מחיר הסגירה נמוך ממחיר הפתיחה. המוכרים שלטו ביום המסחר."
        )

def calculate_score_and_recommendation(pattern_type, rsi, ratio, ma50, ma200, current_price, rvol):
    score_points = 0
    reasons = []

    # 1. מגמה מול ממוצעים נעים (עד 3 נקודות)
    above_ma50 = current_price > ma50 if ma50 else False
    above_ma200 = current_price > ma200 if ma200 else False

    if above_ma50 and above_ma200:
        score_points += 3
        reasons.append("מגמה ראשי עולה (מעל MA50 ו-MA200)")
    elif above_ma50:
        score_points += 2
        reasons.append("מעל ממוצע נע 50")
    elif above_ma200:
        score_points += 1

    # 2. נפח מסחר יחסי RVOL (עד 2 נקודות)
    if rvol >= 1.5:
        score_points += 2
        reasons.append(f"כניסת כסף מוסדי כבד (RVOL {rvol:.1f}x)")
    elif rvol >= 1.2:
        score_points += 1
        reasons.append(f"נפח מסחר מוגבר (RVOL {rvol:.1f}x)")

    # 3. יחס סיכוי / סיכון (עד 2 נקודות)
    if ratio >= 2.0:
        score_points += 2
        reasons.append(f"יחס סיכוי/סיכון מעולה ({ratio}:1)")
    elif ratio >= 1.3:
        score_points += 1

    # 4. תבנית נרות (עד 2 נקודות)
    if pattern_type == "bullish":
        score_points += 2
        reasons.append("תבנית נרות שורית להיפוך עליות")
    elif pattern_type == "bearish":
        score_points -= 2

    # 5. מדד RSI (עד 1 נקודה)
    if 35 <= rsi <= 60:
        score_points += 1
        reasons.append(f"RSI באזור מומנטום אידיאלי ({rsi:.1f})")
    elif rsi < 35:
        score_points += 1
        reasons.append(f"מכירת יתר - RSI נמוך ({rsi:.1f})")

    # נרמול הציון בדיוק לטווח של 1 עד 10
    final_score = max(1, min(10, score_points))
    is_golden_trade = final_score >= 8

    if final_score >= 8:
        rec_title = f"🏆 עסקת זהב ({final_score}/10)"
        rec_desc = f"מדד עוצמה גבוה במיוחד: {final_score}/10 (10/10 = הכי חזק). המניה עומדת בקריטריונים האיכותיים ביותר למסחר."
    elif final_score >= 6:
        rec_title = f"✅ איתות שורי חזק ({final_score}/10)"
        rec_desc = f"מדד עוצמה: {final_score}/10. מציגה מומנטום חיובי ויחס סיכוי/סיכון טוב."
    elif final_score >= 4:
        rec_title = f"🟡 ניטרלי / בזהירות ({final_score}/10)"
        rec_desc = f"מדד עוצמה: {final_score}/10. מומלץ להמתין לאישור נוסף או להגדיר סטופ לוס הדוק."
    else:
        rec_title = f"🔴 איתות חלש ({final_score}/10)"
        rec_desc = f"מדד עוצמה נמוך: {final_score}/10 (1/10 = הכי חלש). הנתונים מעידים על סיכון גבוה או חוסר מומנטום."

    return rec_title, final_score, rec_desc, is_golden_trade, reasons

def analyze_ticker(user_input, period="6mo"):
    clean_input = user_input.split("-")[0].split("/")[0].strip().replace('"', '').replace("'", "")
    ticker = HEBREW_TICKERS.get(clean_input, clean_input).upper()
    is_israeli = ticker.endswith(".TA")

    raw_live_price = get_live_price(ticker)
    t = yf.Ticker(ticker)
    df = t.history(period="1y", auto_adjust=False)

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

        history_df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()
        if history_df['Close'].iloc[-1] > 50:
            history_df['Open'] = history_df['Open'] / 100.0
            history_df['High'] = history_df['High'] / 100.0
            history_df['Low'] = history_df['Low'] / 100.0
            history_df['Close'] = history_df['Close'] / 100.0
    else:
        display_price = f"${raw_live_price:.2f}"
        calc_price = raw_live_price
        prefix = "$"
        history_df = df[['Open', 'High', 'Low', 'Close', 'Volume']].copy()

    history_df['MA50'] = history_df['Close'].rolling(window=50).mean()
    history_df['MA200'] = history_df['Close'].rolling(window=200).mean()

    ma50_val = history_df['MA50'].iloc[-1] if not pd.isna(history_df['MA50'].iloc[-1]) else None
    ma200_val = history_df['MA200'].iloc[-1] if not pd.isna(history_df['MA200'].iloc[-1]) else None

    recent_vol = history_df['Volume'].iloc[-1]
    avg_vol_20 = history_df['Volume'].tail(20).mean()
    rvol = float(recent_vol / avg_vol_20) if avg_vol_20 > 0 else 1.0

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

    rec_title, score_10, rec_desc, is_golden, reasons = calculate_score_and_recommendation(
        pattern_type, rsi, ratio, ma50_val, ma200_val, calc_price, rvol
    )

    analysis = {
        "מניה": ticker,
        "מחיר עדכני": display_price,
        "RSI": round(rsi, 1),
        "RVOL": round(rvol, 2),
        "MA50": f"{prefix}{ma50_val:.2f}" if ma50_val else "N/A",
        "MA200": f"{prefix}{ma200_val:.2f}" if ma200_val else "N/A",
        "תבנית נר": candle_pattern,
        "הסבר נר": candle_desc,
        "המלצה": str(rec_title),
        "ציון": int(score_10),
        "הסבר המלצה": rec_desc,
        "עסקת זהב": bool(is_golden),
        "נימוקים": reasons,
        "סטופ לוס": f"{prefix}{stop_loss}",
        "מחיר יעד": f"{prefix}{target}",
        "פוטנציאל רווח (%)": potential_gain_pct,
        "סיכון (%)": risk_pct,
        "יחס סיכוי/סיכון": ratio,
        "df": history_df.tail(120),
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

    if 'MA50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['MA50'],
            mode='lines',
            name='MA 50',
            line=dict(color='#ff9900', width=1.5, dash='dash'),
            hovertemplate='MA50: ' + prefix + '%{y:.2f}<extra></extra>'
        ))

    if 'MA200' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['MA200'],
            mode='lines',
            name='MA 200',
            line=dict(color='#e63946', width=1.5, dash='dot'),
            hovertemplate='MA200: ' + prefix + '%{y:.2f}<extra></extra>'
        ))

    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=5, r=5, t=10, b=10),
        height=320,
        dragmode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, zeroline=False, fixedrange=True),
        yaxis=dict(showgrid=True, zeroline=False, fixedrange=True)
    )
    return fig

if check_password():
    st.title("📈 Stock Scanner Pro - Golden Trade")

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
                    st.markdown(f"**מדד עוצמה (1-10):** {res['המלצה']}")
                    st.markdown(f"**נפח יחסי (RVOL):** {res['RVOL']}x")
                    st.markdown(f"**תבנית נר:** {res['תבנית נר']}")
                    st.markdown(f"**מדד RSI:** {res['RSI']}")
                    st.markdown(f"**מחיר יעד:** {res['מחיר יעד']}")
                    st.markdown(f"**קץ סיכון:** {res['סטופ לוס']}")
                    st.markdown(f"**יחס סיכוי/סיכון:** {res['יחס סיכוי/סיכון']}")

                with c2:
                    fig = plot_interactive_chart(res['df'], res['מניה'], res['prefix'])
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.markdown("---")

    ISRAEL_TICKERS = ["TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA", "ICL.TA", "HARL.TA", "MZTF.TA"]
    USA_TICKERS = ["AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "AMD", "META", "NFLX", "INTC"]
    ALL_TICKERS = ISRAEL_TICKERS + USA_TICKERS

    with st.spinner("מריץ סריקה מדורגת (סולם עוצמה 1/10 עד 10/10)..."):
        results_israel = []
        results_usa = []
        histories_df = {}
        prefixes = {}

        for ticker in ALL_TICKERS:
            res, err = analyze_ticker(ticker, period=selected_period)
            if res:
                is_israeli = ticker.endswith(".TA")
                item = {
                    "מניה": str(res["מניה"]),
                    "כדאיות": str(res["המלצה"]),
                    "ציון": int(res["ציון"]),
                    "עסקת זהב": bool(res["עסקת זהב"]),
                    "מחיר עדכני": str(res["מחיר עדכני"]),
                    "RVOL": f"{res['RVOL']}x",
                    "תבנית נר": str(res["תבנית נר"]),
                    "הסבר נר": str(res["הסבר נר"]),
                    "הסבר המלצה": str(res["הסבר המלצה"]),
                    "RSI": float(res["RSI"]),
                    "סטופ לוס": str(res["סטופ לוס"]),
                    "מחיר יעד": str(res["מחיר יעד"]),
                    "פוטנציאל רווח (%)": float(res["פוטנציאל רווח (%)"]),
                    "יחס סיכוי/סיכון": float(res["יחס סיכוי/סיכון"]),
                    "נימוקים": res["נימוקים"]
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
            df_il = pd.DataFrame(results_israel).sort_values(by=["ציון", "פוטנציאל רווח (%)"], ascending=[False, False]).head(5).reset_index(drop=True)
            df_il["מקום"] = [f"#{i+1}" for i in range(len(df_il))]
            display_cols = ["מקום", "מניה", "כדאיות", "מחיר עדכני", "RVOL", "תבנית נר", "RSI", "מחיר יעד", "סטופ לוס", "פוטנציאל רווח (%)"]
            st.dataframe(df_il[display_cols], use_container_width=True, hide_index=True)

        st.markdown("---")

        st.subheader("🇺🇸 Top 5 הזדמנויות - בורסת ארה\"ב")
        df_us = pd.DataFrame()
        if results_usa:
            df_us = pd.DataFrame(results_usa).sort_values(by=["ציון", "פוטנציאל רווח (%)"], ascending=[False, False]).head(5).reset_index(drop=True)
            df_us["מקום"] = [f"#{i+1}" for i in range(len(df_us))]
            display_cols = ["מקום", "מניה", "כדאיות", "מחיר עדכני", "RVOL", "תבנית נר", "RSI", "מחיר יעד", "סטופ לוס", "פוטנציאל רווח (%)"]
            st.dataframe(df_us[display_cols], use_container_width=True, hide_index=True)

        st.markdown("---")

        st.subheader("📊 פירוט וגרפים - 10 המניות הנבחרות")
        all_top = pd.concat([df_il, df_us], ignore_index=True)

        if not all_top.empty:
            for index, row in all_top.iterrows():
                ticker_name = row['מניה']
                rank_str = row['מקום']
                badge = "🏆 " if row['עסקת זהב'] else "📌 "
                
                with st.expander(f"{badge}{rank_str} {ticker_name} - {row['כדאיות']} | פוטנציאל: {row['פוטנציאל רווח (%)']}%"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown(f"**מחיר עדכני:** {row['מחיר עדכני']}")
                        st.markdown(f"**מדד עוצמה:** {row['כדאיות']}")
                        st.markdown(f"**נפח יחסי (RVOL):** {row['RVOL']}")
                        st.markdown(f"**תבנית נר:** {row['תבנית נר']}")
                        st.markdown(f"**מדד RSI:** {row['RSI']}")
                        st.markdown(f"**יעד רווח:** {row['מחיר יעד']}")
                        st.markdown(f"**קץ סיכון:** {row['סטופ לוס']}")
                        st.markdown(f"**יחס סיכוי/סיכון:** {row['יחס סיכוי/סיכון']}")
                        if row['נימוקים']:
                            st.info("💡 **גורמי מפתח:** " + " | ".join(row['נימוקים']))

                    with col2:
                        fig = plot_interactive_chart(histories_df[ticker_name], ticker_name, prefixes[ticker_name])
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
