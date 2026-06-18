import telebot
from telebot import types
import config
import threading
import http.server
import socketserver
import os
from database.db_manager import init_db, add_user, add_coins

# --- СЕРВЕР ДЛЯ СДАЧИ WEB APP И ОТВЕТА RENDER ---
class MyHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): return # Отключаем лишние логи

def run_dummy_server():
    port = int(os.environ.get("PORT", 8000))
    with socketserver.TCPServer(("", port), MyHandler) as httpd:
        httpd.serve_forever()
threading.Thread(target=run_dummy_server, daemon=True).start()
# -----------------------------------------------

bot = telebot.TeleBot(config.TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id, message.from_user.first_name)
    
    # Твоя ссылка на приложение на Render
    WEB_APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-bot-ceua.onrender.com')}"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Создаем кнопку, которая открывает полноценное окно прямо внутри Telegram
    web_app_info = types.WebAppInfo(url=WEB_APP_URL)
    markup.add(types.KeyboardButton(text="🎮 Открыть Шашки", web_app=web_app_info))
    
    bot.send_message(message.chat.id, "Привет! Нажми на кнопку ниже, чтобы открыть настоящую игру:", reply_markup=markup)

# Слушаем, когда игра пришлет данные о победителе
@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    import json
    data = json.loads(message.web_app_data.data)
    winner = data.get("winner")
    
    if winner:
        bot.send_message(message.chat.id, f"🎉 Игра завершена! Вы отлично сыграли. Зачислено +10 монет.")
        add_coins(message.from_user.id, 10)

if __name__ == '__main__':
    init_db()
    bot.infinity_polling()
