import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed

# הגדרת עמוד רחב ומותאם
st.set_page_config(
    page_title="Stock Scanner Pro", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# עיצוב CSS נקי וממוסגר
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=86400)
def get_all_us_tickers():
    try:
        sp500 = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]['Symbol'].tolist()
        sp500 = [t.replace('.', '-') for t in sp500]
        extra_us = ["QQQ", "IWM", "PLTR", "SOFI", "HOOD", "COIN", "U", "RBLX", "ARM", "SMCI", "AAPL", "NVDA", "TSLA", "AMZN", "MSFT"]
        return sorted(list(set(sp500 + extra_us)))
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

# מסך התחברות
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    if not st.session_state["authenticated"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center; color: #00d2ff;'>🔒 התחברות למערכת הסורק</h2>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                username = st.text_input("👤 שם משתמש")
                password = st.text_input("🔑 סיסמה", type="password")
                submit = st.form_submit_button("התחבר למערכת", type="primary")
                
                if submit:
                    if username.strip().lower() == "shemi" and password == "yahav8122011":
                        st.session_state["authenticated"] = True
                        st.rerun()
                    else:
                        st.error("שם משתמש או סיסמה שגויים")
        return False
    return True

def detect_candlestick_pattern(df):
    if len(df) < 2:
        return "אין מספיק נתונים", "neutral", "אין מספיק נתוני מסחר."
    curr, prev = df.iloc[-1], df.iloc[-2]
    c_open, c_close, c_high, c_low = curr['Open'], curr['Close'], curr['High'], curr['Low']
    p_open, p_close = prev['Open'], prev['Close']
    body = abs(c_close - c_open)
    lower_shadow = min(c_open, c_close) - c_low

    if lower_shadow > (2 * body) and body > 0:
        return ("🔨 נר פטיש (שורי)", "bullish", "צל תחתון ארוך המעיד על לחץ קונים.")
    if p_close < p_open and c_close > c_open:
        return ("🟢 בליעה שורית", "bullish", "נר ירוק שבולע את האדום קודמו.")
    if c_close > c_open:
        return ("🕯️ נר ירוק רגיל", "neutral", "סגירה חיובית.")
    else:
        return ("🕯️ נר אדום רגיל", "neutral", "סגירה שלילית.")

def calculate_score_and_recommendation(pattern_type, rsi, ratio, ma50, ma200, current_price, rvol):
    score_points = 0
    reasons = []

    if current_price > ma50 if ma50 else False:
        score_points += 2
        reasons.append("מעל ממוצע נע 50")
    if current_price > ma200 if ma200 else False:
        score_points += 1
        reasons.append("מעל ממוצע נע 200")
    if rvol >= 1.2:
        score_points += 1
        reasons.append(f"נפח מסחר ער (RVOL {rvol:.1f}x)")
    if ratio >= 1.5:
        score_points += 1
        reasons.append(f"יחס סיכוי/סיכון טוב ({ratio}:1)")
    if pattern_type == "bullish":
        score_points += 2
        reasons.append("תבנית נרות שורית")

    final_score = max(1, min(10, score_points))
    is_golden_trade = final_score >= 8

    if final_score >= 8:
        rec_title = f"🏆 עסקת זהב ({final_score}/10)"
    elif final_score >= 6:
        rec_title = f"✅ שורי חזק ({final_score}/10)"
    elif final_score >= 4:
        rec_title = f"🟡 ניטרלי ({final_score}/10)"
    else:
        rec_title = f"🔴 חלש ({final_score}/10)"

    return rec_title, final_score, is_golden_trade, reasons

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
            display_price = f"₪{price_ils:.2f}"
            calc_price = price_ils
            prefix = "₪"
            if raw_price > 50:
                df[['Open', 'High', 'Low', 'Close']] /= 100.0
        else:
            display_price = f"${raw_price:.2f}"
            calc_price = raw_price
            prefix = "$"

        df['MA50'] = df['Close'].rolling(50).mean()
        df['MA200'] = df['Close'].rolling(200).mean()
        ma50_val = df['MA50'].iloc[-1] if not pd.isna(df['MA50'].iloc[-1]) else None
        ma200_val = df['MA200'].iloc[-1] if not pd.isna(df['MA200'].iloc[-1]) else None

        recent_vol = df['Volume'].iloc[-1]
        avg_vol_20 = df['Volume'].tail(20).mean()
        rvol = float(recent_vol / avg_vol_20) if avg_vol_20 > 0 else 1.0

        candle_pattern, pattern_type, candle_desc = detect_candlestick_pattern(df)

        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = float((100 - (100 / (1 + rs))).iloc[-1]) if not loss.empty and loss.iloc[-1] != 0 else 50.0

        atr = float((df['High'] - df['Low']).rolling(14).mean().iloc[-1])
        if pd.isna(atr) or atr <= 0:
            atr = calc_price * 0.02

        stop_loss = round(calc_price - (1.5 * atr), 2)
        target = round(calc_price + (3.0 * atr), 2)
        pot_gain = round(((target - calc_price) / calc_price) * 100, 2)
        risk_pct = round(((calc_price - stop_loss) / calc_price) * 100, 2)
        ratio = round(pot_gain / risk_pct, 2) if risk_pct > 0 else 0

        rec_title, score_10, is_golden, reasons = calculate_score_and_recommendation(
            pattern_type, rsi, ratio, ma50_val, ma200_val, calc_price, rvol
        )

        return {
            "מניה": ticker,
            "כדאיות": rec_title,
            "ציון": score_10,
            "עסקת זהב": is_golden,
            "מחיר עדכני": display_price,
            "RVOL": f"{rvol:.2f}x",
            "תבנית נר": candle_pattern,
            "RSI": round(rsi, 1),
            "מחיר יעד": f"{prefix}{target}",
            "סטופ לוס": f"{prefix}{stop_loss}",
            "פוטנציאל רווח (%)": pot_gain,
            "יחס סיכוי/סיכון": ratio,
            "נימוקים": reasons,
            "df": df.tail(120),
            "prefix": prefix
        }
    except Exception:
        return None

def plot_interactive_chart(df, ticker, prefix):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], mode='lines', name='מחיר', line=dict(color='#00d2ff', width=2)))
    if 'MA50' in df.columns:
        fig.add_trace(go.Scatter(x=df.index, y=df['MA50'], mode='lines', name='MA 50', line=dict(color='#ff9900', width=1.5, dash='dash')))
    
    fig.update_layout(
        hovermode="x unified",
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
        dragmode=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showgrid=True, zeroline=False, fixedrange=True),
        yaxis=dict(showgrid=True, zeroline=False, fixedrange=True)
    )
    return fig

# הרצת המערכת
if check_password():
    st.title("📈 Stock Scanner Pro - Top 10")
    
    us_tickers = get_all_us_tickers()
    israel_tickers = get_all_israel_tickers()

    with st.sidebar:
        st.header("⚙️ בקרת מערכת")
        st.success("מחובר כמשתמש: **shemi**")
        run_scan = st.button("🚀 הפעל סריקת שוק מלאה", type="primary")

    if run_scan:
        all_results = []
        histories_df = {}
        prefixes = {}
        total_tickers = israel_tickers + us_tickers

        progress_bar = st.progress(0)
        status_text = st.empty()
        status_text.text("סורק את השוק...")

        completed = 0
        with ThreadPoolExecutor(max_workers=20) as executor:
            future_to_ticker = {executor.submit(analyze_single_ticker, t): t for t in total_tickers}
            for future in as_completed(future_to_ticker):
                res = future.result()
                if res:
                    all_results.append(res)
                    histories_df[res["מניה"]] = res["df"]
                    prefixes[res["מניה"]] = res["prefix"]
                completed += 1
                progress_bar.progress(completed / len(total_tickers))

        status_text.success("הסריקה הסתיימה!")
        df_all = pd.DataFrame(all_results)

        if not df_all.empty:
            # יצירת לשוניות נפרדות לארץ ולארה"ב
            tab_il, tab_us = st.tabs(["🇮🇱 מניות ישראל (Top 10)", "🇺🇸 מניות ארה\"ב (Top 10)"])

            with tab_il:
                st.subheader("10 המניות החזקות ביותר בבורסת תל אביב")
                df_il = df_all[df_all["מניה"].str.endswith(".TA")].sort_values(
                    by=["ציון", "פוטנציאל רווח (%)"], ascending=[False, False]
                ).head(10).reset_index(drop=True)

                if df_il.empty:
                # Fallback if no IL stocks found
                    st.info("אין מספיק נתונים כרגע למניות ישראל.")
                else:
                    for idx, row in df_il.iterrows():
                        badge = "🏆" if row['עסקת זהב'] else "📌"
                        # כותרת נקייה: מספר סידורי ושם המניה בלבד
                        with st.expander(f"{badge} #{idx+1} | סימבול: {row['מניה']}"):
                            c1, c2 = st.columns([1, 1.5])
                            with c1:
                                st.markdown(f"**מחיר עדכני:** {row['מחיר עדכני']}")
                                st.markdown(f"**ציון מערכת:** {row['כדאיות']}")
                                st.markdown(f"**נפח מסחר יחסי:** {row['RVOL']}")
                                st.markdown(f"**תבנית נר:** {row['תבנית נר']}")
                                st.markdown(f"**RSI:** {row['RSI']}")
                                st.markdown(f"**יעד רווח:** {row['מחיר יעד']}")
                                st.markdown(f"**סטופ לוס:** {row['סטופ לוס']}")
                                st.markdown(f"**פוטנציאל רווח:** {row['פוטנציאל רווח (%)']}%")
                                if row['נימוקים']:
                                    st.info("💡 " + " | ".join(row['נימוקים']))
                            with c2:
                                fig = plot_interactive_chart(histories_df[row['מניה']], row['מניה'], prefixes[row['מניה']])
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            with tab_us:
                st.subheader("10 המניות החזקות ביותר בבורסת ארה\"ב")
                df_us = df_all[~df_all["מניה"].str.endswith(".TA")].sort_values(
                    by=["ציון", "פוטנציאל רווח (%)"], ascending=[False, False]
                ).head(10).reset_index(drop=True)

                if df_us.empty:
                    st.info("אין מספיק נתונים כרגע למניות ארה\"ב.")
                else:
                    for idx, row in df_us.iterrows():
                        badge = "🏆" if row['עסקת זהב'] else "📌"
                        # כותרת נקייה: מספר סידורי ושם המניה בלבד
                        with st.expander(f"{badge} #{idx+1} | סימבול: {row['מניה']}"):
                            c1, c2 = st.columns([1, 1.5])
                            with c1:
                                st.markdown(f"**מחיר עדכני:** {row['מחיר עדכני']}")
                                st.markdown(f"**ציון מערכת:** {row['כדאיות']}")
                                st.markdown(f"**נפח מסחר יחסי:** {row['RVOL']}")
                                st.markdown(f"**תבנית נר:** {row['תבנית נר']}")
                                st.markdown(f"**RSI:** {row['RSI']}")
                                st.markdown(f"**יעד רווח:** {row['מחיר יעד']}")
                                st.markdown(f"**סטופ לוס:** {row['סטופ לוס']}")
                                st.markdown(f"**פוטנציאל רווח:** {row['פוטנציאל רווח (%)']}%")
                                if row['נימוקים']:
                                    st.info("💡 " + " | ".join(row['נימוקים']))
                            with c2:
                                fig = plot_interactive_chart(histories_df[row['מניה']], row['מניה'], prefixes[row['מניה']])
                                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    else:
        st.info("👈 לחץ על **'הפעל סריקת שוק מלאה'** בתפריט הצדדי כדי לטעון את רשימות ה-Top 10.")
