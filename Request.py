import os
import requests
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# Telegram botunuzun token'ını alın
TOKEN = "6931338087:AAEJnBmJ3OQe3VsW91EiFBmO_uXMX9bJ8jM"
# Hedef botun token'ını alın
TARGET_BOT_TOKEN = os.environ.get("TARGET_BOT_TOKEN")

app = Flask(__name__)

@app.route('/start', methods=['POST'])
def start():
    update = Update.de_json(request.get_json(force=True), TOKEN)
    user_id = update.effective_user.id
    send_launch_button(user_id)
    return "ok"

def send_launch_button(user_id):
    keyboard = [
        [InlineKeyboardButton("Launch Bot", callback_data='launch_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    send_message(user_id, 'Bot başlatmak için butona tıklayın:', reply_markup)

def send_message(chat_id, text, reply_markup=None):
    url = "https://api.telegram.org/bot{}/sendMessage".format(TOKEN)
    params = {
        "chat_id": chat_id,
        "text": text,
        "reply_markup": reply_markup
    }
    response = requests.post(url, json=params)
    if response.status_code != 200:
        print("Mesaj gönderilemedi. Hata kodu:", response.status_code)

@app.route('/button_click', methods=['POST'])
def button_click():
    update = Update.de_json(request.get_json(force=True), TOKEN)
    query = update.callback_query
    if query.data == 'launch_bot':
        access_target_bot(query.from_user.id)
    return "ok"

def access_target_bot(user_id):
    url = "https://api.telegram.org/bot{}/sendMessage".format(TARGET_BOT_TOKEN)
    params = {
        "chat_id": user_id,
        "text": "Hedef botun ilgili kısmına erişim sağlandı."
    }
    response = requests.post(url, json=params)
    if response.status_code != 200:
        print("Mesaj gönderilemedi. Hata kodu:", response.status_code)

if __name__ == "__main__":
    PORT = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=PORT)
