import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(page_title="Stock Scanner Pro - Full Market Edition", page_icon="📈", layout="wide")

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

# פונקציות להבאת רשימות המניות המלאות של כל השוק
@st.cache_data(ttl=86400)
def get_all_us_tickers():
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        sp500 = [t.replace('.', '-') for t in sp500]
        extra_us = ["QQQ", "IWM", "PLTR", "SOFI", "HOOD", "COIN", "U", "RBLX", "ARM", "SMCI"]
        all_us = list(set(sp500 + extra_us))
        return sorted(all_us)
    except Exception:
        return ["AAPL", "NVDA", "TSLA", "AMZN", "GOOGL", "MSFT", "AMD", "META", "NFLX", "INTC", "PLTR", "ARM", "SMCI"]

@st.cache_data(ttl=86400)
def get_all_israel_tickers():
    il_tickers = [
        "TEVA.TA", "LUMI.TA", "POLI.TA", "DLEKG.TA", "BEZQ.TA", "ORL.TA", "NICE.TA", "ICL.TA", 
        "HARL.TA", "MZTF.TA", "ESLT.TA", "LBRT.TA", "FIBI.TA", "DSCT.TA", "AZRG.TA", "NVTG.TA",
        "ENOG.TA", "KEN.TA", "DELT.TA", "SAE.TA", "STR.TA", "FOX.TA", "MTRX.TA", "SPEN.TA",
        "ELAL.TA", "RTLR.TA", "ARGO.TA", "HLAN.TA", "ONE.TA", "FORTY.TA", "DIMO.TA", "SCL.TA"
    ]
    return sorted(list(set(il_tickers)))

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        st.title("🔒 התחברות למערכת הסורק")
        username = st.text_input("שם משתמש")
        password = st.text_input("סיסמה", type="password")
        if st.button("התחבר"):
            if username == "shemi" and password == "yahav8122011":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("שם משתמש או סיסמה שגויים")
        return False
    return True

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
        return ("🔨 נר פטיש (איתות עליות)", "bullish", "נר פטיש מציג צל ישר וארוך למטה.")

    if p_close < p_open and c_close > c_open and c_open <= p_close and c_close >= p_open:
        return ("🟢 בליעה שורית (איתות עליות)", "bullish", "הנר הירוק בולע לחלוטין את הנר האדום.")

    if p_close > p_open and c_close < c_open and c_open >= p_close and c_close <= p_open:
        return ("🔴 בליעה דובית (איתות ירידות)", "bearish", "הנר האדום בולע לחלוטין את הנר הירוק.")

    if c_close > c_open:
        return ("🕯️ נר ירוק רגיל", "neutral", "מחיר הסגירה גבוה ממחיר הפתיחה.")
    else:
        return ("🕯️ נר אדום רגיל", "neutral", "מחיר הסגירה נמוך ממחיר הפתיחה.")

def calculate_score_and_recommendation(pattern_type, rsi, ratio, ma50, ma200, current_price, rvol):
    score_points = 0
    reasons = []

    above_ma50 = current_price > ma50 if ma50 else False
    above_ma200 = current_price > ma200 if ma200 else False

    if above_ma50 and above_ma200:
        score_points += 3
        reasons.append("מגמה ראשית עולה (מעל MA50 ו-MA200)")
    elif above_ma50:
        score_points += 2
        reasons.append("מעל ממוצע נע 50")
    elif above_ma200:
        score_points += 1

    if rvol >= 1.5:
        score_points += 2
        reasons.append(f"כניסת כסף מוסדי כבד (RVOL {rvol:.1f}x)")
    elif rvol >= 1.2:
        score_points += 1
        reasons.append(f"נפח מסחר מוגבר (RVOL {rvol:.1f}x)")

    if ratio >= 2.0:
        score_points += 2
        reasons.append(f"יחס סיכוי/סיכון מעולה ({ratio}:1)")
    elif ratio >= 1.3:
        score_points += 1

    if pattern_type == "bullish":
        score_points += 2
        reasons.append("תבנית נרות שורית להיפוך עליות")
    elif pattern_type == "bearish":
        score_points -= 2

    if 35 <= rsi <= 60:
        score_points += 1
        reasons.append(f"RSI באזור מומנטום אידיאלי ({rsi:.1f})")
    elif rsi < 35:
        score_points += 1
        reasons.append(f"מכירת יתר - RSI נמוך ({rsi:.1f})")

    final_score = max(1, min(10, score_points))
    is_golden_trade = final_score >= 8

    if final_score >= 8:
        rec_title = f"🏆 עסקת זהב ({final_score}/10)"
        rec_desc = f"מדד עוצמה גבוה במיוחד: {final_score}/10 (10/10 = הכי חזק)."
    elif final_score >= 6:
        rec_title = f"✅ איתות שורי חזק ({final_score}/10)"
        rec_desc = f"מדד עוצמה: {final_score}/10."
    elif final_score >= 4:
        rec_title = f"🟡 ניטרלי / בזהירות ({final_score}/10)"
        rec_desc = f"מדד עוצמה: {final_score}/10."
    else:
        rec_title = f"🔴 איתות חלש ({final_score}/10)"
        rec_desc = f"מדד עוצמה נמוך: {final_score}/10 (1/10 = הכי חלש)."

    return rec_title, final_score, rec_desc, is_golden_trade, reasons

def analyze_single_ticker(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="6mo", auto_adjust=False)

        if df.empty or len(df) < 30:
            return None

        is_israeli = ticker.endswith(".TA")
        raw_price = float(df['Close'].iloc[-1])

        if is_israeli:
            price_ils = raw_price / 100.0 if raw_price > 50 else raw_price
            price_agorot = price_ils * 100.0
            display_price = f"₪{price_ils:.2f} ({int(price_agorot):,} אג')"
            calc_price = price_ils
            prefix = "₪"
            if df['Close'].iloc[-1] > 50:
                df['Open'] /= 100.0
                df['High'] /= 100.0
                df['Low'] /= 100.0
                df['Close'] /= 100.0
        else:
            display_price = f"${raw_price:.2f}"
            calc_price = raw_price
            prefix = "$"

        df['MA50'] = df['Close'].rolling(window=50).mean()
        df['MA200'] = df['Close'].rolling(window=200).mean()

        ma50_val = df['MA50'].iloc[-1] if not pd.isna(df['MA50'].iloc[-1]) else None
        ma200_val = df['MA200'].iloc[-1] if not pd.isna(df['MA200'].iloc[-1]) else None

        recent_vol = df['Volume'].iloc[-1]
        avg_vol_20 = df['Volume'].tail(20).mean()
        rvol = float(recent_vol / avg_vol_20) if avg_vol_20 > 0 else 1.0

        candle_pattern, pattern_type, candle_desc = detect_candlestick_pattern(df)

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if not loss.empty and loss.iloc[-1] != 0 else 50.0

        high_low = df['High'] - df['Low']
        atr = float(high_low.rolling(14).mean().iloc[-1]) if len(high_low) >= 14 else calc_price * 0.02
        if pd.isna(atr) or atr <= 0:
            atr = calc_price * 0.02

        stop_loss = round(calc_price - (1.5 * atr), 2)
        target = round(calc_price + (3.0 * atr), 2)

        potential_gain_pct = round(((target - calc_price) / calc_price) * 100, 2)
        risk_pct = round(((calc_price - stop_loss) / calc_price) * 100, 2)
        ratio = round(potential_gain_pct / risk_pct, 2) if risk_pct > 0 else 0

        rec_title, score_10, rec_desc, is_golden, reasons = calculate_score_and_recommendation(
            pattern_type, rsi, ratio, ma50_val, ma200_val, calc_price, rvol
        )

        return {
            "מניה": ticker,
            "כדאיות": str(rec_title),
            "ציון": int(score_10),
            "עסקת זהב": bool(is_golden),
            "מחיר עדכני": display_price,
            "RVOL": f"{rvol:.2f}x",
            "תבנית נר": str(candle_pattern),
            "הסבר נר": candle_desc,
            "הסבר המלצה": rec_desc,
            "RSI": round(rsi, 1),
            "סטופ לוס": f"{prefix}{stop_loss}",
            "מחיר יעד": f"{prefix}{target}",
            "פוטנציאל רווח (%)": potential_gain_pct,
            "יחס סיכוי/סיכון": ratio,
            "נימוקים": reasons,
            "df": df.tail(120),
            "prefix": prefix
        }
    except Exception:
        return None

def plot_interactive_chart(df, ticker, prefix):
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df.index, y=df['Close'], mode='lines', name='מחיר',
        line=dict(color='#0066cc', width=2.5),
        hovertemplate='%{x|%d/%m/%Y}<br>מחיר: ' + prefix + '%{y:.2f}<extra></extra>'
    ))

    if 'MA50' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA50'], mode='lines', name='MA 50',
            line=dict(color='#ff9900', width=1.5, dash='dash')
        ))

    if 'MA200' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index, y=df['MA200'], mode='lines', name='MA 200',
            line=dict(color='#e63946', width=1.5, dash='dot')
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
    st.title("📈 Stock Scanner Pro - Full Market Scanner")

    us_tickers = get_all_us_tickers()
    israel_tickers = get_all_israel_tickers()

    st.sidebar.header("⚙️ בקרת סורק השוק המלא")
    st.sidebar.info(f"🌐 נטענו **{len(israel_tickers)}** מניות מישראל ו-**{len(us_tickers)}** מניות מארה\"ב.")

    run_scan = st.button("🚀 הרץ סריקה מלאה על כל השוק (ישראל + ארה\"ב)", type="primary")

    if run_scan:
        all_results = []
        histories_df = {}
        prefixes = {}

        total_tickers = israel_tickers + us_tickers
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("מריץ סריקה מקבילית מהירה על מאות מניות...")

        completed_count = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ticker = {executor.submit(analyze_single_ticker, ticker): ticker for ticker in total_tickers}
            for future in as_completed(future_to_ticker):
                res = future.result()
                if res:
                    all_results.append(res)
                    histories_df[res["מניה"]] = res["df"]
                    prefixes[res["מניה"]] = res["prefix"]
                
                completed_count += 1
                progress_bar.progress(completed_count / len(total_tickers))

        status_text.success("הסריקה הושלמה בהצלחה! 🎉")

        df_all = pd.DataFrame(all_results)

        if not df_all.empty:
            st.subheader("🇮🇱 Top 5 הזדמנויות - הבורסה בתל אביב (מתוך כל השוק)")
            df_il = df_all[df_all["מניה"].str.endswith(".TA")].sort_values(
                by=["ציון", "פוטנציאל רווח (%)"], ascending=[False, False]
            ).head(5).reset_index(drop=True)

            if not df_il.empty:
                df_il["מקום"] = [f"#{i+1}" for i in range(len(df_il))]
                display_cols = ["מקום", "מניה", "כדאיות", "מחיר עדכני", "RVOL", "תבנית נר", "RSI", "מחיר יעד", "סטופ לוס", "פוטנציאל רווח (%)"]
                st.dataframe(df_il[display_cols], use_container_width=True, hide_index=True)

            st.markdown("---")

            st.subheader("🇺🇸 Top 5 הזדמנויות - בורסת ארה\"ב (מתוך כל השוק)")
            df_us = df_all[~df_all["מניה"].str.endswith(".TA")].sort_values(
                by=["ציון", "פוטנציאל רווח (%)"], ascending=[False, False]
            ).head(5).reset_index(drop=True)

            if not df_us.empty:
                df_us["מקום"] = [f"#{i+1}" for i in range(len(df_us))]
                display_cols = ["מקום", "מניה", "כדאיות", "מחיר עדכני", "RVOL", "תבנית נר", "RSI", "מחיר יעד", "סטופ לוס", "פוטנציאל רווח (%)"]
                st.dataframe(df_us[display_cols], use_container_width=True, hide_index=True)

            st.markdown("---")

            st.subheader("📊 פירוט וגרפים - 10 המניות החזקות ביותר בשוק")
            all_top = pd.concat([df_il, df_us], ignore_index=True)

            for index, row in all_top.iterrows():
                ticker_name = row['מניה']
                rank_str = row['מקום']
                badge = "🏆 " if row['עסקת זהב'] else "📌 "

                with st.expander(f"{badge}{rank_str} {ticker_name} - {row['כדאיות']} | פוטנציאל: {row['פוטנציאל רווח (%)']}%"):
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        st.markdown(f"**מחיר עדכני:** {row['מחיר עדכני']}")
                        st.markdown(f"**מדד עוצמה (1-10):** {row['כדאיות']}")
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
