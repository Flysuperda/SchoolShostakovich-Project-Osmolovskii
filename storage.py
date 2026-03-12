import json
import os
from config import USERS_FILE, SETTINGS_FILE, DEFAULT_SEND_TIME


def ensure_file_exists(file_path, default_data):
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(default_data, file, ensure_ascii=False, indent=4)


def load_json(file_path, default_data):
    ensure_file_exists(file_path, default_data)

    with open(file_path, "r", encoding="utf-8") as file:
        try:
            return json.load(file)
        except json.JSONDecodeError:
            return default_data.copy() if isinstance(default_data, dict) else default_data


def save_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


# ---------------- USERS ----------------

def ensure_users_file():
    ensure_file_exists(USERS_FILE, {})


def load_users():
    return load_json(USERS_FILE, {})


def save_users(users_data):
    save_json(USERS_FILE, users_data)


def ensure_user_exists(chat_id):
    users = load_users()
    chat_id_str = str(chat_id)

    if chat_id_str not in users:
        users[chat_id_str] = {
            "class_name": None,
            "notification_time": None,
            "last_sent_date": None
        }
        save_users(users)

    return users


def save_user_class(chat_id, class_name):
    users = ensure_user_exists(chat_id)
    users[str(chat_id)]["class_name"] = class_name
    save_users(users)


def get_user_class(chat_id):
    users = load_users()
    user_data = users.get(str(chat_id))
    if not user_data:
        return None
    return user_data.get("class_name")


def save_user_notification_time(chat_id, notification_time):
    users = ensure_user_exists(chat_id)
    users[str(chat_id)]["notification_time"] = notification_time
    save_users(users)


def get_user_notification_time(chat_id):
    users = load_users()
    user_data = users.get(str(chat_id))
    if not user_data:
        return None
    return user_data.get("notification_time")


def update_user_last_sent_date(chat_id, sent_date):
    users = ensure_user_exists(chat_id)
    users[str(chat_id)]["last_sent_date"] = sent_date
    save_users(users)


def get_user_last_sent_date(chat_id):
    users = load_users()
    user_data = users.get(str(chat_id))
    if not user_data:
        return None
    return user_data.get("last_sent_date")


def get_user_data(chat_id):
    users = load_users()
    return users.get(str(chat_id))


def get_all_users():
    return load_users()


# ---------------- SETTINGS ----------------

def ensure_settings_file():
    ensure_file_exists(SETTINGS_FILE, {
        "default_send_time": DEFAULT_SEND_TIME
    })


def load_settings():
    return load_json(SETTINGS_FILE, {
        "default_send_time": DEFAULT_SEND_TIME
    })


def save_settings(settings_data):
    save_json(SETTINGS_FILE, settings_data)


def get_default_send_time():
    settings = load_settings()
    return settings.get("default_send_time", DEFAULT_SEND_TIME)


def set_default_send_time(send_time):
    settings = load_settings()
    settings["default_send_time"] = send_time
    save_settings(settings)