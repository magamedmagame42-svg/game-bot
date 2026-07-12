import telebot
from telebot import types
import config
import os
import threading
from flask import Flask, request, render_template_string
from flask_socketio import SocketIO, emit, join_room, leave_room
from database.db_manager import init_db, add_user, add_coins, get_top_users, get_coins

# Импортируем серверную валидацию шашек из нашей папки games
from games.checkers_logic import create_board, check_move_validity, can_capture

# Инициализация бота и базы данных
bot = telebot.TeleBot(config.TOKEN)
init_db()

# Создаем веб-сервер Flask и сокеты
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

WEB_APP_URL = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'game-bot-ceua.onrender.com')}"

# Структура для хранения активных комнат
GAME_ROOMS = {}
# Очередь игроков, которые ждут оппонента
MATCHMAKING_QUEUE = []

def get_html_content():
    try:
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>Файл index.html не найден на сервере!</h1>"

@app.route('/')
def index():
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


# --- ЛОГИКА ВЕБ-СОКЕТОВ (ОНЛАЙН ИГРА С СЕРВЕРНОЙ ВАЛИДАЦИЕЙ) ---

@socketio.on('join_arena')
def on_join_arena(data):
    """Игрок открыл WebApp и готов к подбору игры"""
    global MATCHMAKING_QUEUE
    
    user_id = data.get('user_id')
    user_name = data.get('name')
    sid = request.sid
    
    if not user_id:
        return

    # Проверяем, нет ли уже кого-то в очереди
    if MATCHMAKING_QUEUE and MATCHMAKING_QUEUE[0]['user_id'] != user_id:
        opponent = MATCHMAKING_QUEUE.pop(0)
        room_id = f"room_{opponent['user_id']}_{user_id}"
        
        # Генерируем чистую доску на стороне сервера
        server_board = create_board()
        
        GAME_ROOMS[room_id] = {
            'white': {'id': opponent['user_id'], 'name': opponent['name'], 'sid': opponent['sid']},
            'black': {'id': user_id, 'name': user_name, 'sid': sid},
            'board': server_board,
            'turn': 'white'  # Начинают всегда белые
        }
        
        join_room(room_id)
        join_room(room_id, sid=opponent['sid'])
        
        emit('match_start', {'room_id': room_id, 'color': 'white', 'opponent': user_name}, room=opponent['sid'])
        emit('match_start', {'room_id': room_id, 'color': 'black', 'opponent': opponent['name']}, room=sid)
        print(f"🎮 Матч создан! {opponent['name']} против {user_name} в комнате {room_id}")
    else:
        # Очищаем старые зависшие сессии этого же юзера, если они были
        MATCHMAKING_QUEUE = [x for x in MATCHMAKING_QUEUE if x['user_id'] != user_id]
        
        MATCHMAKING_QUEUE.append({'user_id': user_id, 'name': user_name, 'sid': sid})
        emit('waiting', {'message': 'Поиск соперника...'})

@socketio.on('make_move')
def on_make_move(data):
    """Серверная проверка и пересылка хода"""
    room_id = data.get('room_id')
    move = data.get('move')  # {fromR, fromC, toR, toC}
    
    if room_id not in GAME_ROOMS:
        return
        
    room = GAME_ROOMS[room_id]
    board = room['board']
    current_turn = room['turn']
    
    # 1. Безопасность: Проверяем, что ходит игрок, чья сейчас очередь
    sender_sid = request.sid
    expected_sid = room['white']['sid'] if current_turn == 'white' else room['black']['sid']
    if sender_sid != expected_sid:
        return  # Не его ход! Чит-запрос отклонен

    from_r, from_c = move['fromR'], move['fromC']
    to_r, to_c = move['toR'], move['toC']

    # 2. Безопасность: Проверяем ход по правилам шашек на сервере
    is_valid, is_hit, enemy_r, enemy_c = check_move_validity(board, current_turn, from_r, from_c, to_r, to_c)

    if is_valid:
        # Переносим фигуру на сервере
        piece = board[from_r][from_c]
        board[to_r][to_c] = piece
        board[from_r][from_c] = {'type': '', 'isKing': False}
        
        # Если было взятие, удаляем побитую шашку
        if is_hit and enemy_r is not None:
            board[enemy_r][enemy_c] = {'type': '', 'isKing': False}

        # Превращение в дамку на сервере
        if board[to_r][to_c]['type'] == 'W' and to_r == 0:
            board[to_r][to_c]['isKing'] = True
        if board[to_r][to_c]['type'] == 'B' and to_r == 7:
            board[to_r][to_c]['isKing'] = True

        # Проверяем, может ли эта же фигура бить дальше (мульти-взятие)
        if is_hit and can_capture(board, to_r, to_c):
            # Оставляем ход за тем же игроком
            pass
        else:
            # Меняем ход на оппонента
            room['turn'] = 'black' if current_turn == 'white' else 'white'

        # Отправляем подтвержденный и чистый ход обоим клиентам
        verified_move_payload = {
            'fromR': from_r, 'fromC': from_c,
            'toR': to_r, 'toC': to_c,
            'isHit': is_hit, 'enemyR': enemy_r, 'enemyC': enemy_c,
            'nextTurn': room['turn']
        }
        emit('opponent_moved', verified_move_payload, room=room_id)

@socketio.on('game_ended')
def on_game_ended(data):
    """Игра завершилась"""
    room_id = data.get('room_id')
    winner_color = data.get('winner')
    
    if room_id in GAME_ROOMS:
        room = GAME_ROOMS[room_id]
        winner_data = room['white'] if winner_color == 'white' else room['black']
        
        add_coins(winner_data['id'], 10)
        
        try:
            bot.send_message(winner_data['id'], "🎉 Браво! Ты победил в сетевом матче и заработал +10 монет!")
        except Exception:
            pass
            
        leave_room(room_id)
        if room_id in GAME_ROOMS:
            del GAME_ROOMS[room_id]

@socketio.on('disconnect')
def on_disconnect():
    """Игрок закрыл вкладку или потерял сеть"""
    global MATCHMAKING_QUEUE
    sid = request.sid
    MATCHMAKING_QUEUE = [x for x in MATCHMAKING_QUEUE if x['sid'] != sid]


def run_networks():
    port = int(os.environ.get("PORT", 8000))
    socketio.run(app, host="0.0.0.0", port=port, allow_unsafe_werkzeug=True)

threading.Thread(target=run_networks, daemon=True).start()

if __name__ == '__main__':
    print("🤖 Бот запускается...")
    bot.infinity_polling()
