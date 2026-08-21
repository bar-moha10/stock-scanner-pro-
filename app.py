import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="טרמינל ניתוח מניות מתקדם", page_icon="📈", layout="wide")

st.title("🚀 טרמינל ניתוח מניות חכם")
st.markdown("בחר מניה, בחר את שיטת הניתוח המועדפת עליך, והמערכת תפיק עבורך את תוצאות האמת מנתוני השוק!")

st.sidebar.header("🎛️ לוח בקרה ומדדים")
ticker_symbol = st.sidebar.text_input("הכנס סימול מניה (למשל: DLEKG.TA, AAPL, MSFT, TSLA):", value="AAPL")

analysis_method = st.sidebar.selectbox(
    "בחר שיטת ניתוח:",
    [
        "1. נרות יפניים (Japanese Candlesticks)",
        "2. תבניות גרף קלאסיות (Chart Patterns)",
        "3. רמות מפתח, פריצות ונפחים (Breakouts & Volume)",
        "4. מתנדים וממוצעים נעים (RSI, MACD, MAs)",
        "5. ניתוח פונדמנטלי קלאסי (Fundamental Ratios)",
        "6. מודל שווי נכסי נטו (NAV - Net Asset Value)",
        "7. מודל הערכת שווי תזרימי (DCF & Gordon Growth)"
    ]
)

run_button = st.sidebar.button("הפעל ניתוח מערכתי 🔍")

if run_button:
    with st.spinner(f'מנתח את המניה {ticker_symbol} לפי {analysis_method}...'):
        try:
            stock = yf.Ticker(ticker_symbol)
            hist = stock.history(period="6mo")
            info = stock.info

            if hist.empty:
                st.error("לא נמצאו נתונים עבור סימול זה. בדוק את האיות.")
            else:
                current_price = hist['Close'].iloc[-1]
                prev_close = hist['Close'].iloc[-2]
                price_change = ((current_price - prev_close) / prev_close) * 100
                
                col1, col2, col3 = st.columns(3)
                col1.metric("שם החברה", info.get('longName', ticker_symbol))
                col2.metric("מחיר נוכחי", f"{current_price:.2f} {info.get('currency', '$')}", f"{price_change:.2f}%")
                col3.metric("שווי שוק", f"{info.get('marketCap', 'N/A'):,}" if isinstance(info.get('marketCap'), int) else "N/A")

                st.markdown("---")
                st.subheader(f"📊 תוצאות ניתוח: {analysis_method}")

                if "1. נרות יפניים" in analysis_method:
                    last_open = hist['Open'].iloc[-1]
                    last_close = hist['Close'].iloc[-1]
                    if last_close > last_open:
                        st.success("🕯️ נר אחרון: **ירוק (שורטי/עולה)**")
                    else:
                        st.warning("🕯️ נר אחרון: **אדום (דובי/יורד)**")
                    st.line_chart(hist['Close'])

                elif "2. תבניות גרף" in analysis_method:
                    st.write(f"- **שיא תקופתי:** {hist['High'].max():.2f}")
                    st.write(f"- **שפל תקופתי:** {hist['Low'].min():.2f}")
                    st.line_chart(hist[['Close']])

                elif "3. רמות מפתח" in analysis_method:
                    st.write(f"- **התנגדות קרובה:** {hist['High'].tail(20).max():.2f}")
                    st.write(f"- **תמיכה קרובה:** {hist['Low'].tail(20).min():.2f}")
                    st.bar_chart(hist['Volume'].tail(20))

                elif "4. מתנדים וממוצעים" in analysis_method:
                    ma50 = hist['Close'].tail(50).mean()
                    st.write(f"- **ממוצע נעים 50 ימים:** {ma50:.2f}")
                    st.line_chart(hist['Close'])

                elif "5. ניתוח פונדמנטלי" in analysis_method:
                    st.write(f"- **מכפיל רווח (P/E):** {info.get('trailingPE', 'N/A')}")
                    st.write(f"- **מכפיל הון (P/B):** {info.get('priceToBook', 'N/A')}")

                elif "6. מודל שווי נכסי" in analysis_method:
                    st.write(f"- **ערך בספרים למניה:** {info.get('bookValue', 'N/A')}")

                elif "7. מודל הערכת שווי תזרימי" in analysis_method:
                    st.write(f"- **תזרים מזומנים חופשי אחרון (FCF):** {info.get('freeCashflow', 'N/A')}")

        except Exception as e:
            st.error(f"אירעה שגיאה: {e}")
else:
    st.info("👈 בחר מניה ושיטת ניתוח ולחץ על הפעל ניתוח.")
