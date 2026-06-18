import telebot
from telebot import types
import config
from database.db_manager import init_db, add_user, add_coins
from games.checkers_logic import create_board, is_valid_move, check_win, EMPTY_WHITE

bot = telebot.TeleBot(config.TOKEN)
active_games = {} # Храним игры в памяти: {chat_id: {board, turn, selected}}

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.from_user.id, message.from_user.first_name)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔴 Играть в Шашки"))
    bot.send_message(message.chat.id, "Привет! Готов к партии?", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == "🔴 Играть в Шашки")
def start_checkers(message):
    chat_id = message.chat.id
    active_games[chat_id] = {
        'board': create_board(),
        'turn': 'white',
        'selected': None # Координаты выбранной шашки (row, col)
    }
    bot.send_message(chat_id, "Игра началась! Ход Белых (⚪).\nНажми на шашку, чтобы выбрать её.", 
                     reply_markup=get_board_markup(chat_id))

def get_board_markup(chat_id):
    """Рисует доску из кнопок"""
    game = active_games[chat_id]
    board = game['board']
    markup = types.InlineKeyboardMarkup(row_width=8)
    buttons = []
    for r in range(8):
        for c in range(8):
            # Если клетка выбрана для хода, пометим её точкой
            text = board[r][c]
            if game['selected'] == (r, c):
                text = "✨"
            buttons.append(types.InlineKeyboardButton(text=text, callback_data=f"click_{r}_{c}"))
    markup.add(*buttons)
    return markup

@bot.callback_query_handler(func=lambda call: call.data.startswith("click_"))
def handle_click(call):
    chat_id = call.message.chat.id
    if chat_id not in active_games: return
    
    _, r, c = call.data.split("_")
    r, c = int(r), int(c)
    game = active_games[chat_id]
    
    # 1. Если еще ничего не выбрано — выбираем шашку
    if game['selected'] is None:
        if (game['turn'] == 'white' and game['board'][r][c] == "⚪") or \
           (game['turn'] == 'black' and game['board'][r][c] == "🔴"):
            game['selected'] = (r, c)
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_board_markup(chat_id))
        else:
            bot.answer_callback_query(call.id, "Сейчас не твой ход или клетка пустая!")
            
    # 2. Если шашка уже выбрана — делаем ход
    else:
        from_r, from_c = game['selected']
        
        # Если кликнули на ту же шашку — отменяем выбор
        if (from_r, from_c) == (r, c):
            game['selected'] = None
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=get_board_markup(chat_id))
            return
            
        # Проверяем правила хода
        if is_valid_move(game['board'], from_r, from_c, r, c, game['turn']):
            # Двигаем фигуру
            game['board'][r][c] = game['board'][from_r][from_c]
            game['board'][from_r][from_c] = "⬛"
            game['selected'] = None
            
            # Проверяем победу
            winner = check_win(game['board'])
            if winner:
                bot.send_message(chat_id, f"🎉 Победили {''Белые'' if winner == ''white'' else ''Черные''}! Вы получили 10 монет!")
                add_coins(call.from_user.id, 10) # Начисляем монеты в базу!
                del active_games[chat_id]
                return
                
            # Передаем ход
            game['turn'] = 'black' if game['turn'] == 'white' else 'white'
            turn_emoji = "⚪" if game['turn'] == 'white' else "🔴"
            
            bot.edit_message_text(f"Ход переходит к {turn_emoji}", chat_id, call.message.message_id, 
                                  reply_markup=get_board_markup(chat_id))
        else:
            bot.answer_callback_query(call.id, "Неверный ход!")

if __name__ == '__main__':
    init_db()
    bot.infinity_polling()
