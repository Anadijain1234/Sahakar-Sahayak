import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
API_URL = os.getenv("API_URL", "https://sahakar-sahayak-4.onrender.com//query")

if not BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is missing from your environment variables!")

print("🤖 Sahakar Sahayak Bot running with Interactive Menu...")
last_update_id = 0
user_languages = {}  # Map chat_id -> selected language code ('kn', 'en', 'hi')

def send_language_menu(chat_id):
    """Sends interactive inline buttons for language selection."""
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "🌾 ಕನ್ನಡ (Kannada)", "callback_data": "lang_kn"},
                {"text": "🇬🇧 English", "callback_data": "lang_en"}
            ],
            [
                {"text": "🇮🇳 हिंदी (Hindi)", "callback_data": "lang_hi"}
            ]
        ]
    }
    welcome_msg = (
        "🙏 **Welcome to Sahakar Sahayak / ಸಹಕಾರ ಸಹಾಯಕ್ ಗೆ ಸ್ವಾಗತ!**\n\n"
        "Please select your preferred language:\n"
        "ದಯವಿಟ್ಟು ನಿಮ್ಮ ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ:"
    )
    try:
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id, 
                "text": welcome_msg, 
                "parse_mode": "Markdown", 
                "reply_markup": keyboard
            },
            timeout=10
        )
    except Exception as e:
        print(f"Error sending language menu: {e}")

while True:
    try:
        updates_url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates?offset={last_update_id}&timeout=30"
        response = requests.get(updates_url, timeout=35).json()

        for result in response.get("result", []):
            last_update_id = result["update_id"] + 1

            # 1. Handle Interactive Button Clicks
            if "callback_query" in result:
                cb = result["callback_query"]
                chat_id = cb["message"]["chat"]["id"]
                data = cb["data"]
                cb_id = cb["id"]

                try:
                    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
                except Exception:
                    pass

                if data == "lang_kn":
                    user_languages[chat_id] = "kn"
                    reply = "✅ **ಭಾಷೆಯನ್ನು ಕನ್ನಡಕ್ಕೆ ಹೊಂದಿಸಲಾಗಿದೆ!**\nನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಕೇಳಿ (ಉದಾ: PM-KISAN ಯೋಜನೆಯ ಪ್ರಯೋಜನಗಳೇನು?)."
                elif data == "lang_en":
                    user_languages[chat_id] = "en"
                    reply = "✅ **Language set to English!**\nType your question (e.g., What are PM KISAN benefits?)."
                elif data == "lang_hi":
                    user_languages[chat_id] = "hi"
                    reply = "✅ **भाषा हिंदी सेट की गई है!**\nअपना प्रश्न पूछें (उदा: PM-KISAN के लाभ क्या हैं?)."
                else:
                    reply = "✅ Language updated!"

                try:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={"chat_id": chat_id, "text": reply, "parse_mode": "Markdown"},
                        timeout=10
                    )
                except Exception as e:
                    print(f"Error sending language response: {e}")
                continue

            # 2. Handle User Text Messages
            message = result.get("message", {})
            chat_id = message.get("chat", {}).get("id")
            user_text = message.get("text")

            if user_text and chat_id:
                if user_text.lower() in ["/start", "/language", "/lang"]:
                    send_language_menu(chat_id)
                    continue

                selected_lang = user_languages.get(chat_id, "kn")

                try:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendChatAction",
                        json={"chat_id": chat_id, "action": "typing"},
                        timeout=5
                    )
                except Exception:
                    pass

                rag_payload = {"query": user_text, "language": selected_lang}
                try:
                    rag_res = requests.post(API_URL, json=rag_payload, timeout=25).json()
                    answer = rag_res.get("answer", "No response generated.")
                except Exception as req_err:
                    answer = "⚠️ Could not connect to backend server / ಬ್ಯಾಕೆಂಡ್ ಸರ್ವರ್ ಸಂಪರ್ಕಿಸಲು ಸಾಧ್ಯವಾಗಿಲ್ಲ."
                    print(f"Error calling backend: {req_err}")

                try:
                    requests.post(
                        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                        json={"chat_id": chat_id, "text": answer},
                        timeout=10
                    )
                except Exception as e:
                    print(f"Error sending final message: {e}")

    except Exception as e:
        print(f"Connection error, retrying... ({e})")
        time.sleep(5)