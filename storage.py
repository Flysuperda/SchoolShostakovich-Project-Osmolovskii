import json
import os
from config import USERS_FILE


def ensure_users_file():
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, "w", encoding="utf-8") as file:
            json.dump({}, file, ensure_ascii=False, indent=4)


def load_users():
    ensure_users_file()
    with open(USERS_FILE, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return {}


def save_users(users_data):
    with open(USERS_FILE, "w", encoding="utf-8") as file:
        json.dump(users_data, file, ensure_ascii=False, indent=4)


def save_user_class(chat_id, class_name):
    users = load_users()
    users[str(chat_id)] = {
        "class_name": class_name
    }
    save_users(users)


def get_user_class(chat_id):
    users = load_users()
    user_data = users.get(str(chat_id))
    if not user_data:
        return None
    return user_data.get("class_name")


def get_all_users():
    return load_users()