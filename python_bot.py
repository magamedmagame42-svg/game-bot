import telebot
from telebot import types
import config
import threading
import http.server
import socketserver
import os
from database.db_manager import init_db, add_user, add_coins, get_top_users

# --- СЕРВЕР ДЛЯ СДАЧИ WEB APP И ОТВЕТА RENDER ---
class MyHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): return

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
    
    WEB_APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-bot-ceua.onrender.com')}"
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    web_app_info = types.WebAppInfo(url=WEB_APP_URL)
    markup.add(types.KeyboardButton(text="🎮 Открыть Шашки", web_app=web_app_info))
    
    bot.send_message(message.chat.id, 
                     "Привет! Нажми на кнопку ниже, чтобы запустить игру.\n\n"
                     "📌 Доступные команды:\n"
                     "🏆 /top — Список лидеров по монетам", 
                     reply_markup=markup)

# Новая команда для вывода таблицы лидеров
@bot.message_handler(commands=['top'])
def top_leaderboard(message):
    top_players = get_top_users()
    if not top_players:
        bot.send_message(message.chat.id, "🏆 Таблица лидеров пока пуста. Будь первым!")
        return
        
    text = "🏆 **ТОП-10 ИГРОКОВ ПО МОНЕТАМ:**\n\n"
    for index, player in enumerate(top_players, 1):
        name, coins = player
        # Добавим красивые медали для топ-3
        medal = "🥇" if index == 1 else "🥈" if index == 2 else "🥉" if index == 3 else f"{index}."
        text += f"{medal} {name} — {coins} 🪙\n"
        
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    import json
    data = json.loads(message.web_app_data.data)
    winner = data.get("winner")
    
    if winner:
        bot.send_message(message.chat.id, "🎉 Игра завершена! Вы отлично сыграли. Баланс пополнен на +10 монет.")
        add_coins(message.from_user.id, 10)

if __name__ == '__main__':
    init_db()
    bot.infinity_polling()
