import sqlite3

def init_db():
    conn = sqlite3.connect('database/users.db')
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, coins INTEGER)')
    conn.commit()
    conn.close()

def add_user(user_id, name):
    conn = sqlite3.connect('database/users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users VALUES (?, ?, ?)', (user_id, name, 0))
    conn.commit()
    conn.close()