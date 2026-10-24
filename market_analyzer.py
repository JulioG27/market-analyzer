import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# הגדרות עמוד
st.set_page_config(
    page_title="Global Market Confluence Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# עיצוב CSS ממוקד: RTL לכותרות וטקסטים בלבד (ללא שיבוש טבלאות)
st.markdown("""
<style>
    h1, h2, h3, h4, h5, h6, .stMarkdown, .stCaption {
        direction: rtl;
        text-align: right;
    }
    
    .score-card {
        background: linear-gradient(135deg, #1E1B4B 0%, #0F172A 100%);
        border: 2px solid #6366F1;
        border-radius: 16px;
        padding: 24px;
        text-align: center !important;
        box-shadow: 0 10px 25px -5px rgba(99, 102, 241, 0.3);
        margin-bottom: 25px;
        direction: rtl;
    }
    
    .action-badge {
        display: inline-block;
        padding: 10px 24px;
        border-radius: 30px;
        font-size: 1.5rem;
        font-weight: 800;
        margin-top: 15px;
    }
    
    .action-buy { background-color: rgba(16, 185, 129, 0.2); color: #10B981; border: 2px solid #10B981; }
    .action-wait { background-color: rgba(245, 158, 11, 0.2); color: #F59E0B; border: 2px solid #F59E0B; }
    .action-avoid { background-color: rgba(239, 68, 68, 0.2); color: #EF4444; border: 2px solid #EF4444; }
</style>
""", unsafe_allow_html=True)

# רשימת המדדים וה-ETFs העוקבות
MARKETS = {
    'S&P 500 Futures': {'ticker': 'ES=F', 'etf': 'SPY / VOO'},
    'Nasdaq 100 Futures': {'ticker': 'NQ=F', 'etf': 'QQQ'},
    'Nikkei 225': {'ticker': '^N225', 'etf': 'EWJ'},
    'Hang Seng': {'ticker': '^HSI', 'etf': 'EWH / FXI'},
    'TA-35': {'ticker': 'TA35.TA', 'etf': 'EIS / תכלית 35'}
}

COMMODITIES_CRYPTO = {
    'זהב (Gold)': {'ticker': 'GC=F', 'etf': 'GLD / IAU'},
    'נפט (Crude Oil)': {'ticker': 'CL=F', 'etf': 'USO'},
    'ביטקוין (Bitcoin)': {'ticker': 'BTC-USD', 'etf': 'IBIT / FBTC'}
}

MACRO_INDICATORS = {
    'VIX (מדד הפחד)': {'ticker': '^VIX', 'etf': 'VXX / UVXY'},
    'דולר / שקל': {'ticker': 'USDILS=X', 'etf': 'USD/ILS'}
}

def render_zoomed_chart(series, height=120):
    """ייצור גרף Plotly עם זום אוטומטי ואפשרות הגדלה למסך מלא"""
    if series.empty:
        return None
    
    y_min = series.min() * 0.995
    y_max = series.max() * 1.005
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=series.index, 
        y=series.values, 
        mode='lines',
        line=dict(color='#6366F1', width=2),
        hovertemplate='מחיר: %{y:,.2f}<extra></extra>'
    ))
    
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=10),
        height=height,
        xaxis=dict(visible=False),
        yaxis=dict(
            visible=True, 
            range=[y_min, y_max],
            tickfont=dict(size=10, color='#9CA3AF'),
            gridcolor='#1F2937',
            zeroline=False
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )
    return fig

def calculate_technical_indicators(df):
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
    all_assets = {**MARKETS, **COMMODITIES_CRYPTO, **MACRO_INDICATORS}
    
    for name, item in all_assets.items():
        ticker = item['ticker']
        etf = item['etf']
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
                'ETF': etf,
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
    score = 50
    reasons = []
    
    sp_change = data.get('S&P 500 Futures', {}).get('% Change', 0)
    nq_change = data.get('Nasdaq 100 Futures', {}).get('% Change', 0)
    us_avg = (sp_change + nq_change) / 2
    
    if us_avg > 0.5:
        score += 20
        reasons.append("🟢 חוזים עתידיים בארה\"ב מציגים עליות נאות.")
    elif us_avg < -0.5:
        score -= 20
        reasons.append("🔴 חוזים עתידיים בארה\"ב בירידות חדות.")
        
    nikkei = data.get('Nikkei 225', {}).get('% Change', 0)
    hangseng = data.get('Hang Seng', {}).get('% Change', 0)
    asia_avg = (nikkei + hangseng) / 2
    
    if asia_avg > 0.3:
        score += 15
        reasons.append("🟢 סגירה חיובית בשווקי אסיה.")
    elif asia_avg < -0.3:
        score -= 15
        reasons.append("🔴 סגירה שלילית בשווקי אסיה.")

    vix = data.get('VIX (מדד הפחד)', {}).get('Price', 15)
    if vix < 16:
        score += 10
        reasons.append("🟢 מדד VIX נמוך (סביבת מסחר רגועה).")
    elif vix > 22:
        score -= 15
        reasons.append("⚠️ מדד VIX גבוה (תנודתיות ורמת סיכון גבוהה בשוק).")

    sp_data = data.get('S&P 500 Futures', {})
    if sp_data.get('Price', 0) > sp_data.get('EMA_20', 1):
        score += 5
    if sp_data.get('Price', 0) > sp_data.get('SMA_150', 1):
        score += 5
    if sp_data.get('RSI', 50) > 70:
        reasons.append("⚠️ S&P 500 בטריטוריית קניית-יתר (RSI > 70).")

    final_score = max(0, min(100, score))
    
    if final_score >= 65:
        action_text = "🟢 להיכנס לשוק (איתות חיובי חזק)"
        action_class = "action-buy"
    elif final_score >= 40:
        action_text = "🟡 להמתין (סנטימנט מעורב / שוק לא החלטי)"
        action_class = "action-wait"
    else:
        action_text = "🔴 לא להיכנס (סיכון גבוה / מומנטום שלילי)"
        action_class = "action-avoid"
        
    return final_score, action_text, action_class, reasons

if __name__ == "__main__":
    st.title("⚡ Global Market Confluence Pro")
    st.markdown("מערכת ניתוח עוקבת לקבלת החלטות מסחר לפני פתיחת הבוקר")

    data = fetch_all_data()

    if data:
        score, action_text, action_class, reasons = compute_confluence_score(data)
        
        st.markdown(f"""
        <div class="score-card">
            <h3 style="margin:0; color:#A5B4FC;">ציון התלכדות שוק (Confluence Score)</h3>
            <h1 style="font-size: 3.5rem; margin:10px 0; color: {'#10B981' if score>=65 else ('#EF4444' if score<40 else '#F59E0B')};">
                {score} / 100
            </h1>
            <div>
                <span class="action-badge {action_class}">{action_text}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        tab1, tab2, tab3, tab4 = st.tabs([
            "📊 מדדים מרכזיים", 
            "🥇 סחורות וקריפטו", 
            "📈 ניתוח טכני מעמיק", 
            "🌐 מדדי מאקרו ו-VIX"
        ])
        
        with tab1:
            st.subheader("מצב המדדים הבינלאומיים")
            cols = st.columns(len(MARKETS))
            for idx, (name, _) in enumerate(MARKETS.items()):
                if name in data:
                    m = data[name]
                    with cols[idx]:
                        st.metric(label=name, value=f"{m['Price']}", delta=f"{m['% Change']}%")
                        st.caption(f"🎯 ETF: **{m['ETF']}**")
                        st.caption(f"RSI: {m['RSI']} | ATR: {m['ATR_PCT']}%")
                        fig = render_zoomed_chart(m['History'], height=110)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
            
            st.subheader("💡 גורמים משפיעים על הציון")
            for r in reasons:
                st.write(r)

        with tab2:
            st.subheader("נכסי מקלט, סחורות וקריפטו")
            c_cols = st.columns(len(COMMODITIES_CRYPTO))
            for idx, (name, _) in enumerate(COMMODITIES_CRYPTO.items()):
                if name in data:
                    m = data[name]
                    with c_cols[idx]:
                        st.metric(label=name, value=f"{m['Price']}", delta=f"{m['% Change']}%")
                        st.caption(f"🎯 ETF: **{m['ETF']}**")
                        st.caption(f"RSI: {m['RSI']} | ATR: {m['ATR_PCT']}%")
                        fig = render_zoomed_chart(m['History'], height=120)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})

        with tab3:
            st.subheader("תיאום מגמה ואינדיקטורים טכניים")
            tech_list = []
            all_assets = {**MARKETS, **COMMODITIES_CRYPTO}
            for name in all_assets.keys():
                if name in data:
                    m = data[name]
                    price = m['Price']
                    ema20 = m['EMA_20']
                    ema50 = m['EMA_50']
                    sma150 = m['SMA_150']
                    
                    if price and ema20 and ema50 and sma150:
                        trend = "🟢 שורי" if price > ema20 > ema50 > sma150 else ("🔴 דובי" if price < ema20 else "🟡 דשדוש")
                    else:
                        trend = "⚪ ללא נתונים"
                        
                    tech_list.append({
                        'Asset': name,
                        'ETF': m['ETF'],
                        'Price': price,
                        'Change %': f"{m['% Change']}%",
                        'RSI (14)': m['RSI'],
                        'ATR %': f"{m['ATR_PCT']}%",
                        'Trend': trend
                    })
            
            df_tech = pd.DataFrame(tech_list)
            
            st.dataframe(
                df_tech, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Asset": st.column_config.TextColumn("נכס", width="medium"),
                    "ETF": st.column_config.TextColumn("תעודת סל (ETF)", width="small"),
                    "Price": st.column_config.NumberColumn("מחיר ($)", format="%.2f"),
                    "Change %": st.column_config.TextColumn("שינוי יומי"),
                    "RSI (14)": st.column_config.NumberColumn("RSI (14)", format="%.1f"),
                    "ATR %": st.column_config.TextColumn("ATR (%)"),
                    "Trend": st.column_config.TextColumn("מבנה מגמה", width="medium")
                }
            )

        with tab4:
            st.subheader("מדדי סיכון ומט\"ח")
            m_cols = st.columns(2)
            for idx, (name, _) in enumerate(MACRO_INDICATORS.items()):
                if name in data:
                    m = data[name]
                    with m_cols[idx]:
                        st.metric(label=name, value=f"{m['Price']}", delta=f"{m['% Change']}%")
                        st.caption(f"🎯 ETF / Ticker: **{m['ETF']}**")
                        fig = render_zoomed_chart(m['History'], height=130)
                        if fig:
                            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
