import telebot
from telebot import types
import config
import threading
import http.server
import socketserver
import os
from database.db_manager import init_db, add_user, add_coins
from games.checkers_logic import create_board, is_valid_move, check_win

# --- ФОНОВЫЙ СЕРВЕР ДЛЯ RENDER ---
def run_dummy_server():
    handler = http.server.SimpleHTTPRequestHandler
    port = int(os.environ.get("PORT", 8000))
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_dummy_server, daemon=True).start()
# ---------------------------------

bot = telebot.TeleBot(config.TOKEN)
active_games = {} # Хранилище игр: {chat_id: {board, turn, selected}}

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id, message.from_user.first_name)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔴 Играть в Шашки"))
    bot.send_message(message.chat.id, "Привет! Рад тебя видеть. Начнем игру?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔴 Играть в Шашки")
def start_checkers(message):
    chat_id = message.chat.id
    active_games[chat_id] = {
        'board': create_board(),
        'turn': 'white',
        'selected': None # Сюда сохраняем координаты выбранной шашки (row, col)
    }
    bot.send_message(chat_id, "Игра началась! Твой ход Белыми (⚪).\nНажми на шашку, чтобы выбрать её.", 
                     reply_markup=get_board_markup(chat_id))

def get_board_markup(chat_id):
    """Генерирует доску 8х8 из кнопок"""
    game = active_games[chat_id]
    board = game['board']
    markup = types.InlineKeyboardMarkup(row_width=8)
    buttons = []
    for r in range(8):
        for c in range(8):
            text = board[r][c]
            # Если игрок кликнул на шашку, подсветим её звездочками
            if game['selected'] == (r, c):
                text = "✨"
            buttons.append(types.InlineKeyboardButton(text=text, callback_data=f"click_{r}_{c}"))
    markup.add(*buttons)
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("click_"))
def handle_click(call):
    chat_id = call.message.chat.id
    if chat_id not in active_games: 
        return
    
    _, r, c = call.data.split("_")
    r, c = int(r), int(c)
    game = active_games[chat_id]
    
    # 1. ШАГ: Если шашка еще не выбрана
    if game['selected'] is None:
        if (game['turn'] == 'white' and game['board'][r][c] == "⚪") or \
           (game['turn'] == 'black' and game['board'][r][c] == "🔴"):
            game['selected'] = (r, c)
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_board_markup(chat_id))
        else:
            bot.answer_callback_query(call.id, "Сейчас не твой ход или клетка пустая!")
            
    # 2. ШАГ: Шашка уже выбрана, игрок делает ход
    else:
        from_r, from_c = game['selected']
        
        # Если кликнули на ту же самую шашку — отменяем выделение
        if (from_r, from_c) == (r, c):
            game['selected'] = None
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_board_markup(chat_id))
            return
            
        # Проверяем ход по правилам из checkers_logic.py
        is_allowed, is_capture = is_valid_move(game['board'], from_r, from_c, r, c, game['turn'])
        
        if is_allowed:
            # Если это прыжок через фигуру (взятие) — удаляем съеденную шашку соперника
            if is_capture:
                mid_r = (from_r + r) // 2
                mid_c = (from_c + c) // 2
                game['board'][mid_r][mid_c] = "⬛"
                
            # Перемещаем нашу шашку на новую позицию
            game['board'][r][c] = game['board'][from_r][from_c]
            game['board'][from_r][from_c] = "⬛"
            game['selected'] = None # Сбрасываем выделение
            
            # Проверяем, победил ли кто-то
            winner = check_win(game['board'])
            if winner:
                bot.send_message(chat_id, f"🎉 Победили {'Белые' if winner == 'white' else 'Черные'}! Зачислено +10 монет.")
                add_coins(call.from_user.id, 10) # Начисляем награду в БД
                del active_games[chat_id] # Удаляем завершенную сессию игры
                return
                
            # Меняем ход партии
            game['turn'] = 'black' if game['turn'] == 'white' else 'white'
            turn_emoji = "⚪" if game['turn'] == 'white' else "🔴"
            
            bot.edit_message_text(f"Ход переходит к {turn_emoji}", chat_id, call.message.message_id, 
                                  reply_markup=get_board_markup(chat_id))
        else:
            bot.answer_callback_query(call.id, "Неверный ход! Ходить можно только по диагонали.")

if __name__ == '__main__':
    init_db()
    print("Игровой бот успешно запущен...")
    bot.infinity_polling()
