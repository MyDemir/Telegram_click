from telegram.ext import Updater, CommandHandler

# Botunuzun token'ını buraya ekleyin
TOKEN = "6931338087:AAEJnBmJ3OQe3VsW91EiFBmO_uXMX9bJ8jM" #"YOUR_TELEGRAM_BOT_TOKEN"

# Botunuzun butonuna tıklandığında bu fonksiyonu çağırın
def start(update, context):
    click_function()  # Tıklama fonksiyonunu çağırın

def main():
    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # /start komutuna cevap vermek için bir CommandHandler ekleyin
    dispatcher.add_handler(CommandHandler("start", start))

    # Botu başlatın
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
    
