import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# הגדרות תצוגת העמוד
st.set_page_config(page_title="Market Confluence Dashboard", page_icon="📈", layout="wide")

MARKETS = {
    'Nikkei 225 (Asia)': '^N225',
    'Hang Seng (Asia)': '^HSI',
    'S&P 500 Futures (US)': 'ES=F',
    'Nasdaq 100 Futures (US)': 'NQ=F',
    'TA-35 (Israel)': 'TA35.TA'
}

def calculate_technical_indicators(df):
    if len(df) < 150:
        return df
    
    df['SMA_150'] = df['Close'].rolling(window=150).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    return df

@st.cache_data(ttl=900) # שמירת הנתונים במטמון ל-15 דקות כדי למנוע חסימות API
def get_market_snapshot():
    snapshot = {}
    for name, ticker in MARKETS.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            
            if df.empty:
                continue
                
            df = calculate_technical_indicators(df)
            last_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            pct_change = ((last_close - prev_close) / prev_close) * 100
            sma_150 = df['SMA_150'].iloc[-1]
            rsi_14 = df['RSI_14'].iloc[-1]
            
            snapshot[name] = {
                'Price': round(last_close, 2),
                '% Change': round(pct_change, 2),
                'RSI (14)': round(rsi_14, 2) if not pd.isna(rsi_14) else None,
                'SMA 150': round(sma_150, 2) if not pd.isna(sma_150) else None,
                'Above SMA 150': last_close > sma_150 if not pd.isna(sma_150) else None
            }
        except Exception as e:
            st.error(f"Error fetching data for {name}: {e}")
    return snapshot

def analyze_trend(market_data):
    """מנוע החלטות המנתח את הסנטימנט הגלובלי"""
    if not market_data:
        return "לא ניתן לנתח - חסרים נתונים", "yellow"
        
    asia_up = market_data.get('Nikkei 225 (Asia)', {}).get('% Change', 0) > 0 and \
              market_data.get('Hang Seng (Asia)', {}).get('% Change', 0) > 0
    us_futures_up = market_data.get('S&P 500 Futures (US)', {}).get('% Change', 0) > 0
    
    warnings = []
    
    # בדיקת מדדים טכניים ב-S&P 500 (הקטר המרכזי)
    sp500_data = market_data.get('S&P 500 Futures (US)', {})
    if sp500_data.get('RSI (14)', 50) > 70:
        warnings.append("⚠️ שוק אמריקאי מתקרב לטריטוריית קניית-יתר (RSI > 70).")
    if sp500_data.get('Above SMA 150') == False:
        warnings.append("⚠️ שוק אמריקאי מתחת לממוצע 150 יום - סיכון לתנודתיות שוק דובי.")

    if asia_up and us_futures_up:
        return "🟢 סנטימנט חיובי: התלכדות בין אסיה לחוזים בארה\"ב.", "green", warnings
    elif not asia_up and not us_futures_up:
        return "🔴 סנטימנט שלילי: התלכדות בין אסיה לחוזים בארה\"ב (מומנטום דובי).", "red", warnings
    elif us_futures_up and not asia_up:
        return "🟡 סנטימנט מעורב (נוטה חיובי): ארה\"ב ירוקה אך אסיה סגרה באדום.", "orange", warnings
    else:
        return "🟡 סנטימנט מעורב (נוטה שלילי): ארה\"ב אדומה למרות עליות באסיה.", "orange", warnings

# ממשק המשתמש (UI)
st.title("🌐 Global Market Confluence Dashboard")
st.markdown("כלי תומך החלטה לזיהוי מגמות שוק עוקבות (אסיה -> ישראל -> ארה\"ב)")

if st.button("רענן נתונים כעת 🔄"):
    get_market_snapshot.clear()

with st.spinner("מושך נתוני זמן אמת..."):
    market_data = get_market_snapshot()

if market_data:
    st.subheader("🎯 שורת המחץ (Market Bias)")
    trend_text, color, warnings = analyze_trend(market_data)
    st.markdown(f"<h3 style='color: {color};'>{trend_text}</h3>", unsafe_allow_html=True)
    
    for w in warnings:
        st.warning(w)

    st.markdown("---")
    st.subheader("📊 נתוני שווקים (זמן אמת / סוף יום)")
    
    # יצירת עמודות להצגת הנתונים כמו קלפים (Cards)
    cols = st.columns(len(market_data))
    
    for idx, (name, data) in enumerate(market_data.items()):
        with cols[idx]:
            st.markdown(f"**{name}**")
            # הבלטת אחוז השינוי בירוק או אדום
            pct_color = "green" if data['% Change'] > 0 else "red"
            st.markdown(f"<h2 style='color: {pct_color};'>{data['% Change']}%</h2>", unsafe_allow_html=True)
            st.write(f"מחיר: {data['Price']}")
            st.write(f"RSI (14): {data['RSI (14)']}")
            
            # תצוגה ויזואלית ל-SMA 150
            sma_status = "🟢 מעל" if data['Above SMA 150'] else "🔴 מתחת"
            st.write(f"מגמה ארוכה: {sma_status}")