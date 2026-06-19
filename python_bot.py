import telebot
from telebot import types
import config
import os
import threading
from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit, join_room, leave_room
from database.db_manager import init_db, add_user, add_coins, get_top_users, get_coins

# Инициализация бота и базы данных
bot = telebot.TeleBot(config.TOKEN)
init_db()

# Создаем веб-сервер Flask и сокеты
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

WEB_APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-bot-ceua.onrender.com')}"

# Структура для хранения активных комнат
# { room_id: { 'white': user_id, 'black': user_id, 'spectators': [] } }
GAME_ROOMS = {}
# Очередь игроков, которые ждут оппонента
MATCHMAKING_QUEUE = []

# Читаем HTML файл, чтобы Flask мог его раздавать игрокам
def get_html_content():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Файл index.html не найден на сервере!</h1>"

@app.route('/')
def index():
    """Раздаем наш index.html по главной ссылке"""
    return render_template_string(get_html_content())


# --- ЛОГИКА ТЕЛЕГРАМ БОТА ---

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id, message.from_user.first_name)
    user_coins = get_coins(message.from_user.id)
    
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🎮 Найти игру Онлайн"), types.KeyboardButton("🏆 Таблица лидеров"))
    
    bot.send_message(message.chat.id, 
                     f"Привет, {message.from_user.first_name}! 🪙 Твой баланс: {user_coins} монет.\n\n"
                     "Нажми на кнопку ниже, чтобы войти в режим поиска соперника по сети!", 
                     reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🎮 Найти игру Онлайн")
def find_match(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    user_coins = get_coins(user_id)
    
    # Кнопка запускает WebApp, передавая туда ID юзера и его имя
    markup = types.InlineKeyboardMarkup()
    url = f"{WEB_APP_URL}?user_id={user_id}&name={user_name}&coins={user_coins}"
    markup.add(types.InlineKeyboardButton("🚀 Войти на Арену", web_app=types.WebAppInfo(url=url)))
    
    bot.send_message(message.chat.id, "Нажми кнопку, чтобы запустить игровую сессию:", reply_markup=markup)

@bot.message_handler(commands=['top'])
@bot.message_handler(func=lambda message: message.text == "🏆 Таблица лидеров")
def top_leaderboard(message):
    top_players = get_top_users()
    if not top_players:
        bot.send_message(message.chat.id, "🏆 Таблица лидеров пока пуста.")
        return
    
    text = "🏆 **ТАБЛИЦА ЛИДЕРОВ:**\n\n"
    text += "`| №  | Имя          | Монеты  |`\n"
    text += "`|----|--------------|---------|`\n"
    
    for index, player in enumerate(top_players, 1):
        name, coins = player
        if len(name) > 12:
            name = name[:9] + "..."
        row = f"`| {index:<2} | {name:<12} | {coins:<7} |`"
        text += row + "\n"
        
    bot.send_message(message.chat.id, text, parse_mode="Markdown")


# --- ЛОГИКА ВЕБ-СОКЕТОВ (ОНЛАЙН ИГРА) ---

@socketio.on('join_arena')
def on_join_arena(data):
    """Игрок открыл WebApp и готов к подбору игры"""
    user_id = data.get('user_id')
    user_name = data.get('name')
    sid = request.sid # уникальный ID интернет-сессии игрока
    
    if not user_id:
        return

    # Проверяем, нет ли уже кого-то в очереди
    if MATCHMAKING_QUEUE and MATCHMAKING_QUEUE[0]['user_id'] != user_id:
        # Пару нашли! Создаем комнату
        opponent = MATCHMAKING_QUEUE.pop(0)
        room_id = f"room_{opponent['user_id']}_{user_id}"
        
        GAME_ROOMS[room_id] = {
            'white': {'id': opponent['user_id'], 'name': opponent['name'], 'sid': opponent['sid']},
            'black': {'id': user_id, 'name': user_name, 'sid': sid},
            'board': None # Состояние доски будем хранить позже
        }
        
        # Подключаем обоих в одну комнату веб-сокетов
        join_room(room_id)
        join_room(room_id, sid=opponent['sid'])
        
        # Оповещаем игроков о старте матча и распределяем цвета фигурок!
        emit('match_start', {'room_id': room_id, 'color': 'white', 'opponent': user_name}, room=opponent['sid'])
        emit('match_start', {'room_id': room_id, 'color': 'black', 'opponent': opponent['name']}, room=sid)
        print(f"🎮 Матч создан! {opponent['name']} против {user_name} в комнате {room_id}")
    else:
        # Если очередь пуста, добавляем игрока ждать
        # Удаляем старые сессии этого же юзера, если они были
        global MATCHMAKING_QUEUE
        MATCHMAKING_QUEUE = [x for x in MATCHMAKING_QUEUE if x['user_id'] != user_id]
        
        MATCHMAKING_QUEUE.append({'user_id': user_id, 'name': user_name, 'sid': sid})
        join_room(f"waiting_{user_id}")
        emit('waiting', {'message': 'Поиск соперника...'})

@socketio.on('make_move')
def on_make_move(data):
    """Один из игроков сделал ход. Пересылаем его оппоненту"""
    room_id = data.get('room_id')
    move_data = data.get('move') # Информация о том откуда и куда пошли
    
    if room_id in GAME_ROOMS:
        # Отправляем ход всем в этой комнате, кроме самого ходившего
        emit('opponent_moved', move_data, room=room_id, include_self=False)

@socketio.on('game_ended')
def on_game_ended(data):
    """Игра завершилась на клиенте"""
    room_id = data.get('room_id')
    winner_color = data.get('winner') # 'white' или 'black'
    
    if room_id in GAME_ROOMS:
        room = GAME_ROOMS[room_id]
        winner_data = room['white'] if winner_color == 'white' else room['black']
        
        # Начисляем монеты победителю в SQLite базу
        add_coins(winner_data['id'], 10)
        
        # Оповещаем чат бота
        try:
            bot.send_message(winner_data['id'], "🎉 Браво! Ты победил в сетевом матче и заработал +10 монет!")
        except Exception:
            pass
            
        # Удаляем комнату из памяти сервера
        leave_room(room_id)
        if room_id in GAME_ROOMS:
            del GAME_ROOMS[room_id]

@socketio.on('disconnect')
def on_disconnect():
    """Игрок закрыл вкладку или потерял сеть"""
    sid = request.sid
    # Удаляем из очереди поиска, если он там был
    global MATCHMAKING_QUEUE
    MATCHMAKING_QUEUE = [x for x in MATCHMAKING_QUEUE if x['sid'] != sid]
    
    # Если он был в игре, можно засчитать техническое поражение (сделаем в следующем шаге)


# Функция запуска Flask + Сокетов в отдельном потоке
def run_networks():
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)

threading.Thread(target=run_networks, daemon=True).start()

if __name__ == '__main__':
    print("🤖 Бот запускается...")
    bot.infinity_polling()
