# src/telegram_notifier.py
import requests

def send_telegram_message(message: str, bot_token: str, chat_id: str):
    api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': message,
        'parse_mode': 'Markdown'
    }
    try:
        response = requests.post(api_url, json=payload, timeout=10)
        response_json = response.json()
        if response.status_code == 200 and response_json.get("ok"):
            print("Messaggio Telegram inviato con successo!")
            return True
        else:
            print(f"Errore nell'invio del messaggio Telegram: {response_json}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Errore di connessione all'API di Telegram: {e}")
        return False
