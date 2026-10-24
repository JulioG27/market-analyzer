import os
import requests
from market_analyzer import fetch_all_data, compute_confluence_score

# הדבק כאן את הקישור האישי של האפליקציה שלך ב-Streamlit Cloud
STREAMLIT_APP_URL = "https://market-analyzer.streamlit.app"  # החלף במידת הצורך בכתובת המדויקת שלך

def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("שגיאה: חסרים מפתחות גישה ל-Telegram (BOT_TOKEN / CHAT_ID)")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False  # מציג תצוגה מקדימה עדינה לקישור
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("ההתראה נשלחה בהצלחה ל-Telegram!")
    else:
        print(f"שגיאה בשליחת ההודעה: {response.text}")

def main():
    data = fetch_all_data()
    if not data:
        send_telegram_message("⚠️ לא ניתן היה למשוך נתוני שוק הבוקר.")
        return

    score, reasons = compute_confluence_score(data)
    
    status_icon = "🟢" if score >= 60 else ("🔴" if score <= 40 else "🟡")
    status_text = "שורי (Bullish)" if score >= 60 else ("דובי (Bearish)" if score <= 40 else "ניטרלי / מעורב")

    msg = f"*⚡ התרעת שוק יומית | Global Market Confluence*\n\n"
    msg += f"*ציון התלכדות:* `{score} / 100` {status_icon}\n"
    msg += f"*מצב שוק:* {status_text}\n\n"
    
    msg += "*גורמים מרכזיים:*\n"
    for r in reasons:
        msg += f"• {r}\n"
        
    msg += "\n*נתונים מהירים:*\n"
    sp = data.get('S&P 500 Futures (US)', {})
    vix = data.get('VIX (Fear Index)', {})
    usd = data.get('USD/ILS (Dollar/Shekel)', {})
    
    if sp: msg += f"• S&P 500 Futures: `{sp.get('% Change')}%` (RSI: `{sp.get('RSI')}`)\n"
    if vix: msg += f"• VIX (פחד): `{vix.get('Price')}` (`{vix.get('% Change')}%`)\n"
    if usd: msg += f"• דולר/שקל: `{usd.get('Price')}`\n"
    
    # הוספת הקישור הדינמי בתחתית ההודעה
    app_url = os.getenv("STREAMLIT_APP_URL", STREAMLIT_APP_URL)
    msg += f"\n🌐 [לחץ כאן לצפייה בדשבורד המלא והחי]({app_url})"
    
    send_telegram_message(msg)

if __name__ == "__main__":
    main()
