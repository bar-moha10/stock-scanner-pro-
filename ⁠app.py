import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor, as_completed

st.set_page_config(
    page_title="Stock Scanner Pro", 
    page_icon="📈", 
    layout="wide",
    initial_sidebar_state="expanded"
)

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

ISRAEL_STOCKS_INFO = {
    "TEVA.TA": {"name": "טבע", "id": "1081124"},
    "LUMI.TA": {"name": "בנק לאומי", "id": "604011"},
    "POLI.TA": {"name": "בנק הפועלים", "id": "662577"},
    "DLEKG.TA": {"name": "קבוצת דלק", "id": "1081116"},
    "BEZQ.TA": {"name": "בזק", "id": "238011"},
    "ORL.TA": {"name": "בזן (בתי זיקוק)", "id": "401011"},
    "NICE.TA": {"name": "נייס", "id": "1081132"},
    "ICL.TA": {"name": "כיל / איי.סי.אל", "id": "281014"},
    "HARL.TA": {"name": "הראל השקעות", "id": "259016"},
    "MZTF.TA": {"name": "מזרחי טפחות", "id": "698019"},
    "ESLT.TA": {"name": "אלביט מערכות", "id": "108112"},
    "LBRT.TA": {"name": "ליברה ביטוח", "id": "1160356"},
    "FIBI.TA": {"name": "הבינלאומי", "id": "1081140"},
    "DSCT.TA": {"name": "בנק דיסקונט", "id": "654012"},
    "AZRG.TA": {"name": "עזריאלי", "id": "1128114"},
    "NVTG.TA": {"name": "נובה", "id": "1081157"},
    "ENOG.TA": {"name": "אנרג'יאן", "id": "1159044"},
    "KEN.TA": {"name": "קנזון / קן", "id": "1148013"},
    "DELT.TA": {"name": "דלתא גליל", "id": "1081165"},
    "SAE.TA": {"name": "סאמיט", "id": "1098128"},
    "STR.TA": {"name": "שטראוס", "id": "319012"},
    "FOX.TA": {"name": "פוקס", "id": "1118016"},
    "MTRX.TA": {"name": "מטריקס", "id": "1078012"},
    "SPEN.TA": {"name": "שפיר אנגיניירינג", "id": "1134013"},
    "ELAL.TA": {"name": "אל על", "id": "312017"},
    "RTLR.TA": {"name": "רציו אנרגיות", "id": "245016"},
    "ARGO.TA": {"name": "ארקו החזקות", "id": "1124014"},
    "HLAN.TA": {"name": "היילנד", "id": "1141018"},
    "ONE.TA": {"name": "וואן טכנולוגיות", "id": "1092014"},
    "FORTY.TA": {"name": "פורמולה מערכות", "id": "1081173"},
    "DIMO.TA": {"name": "דימול", "id": "1151017"},
    "SCL.TA": {"name": "סלקום", "id": "270016"}
}

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
    return sorted(list(set(ISRAEL_STOCKS_INFO.keys())))

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
            
            stock_info = ISRAEL_STOCKS_INFO.get(ticker, {"name": ticker, "id": "לא ידוע"})
            display_name = stock_info["name"]
            stock_id = stock_info["id"]
        else:
            display_price = f"${raw_price:.2f}"
            calc_price = raw_price
            prefix = "$"
            display_name = ticker
            stock_id = ticker

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
            "שם תצוגה": display_name,
            "מספר נייר": stock_id,
            "כדאיות": rec_title,
            "ציון": score_10,
            "עסקת זהב": is_golden,
            "מחיר עדכני": display_price,
            "מחיר מספרי": calc_price,
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

if check_password():
    st.title("📈 Stock Scanner Pro - Top 10")
    
    if "virtual_portfolio" not in st.session_state:
        st.session_state["virtual_portfolio"] = []

    us_tickers = get_all_us_tickers()
    israel_tickers = get_all_israel_tickers()

    with st.sidebar:
        st.header("⚙️ בקרת מערכת")
        st.success("מחובר כמשתמש: **shemi**")
        run_scan_sidebar = st.button("🚀 הפעל סריקת שוק מלאה (צד)", type="primary")

    st.markdown("### 🔍 התחלת עבודה")
    run_scan_main = st.button("🚀 הפעל סריקת שוק מלאה עכשיו", type="primary", use_container_width=True)

    run_scan = run_scan_sidebar or run_scan_main

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
        st.session_state["df_all"] = df_all
        st.session_state["histories_df"] = histories_df
        st.session_state["prefixes"] = prefixes

    if "df_all" in st.session_state and not st.session_state["df_all"].empty:
        df_all = st.session_state["df_all"]
        histories_df = st.session_state["histories_df"]
        prefixes = st.session_state["prefixes"]

        tab_il, tab_us, tab_portfolio = st.tabs([
            "🇮🇱 מניות ישראל (Top 10)", 
            "🇺🇸 מניות ארה\"ב (Top 10)", 
            "💼 תיק וירטואלי"
        ])

        with tab_il:
            st.subheader("10 המניות החזקות ביותר בבורסת תל אביב")
            df_il = df_all[df_all["מניה"].str.endswith(".TA")].sort_values(
                by=["ציון", "פוטנציאל רווח (%)"], ascending=[False, False]
            ).head(10).reset_index(drop=True)

            if df_il.empty:
                st.info("אין מספיק נתונים כרגע למניות ישראל.")
            else:
                for idx, row in df_il.iterrows():
                    badge = "🏆" if row['עסקת זהב'] else "📌"
                    title_text = f"{badge} #{idx+1} | {row['שם תצוגה']} ({row['מספר נייר']} / {row['מניה']})"
                    
                    with st.expander(title_text):
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
                    title_text = f"{badge} #{idx+1} | {row['מניה']}"

                    with st.expander(title_text):
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

        with tab_portfolio:
            st.subheader("💼 ניהול תיק השקעות וירטואלי")
            
            with st.form("add_trade_form"):
                st.markdown("**הוסף עסקת רכישה חדשה:**")
                
                ticker_options = {}
                for _, r in df_all.iterrows():
                    display_label = f"{r['שם תצוגה']} ({r['מניה']})"
                    ticker_options[display_label] = r['מניה']
                
                selected_label = st.selectbox("בחר מניה (ניתן להקליד שם בעברית או סימבול)", list(ticker_options.keys()))
                selected_ticker_port = ticker_options[selected_label]

                default_price_row = df_all[df_all["מניה"] == selected_ticker_port]
                def_val = float(default_price_row["מחיר מספרי"].values[0]) if not default_price_row.empty else 10.0

                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    purchase_mode = st.radio("צורת רכישה:", ["לפי כמות יחידות", "לפי סכום כסף השקעה"])
                with col_f2:
                    buy_price = st.number_input("מחיר קנייה ליחידה", min_value=0.01, value=def_val, format="%.2f")

                if purchase_mode == "לפי כמות יחידות":
                    shares_qty = st.number_input("כמות יחידות", min_value=1, value=100)
                else:
                    investment_amount = st.number_input("סכום כסף להשקעה (₪/$)", min_value=1.0, value=100000.0, format="%.2f")
                    shares_qty = int(investment_amount // buy_price) if buy_price > 0 else 0
                    st.caption(f"💡 לפי המחיר הנוכחי, הסכום יקנה לך בקירוב: **{shares_qty} יחידות**")

                submit_trade = st.form_submit_button("➕ הוסף לתיק", type="primary")
                if submit_trade:
                    if shares_qty <= 0:
                        st.error("הסכום שהוזן קטן מדי מכדי לקנות אפילו יחידה אחת שלמה.")
                    else:
                        st.session_state["virtual_portfolio"].append({
                            "ticker": selected_ticker_port,
                            "shares": shares_qty,
                            "buy_price": buy_price
                        })
                        st.success(f"העסקה נוספה בהצלחה! ({shares_qty} יחידות)")
                        st.rerun()

            st.markdown("---")
            st.markdown("### 📊 מצב התיק הנוכחי שלך")
            
            if not st.session_state["virtual_portfolio"]:
                st.info("התיק שלך ריק כרגע. הוסף עסקאות באמצעות הטופס למעלה.")
            else:
                portfolio_rows = []
                total_invested = 0
                total_current_value = 0

                for i, trade in enumerate(st.session_state["virtual_portfolio"]):
                    ticker = trade["ticker"]
                    shares = trade["shares"]
                    buy_price = trade["buy_price"]
                    
                    match_row = df_all[df_all["מניה"] == ticker]
                    if not match_row.empty:
                        current_price = float(match_row["מחיר מספרי"].values[0])
                        prefix = match_row["prefix"].values[0]
                        display_name = match_row["שם תצוגה"].values[0]
                    else:
                        current_price = buy_price
                        prefix = "$"
                        display_name = ticker

                    invested = shares * buy_price
                    current_val = shares * current_price
                    pnl_ils = current_val - invested
                    pnl_pct = ((current_price - buy_price) / buy_price) * 100 if buy_price > 0 else 0

                    total_invested += invested
                    total_current_value += current_val

                    portfolio_rows.append({
                        "מניה": display_name,
                        "סימבול": ticker,
                        "כמות": shares,
                        "מחיר קנייה": f"{prefix}{buy_price:.2f}",
                        "מחיר נוכחי": f"{prefix}{current_price:.2f}",
                        "שווי נוכחי": f"{prefix}{current_val:.2f}",
                        "רווח/הפסד (₪/$)": f"{prefix}{pnl_ils:+.2f}",
                        "תשואה (%)": f"{pnl_pct:+.2f}%",
                        "raw_pnl": pnl_ils
                    })

                df_port = pd.DataFrame(portfolio_rows)
                st.dataframe(df_port.drop(columns=["raw_pnl"]), use_container_width=True)

                total_pnl = total_current_value - total_invested
                total_pnl_pct = ((total_current_value - total_invested) / total_invested) * 100 if total_invested > 0 else 0

                col_m1, col_m2, col_m3 = st.columns(3)
                col_m1.metric("סה\"כ השקעה", f"{total_invested:,.2f}")
                col_m2.metric("שווי נוכחי של התיק", f"{total_current_value:,.2f}")
                col_m3.metric("רווח / הפסד כולל", f"{total_pnl:+,.2f}", f"{total_pnl_pct:+.2f}%")

                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🗑️ נקה את כל התיק"):
                    st.session_state["virtual_portfolio"] = []
                    st.rerun()
    else:
        st.info("👈 לחץ על כפתור **'הפעל סריקת שוק מלאה עכשיו'** כדי לטעון את הנתונים ולנהל את התיק הווירטואלי.")
