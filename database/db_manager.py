import firebase_admin
from firebase_admin import credentials, firestore

try:
    cred = credentials.Certificate("firebase-key.json")
    firebase_admin.initialize_app(cred)
except ValueError:
    pass

db = firestore.client()

def init_db():
    print("🔥 Облачная база данных Firestore успешно подключена!")

def add_user(user_id, name):
    """Добавляет нового игрока в глобальную базу"""
    user_ref = db.collection("users").document(str(user_id))
    doc = user_ref.get()
    
    if not doc.exists:
        user_ref.set({
            "name": name if name else "Игрок",
            "coins": 100  # Стартовый капитал
        })
    else:
        # Если игрок сменил имя в Telegram, обновляем его в базе топа
        user_ref.update({"name": name})

def add_coins(user_id, amount):
    """Изменение баланса монет игрока"""
    user_ref = db.collection("users").document(str(user_id))
    if user_ref.get().exists:
        user_ref.update({"coins": firestore.Increment(amount)})

def get_coins(user_id):
    user_ref = db.collection("users").document(str(user_id))
    doc = user_ref.get()
    if doc.exists:
        return doc.to_dict().get("coins", 0)
    return 0

def get_top_users():
    """Вытягивает ТОП-10 игроков со всего облака для команды /top"""
    users_ref = db.collection("users")
    query = users_ref.order_by("coins", direction=firestore.Query.DESCENDING).limit(10)
    docs = query.stream()
    
    top = []
    for doc in docs:
        data = doc.to_dict()
        top.append((data.get("name", "Аноним"), data.get("coins", 0)))
    return top
