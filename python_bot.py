import telebot
from telebot import types
import config
import threading
import http.server
import socketserver
import os
from database.db_manager import init_db, add_user, add_coins, get_top_users, get_coins

class MyHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format, *args): return

def run_dummy_server():
    port = int(os.environ.get("PORT", 8000))
    with socketserver.TCPServer(("", port), MyHandler) as httpd:
        httpd.serve_forever()
threading.Thread(target=run_dummy_server, daemon=True).start()

bot = telebot.TeleBot(config.TOKEN)
WEB_APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-bot-ceua.onrender.com')}"

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id, message.from_user.first_name)
    user_coins = get_coins(message.from_user.id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("⚡ Быстрая игра (15 мин)"), types.KeyboardButton("⏳ Долгая партия (45 мин)"))
    markup.add(types.KeyboardButton("⚙️ Свое время партии"))
    
    bot.send_message(message.chat.id, 
                     f"Привет, {message.from_user.first_name}! 🪙 Твой баланс: {user_coins} монет.\n\n"
                     "Выбери режим времени для игры в шашки или используй команды:\n"
                     "🏆 /top — Список лидеров по монетам", 
                     reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "⚡ Быстрая игра (15 мин)")
def fast_game(message):
    user_coins = get_coins(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🚀 Запустить (15 мин)", web_app=types.WebAppInfo(url=f"{WEB_APP_URL}?time=15&coins={user_coins}")))
    bot.send_message(message.chat.id, "Кнопка для быстрого матча готова:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "⏳ Долгая партия (45 мин)")
def long_game(message):
    user_coins = get_coins(message.from_user.id)
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🧠 Запустить (45 мин)", web_app=types.WebAppInfo(url=f"{WEB_APP_URL}?time=45&coins={user_coins}")))
    bot.send_message(message.chat.id, "Кнопка для вдумчивой долгой партии готова:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "⚙️ Свое время партии")
def custom_time_request(message):
    msg = bot.send_message(message.chat.id, "Напиши числом, сколько минут должна длиться партия? (Например: 20 или 60)")
    bot.register_next_step_handler(msg, custom_time_process)

def custom_time_process(message):
    try:
        minutes = int(message.text)
        if minutes < 1 or minutes > 180:
            bot.send_message(message.chat.id, "Пожалуйста, введи разумное время от 1 до 180 минут.")
            return
        user_coins = get_coins(message.from_user.id)
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(f"🎮 Играть ({minutes} мин)", web_app=types.WebAppInfo(url=f"{WEB_APP_URL}?time={minutes}&coins={user_coins}")))
        bot.send_message(message.chat.id, f"Установлено время: {minutes} мин. Твоя ссылка:", reply_markup=markup)
    except ValueError:
        bot.send_message(message.chat.id, "Ошибка! Нужно отправить только целое число минут. Попробуй еще раз через меню.")

@bot.message_handler(commands=['top'])
def top_leaderboard(message):
    top_players = get_top_users()
    if not top_players:
        bot.send_message(message.chat.id, "🏆 Таблица лидеров пока пуста.")
        return
    
    # Заголовок таблицы
    text = "🏆 **ТАБЛИЦА ЛИДЕРОВ:**\n\n"
    text += "`| №  | Имя          | Монеты  |`\n"
    text += "`|----|--------------|---------|`\n"
    
    for index, player in enumerate(top_players, 1):
        name, coins = player
        
        # Обрезаем слишком длинные имена до 12 символов, чтобы таблица не ломалась
        if len(name) > 12:
            name = name[:9] + "..."
            
        # Форматируем строки с фиксированной шириной колонок
        # {:<2} - под номер (2 символа, выравнивание по левому краю)
        # {:<12} - под имя (12 символов)
        # {:<7} - под монеты (7 символов)
        row = f"`| {index:<2} | {name:<12} | {coins:<7} |`"
        text += row + "\n"
        
    bot.send_message(message.chat.id, text, parse_mode="Markdown")

@bot.message_handler(content_types=['web_app_data'])
def web_app_data_handler(message):
    import json
    data = json.loads(message.web_app_data.data)
    if data.get("winner"):
        bot.send_message(message.chat.id, "🎉 Игра завершена! Победа зафиксирована. Начислено +10 монет.")
        add_coins(message.from_user.id, 10)

if __name__ == '__main__':
    init_db()
    bot.infinity_polling()
