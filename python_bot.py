import telebot
import config
from database.db_manager import init_db, add_user

bot = telebot.TeleBot(config.TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id, message.from_user.first_name)
    bot.send_message(message.chat.id, "Бот готов к работе! База данных создана.")

if __name__ == '__main__':
    init_db()
    bot.infinity_polling()