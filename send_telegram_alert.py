import os
import requests
from market_analyzer import fetch_all_data, compute_confluence_score

STREAMLIT_APP_URL = "https://market-analyzer-faefsahmujsbsqyreisjmi.streamlit.app"

def send_telegram_message(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    
    if not token or not chat_id:
        print("שגיאה: חסרים מפתחות גישה ל-Telegram")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    
    requests.post(url, json=payload)

def main():
    data = fetch_all_data()
    if not data:
        send_telegram_message("⚠️ לא ניתן היה למשוך נתוני שוק הבוקר.")
        return

    score, action_text, _, reasons = compute_confluence_score(data)

    msg = f"*⚡ התרעת שוק יומית | Global Market Confluence*\n\n"
    msg += f"*ציון התלכדות:* `{score} / 100`\n"
    msg += f"*המלצה אופרטיבית:* *{action_text}*\n\n"
    
    msg += "*גורמים מרכזיים:*\n"
    for r in reasons:
        msg += f"• {r}\n"
        
    msg += "\n*נתונים מהירים:*\n"
    sp = data.get('S&P 500 Futures (US)', {})
    vix = data.get('VIX (Fear Index)', {})
    gold = data.get('זהב (Gold)', {})
    btc = data.get('ביטקוין (Bitcoin)', {})
    
    if sp: msg += f"• S&P 500 Futures: `{sp.get('% Change')}%`\n"
    if vix: msg += f"• VIX (פחד): `{vix.get('Price')}`\n"
    if gold: msg += f"• זהב: `{gold.get('Price')}$` (`{gold.get('% Change')}%`)\n"
    if btc: msg += f"• ביטקוין: `{btc.get('Price')}$` (`{btc.get('% Change')}%`)\n"
    
    app_url = os.getenv("STREAMLIT_APP_URL", STREAMLIT_APP_URL)
    msg += f"\n🌐 [לחץ כאן לצפייה בדשבורד המלא והחי]({app_url})"
    
    send_telegram_message(msg)

if __name__ == "__main__":
    main()
