import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

MARKETS = {
    'S&P 500 Futures (US)': 'ES=F',
    'Nasdaq 100 Futures (US)': 'NQ=F',
    'Nikkei 225 (Asia)': '^N225',
    'Hang Seng (Asia)': '^HSI',
    'TA-35 (Israel)': 'TA35.TA'
}

MACRO_INDICATORS = {
    'VIX (Fear Index)': '^VIX',
    'USD/ILS (Dollar/Shekel)': 'USDILS=X'
}

def calculate_technical_indicators(df):
    """חישוב מורחב: EMA20, EMA50, SMA150, RSI, ATR, MACD"""
    if len(df) < 150:
        return df
    
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    df['SMA_150'] = df['Close'].rolling(window=150).mean()
    
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI_14'] = 100 - (100 / (1 + rs))
    
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR_14'] = tr.rolling(window=14).mean()
    df['ATR_PCT'] = (df['ATR_14'] / df['Close']) * 100

    ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
    ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema_12 - ema_26
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    return df

@st.cache_data(ttl=900)
def fetch_all_data():
    data = {}
    all_tickers = {**MARKETS, **MACRO_INDICATORS}
    
    for name, ticker in all_tickers.items():
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y")
            if df.empty:
                continue
                
            df = calculate_technical_indicators(df)
            last_close = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            pct_change = ((last_close - prev_close) / prev_close) * 100
            
            data[name] = {
                'Price': round(last_close, 2),
                '% Change': round(pct_change, 2),
                'RSI': round(df['RSI_14'].iloc[-1], 1) if 'RSI_14' in df else None,
                'EMA_20': round(df['EMA_20'].iloc[-1], 2) if 'EMA_20' in df else None,
                'EMA_50': round(df['EMA_50'].iloc[-1], 2) if 'EMA_50' in df else None,
                'SMA_150': round(df['SMA_150'].iloc[-1], 2) if 'SMA_150' in df else None,
                'ATR_PCT': round(df['ATR_PCT'].iloc[-1], 2) if 'ATR_PCT' in df else None,
                'MACD_Hist': round(df['MACD_Hist'].iloc[-1], 2) if 'MACD_Hist' in df else None,
                'History': df['Close'].tail(60)
            }
        except Exception as e:
            print(f"Error fetching {name}: {e}")
    return data

def compute_confluence_score(data):
    """מנוע חישוב ציון התלכדות 0-100"""
    score = 50
    reasons = []
    
    sp_change = data.get('S&P 500 Futures (US)', {}).get('% Change', 0)
    nq_change = data.get('Nasdaq 100 Futures (US)', {}).get('% Change', 0)
    us_avg = (sp_change + nq_change) / 2
    
    if us_avg > 0.5:
        score += 20
        reasons.append("🟢 חוזים בארה\"ב מציגים עליות נאות.")
    elif us_avg < -0.5:
        score -= 20
        reasons.append("🔴 חוזים בארה\"ב בירידות חדות.")
        
    nikkei = data.get('Nikkei 225 (Asia)', {}).get('% Change', 0)
    hangseng = data.get('Hang Seng (Asia)', {}).get('% Change', 0)
    asia_avg = (nikkei + hangseng) / 2
    
    if asia_avg > 0.3:
        score += 15
        reasons.append("🟢 סגירה חיובית בשווקי אסיה.")
    elif asia_avg < -0.3:
        score -= 15
        reasons.append("🔴 סגירה שלילית באסיה.")

    vix = data.get('VIX (Fear Index)', {}).get('Price', 15)
    if vix < 16:
        score += 10
        reasons.append("🟢 מדד VIX נמוך (רגיעה בשווקים).")
    elif vix > 22:
        score -= 15
        reasons.append("⚠️ מדד VIX גבוה (תנודתיות ופחד בשוק).")

    sp_data = data.get('S&P 500 Futures (US)', {})
    if sp_data.get('Price', 0) > sp_data.get('EMA_20', 1):
        score += 5
    if sp_data.get('Price', 0) > sp_data.get('SMA_150', 1):
        score += 5
    if sp_data.get('RSI', 50) > 70:
        reasons.append("⚠️ S&P 500 בקניית יתר (RSI > 70).")
        
    return max(0, min(100, score)), reasons

# --- הרצת ממשק Streamlit בלבד (לא מופעל בעת import לטלגרם) ---
if __name__ == "__main__":
    st.set_page_config(
        page_title="Global Market Confluence Pro",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="collapsed"
    )

    st.markdown("""
    <style>
        .stApp { background-color: #0A0E17; color: #E2E8F0; }
        .score-card {
            background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%);
            border: 2px solid #6366F1;
            border-radius: 16px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.3);
            margin-bottom: 25px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("⚡ Global Market Confluence Pro")
    st.markdown("מערכת ניתוח עוקבת לקבלת החלטות מסחר לפני פתיחת הבוקר")

    data = fetch_all_data()

    if data:
        score, reasons = compute_confluence_score(data)
        
        st.markdown(f"""
        <div class="score-card">
            <h3 style="margin:0; color:#A5B4FC;">ציון התלכדות שוק (Confluence Score)</h3>
            <h1 style="font-size: 3.5rem; margin:10px 0; color: {'#10B981' if score>=60 else ('#EF4444' if score<=40 else '#F59E0B')};">
                {score} / 100
            </h1>
            <h4>סטטוס: {'🟢 שורי (Bullish Bias)' if score>=60 else ('🔴 דובי (Bearish Bias)' if score<=40 else '🟡 ניטרלי / מעורב')}</h4>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3 = st.tabs(["📊 תמונת מצב מהירה", "📈 ניתוח טכני מעמיק", "🌐 מדדי מאקרו ו-VIX"])
        
        with tab1:
            st.subheader("מצב המדדים המרכזיים")
            cols = st.columns(len(MARKETS))
            for idx, (name, ticker_data) in enumerate(MARKETS.items()):
                if name in data:
                    m = data[name]
                    with cols[idx]:
                        st.metric(label=name, value=f"{m['Price']}", delta=f"{m['% Change']}%")
                        st.caption(f"RSI: {m['RSI']} | ATR: {m['ATR_PCT']}%")
                        st.line_chart(m['History'], height=80)
            
            st.subheader("💡 ניתוח גורמים משפיעים")
            for r in reasons:
                st.write(r)

        with tab2:
            st.subheader("תיאום מגמה ואינדיקטורים מתקדמים")
            tech_list = []
            for name in MARKETS.keys():
                if name in data:
                    m = data[name]
                    price = m['Price']
                    ema20 = m['EMA_20']
                    ema50 = m['EMA_50']
                    sma150 = m['SMA_150']
                    
                    if price and ema20 and ema50 and sma150:
                        trend = "🟢 שורי חזק" if price > ema20 > ema50 > sma150 else ("🔴 דובי" if price < ema20 else "🟡 דשדוש")
                    else:
                        trend = "ללא נתונים"
                        
                    tech_list.append({
                        'מדד': name,
                        'מחיר': price,
                        'שינוי %': f"{m['% Change']}%",
                        'RSI (14)': m['RSI'],
                        'ATR % (תנודתיות)': f"{m['ATR_PCT']}%",
                        'MACD Hist': m['MACD_Hist'],
                        'מבנה מגמה': trend
                    })
            st.dataframe(pd.DataFrame(tech_list), use_container_width=True)

        with tab3:
            st.subheader("מדדי סיכון ומט\"ח")
            m_cols = st.columns(2)
            for idx, (name, ticker_data) in enumerate(MACRO_INDICATORS.items()):
                if name in data:
                    m = data[name]
                    with m_cols[idx]:
                        st.metric(label=name, value=f"{m['Price']}", delta=f"{m['% Change']}%")
                        st.line_chart(m['History'], height=120)
