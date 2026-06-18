import sqlite3

def init_db():
    """Создает базу данных и таблицы, если их нет"""
    conn = sqlite3.connect('database/users.db')
    cursor = conn.cursor()
    # Таблица пользователей: ID, имя и баланс монет
    cursor.execute('''CREATE TABLE IF NOT EXISTS users 
                      (id INTEGER PRIMARY KEY, name TEXT, coins INTEGER)''')
    conn.commit()
    conn.close()

def add_user(user_id, name):
    """Добавляет нового игрока в базу"""
    conn = sqlite3.connect('database/users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?, ?, ?)', (user_id, name, 0))
    conn.commit()
    conn.close()

def add_coins(user_id, amount):
    """Начисляет монеты пользователю за победу"""
    conn = sqlite3.connect('database/users.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET coins = coins + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def get_top_users():
    """Возвращает ТОП-10 игроков"""
    conn = sqlite3.connect('database/users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, coins FROM users ORDER BY coins DESC LIMIT 10')
    top = cursor.fetchall()
    conn.close()
    return top
