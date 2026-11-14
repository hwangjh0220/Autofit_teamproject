import os
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")


def send_telegram_alert(message: str) -> dict:
    """Sends a formatted message to your Telegram chat."""
    if not TOKEN or not CHAT_ID:
        raise ValueError(
            "Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in .env!")

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    response = requests.post(url, json=payload)
    return response.json()


if __name__ == "__main__":
    print(send_telegram_alert("<b>Kodi Alert:</b> Module test successful!"))
