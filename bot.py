import sys
import threading
import time
from datetime import datetime

import telebot
from telebot import types

from config import TOKEN, ADMIN_IDS, AVAILABLE_CLASSES, CHECK_INTERVAL_SECONDS
from storage import (
    save_user_class,
    get_user_class,
    get_all_users,
    save_user_notification_time,
    get_user_notification_time,
    update_user_last_sent_date,
    get_user_last_sent_date,
    get_user_data,
    get_default_send_time,
    set_default_send_time,
)
from schedule_utils import (
    get_schedule_path,
    is_weekend,
    get_current_date_string,
    get_current_time_string,
    is_valid_time_format,
    normalize_time_string,
    weekday_name_to_russian,
    get_today_weekday_name,
)

bot = telebot.TeleBot(TOKEN)

stop_event = threading.Event()
bot_started_at = datetime.now()


# ---------------- KEYBOARDS ----------------

def create_classes_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [types.KeyboardButton(class_name) for class_name in AVAILABLE_CLASSES]
    markup.add(*buttons)
    return markup


def create_main_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📅 Моё расписание"),
        types.KeyboardButton("🕒 Время уведомления"),
        types.KeyboardButton("🎓 Сменить класс"),
        types.KeyboardButton("👤 Мой профиль"),
    )
    return markup


def create_admin_menu_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("📊 Админ: статистика"),
        types.KeyboardButton("🚀 Админ: рассылка"),
        types.KeyboardButton("⏰ Админ: время"),
    )
    markup.add(types.KeyboardButton("🔙 Обычное меню"))
    return markup


# ---------------- HELPERS ----------------

def is_admin(user_id):
    return user_id in ADMIN_IDS


def get_user_effective_time(chat_id):
    user_time = get_user_notification_time(chat_id)
    if user_time:
        return user_time
    return get_default_send_time()


def format_user_profile(chat_id):
    user_data = get_user_data(chat_id)

    if not user_data:
        return (
            "Профиль пока пустой.\n"
            "Выбери класс через /start."
        )

    class_name = user_data.get("class_name") or "не выбран"
    personal_time = user_data.get("notification_time")
    effective_time = get_user_effective_time(chat_id)

    return (
        f"Твой класс: {class_name}\n"
        f"Личное время уведомления: {personal_time or 'не задано'}\n"
        f"Фактическое время рассылки: {effective_time}"
    )


def send_schedule_to_user(chat_id, class_name, weekday_name=None, silent_weekend=False):
    if weekday_name is None:
        if is_weekend():
            if not silent_weekend:
                bot.send_message(chat_id, "Сегодня выходной, расписания нет.")
            return False

        weekday_name = get_today_weekday_name()

    schedule_path = get_schedule_path(class_name, weekday_name)

    if not schedule_path:
        bot.send_message(
            chat_id,
            f"Не найден файл расписания для класса {class_name} "
            f"на {weekday_name_to_russian(weekday_name)}."
        )
        return False

    with open(schedule_path, "rb") as photo:
        bot.send_photo(
            chat_id,
            photo,
            caption=(
                f"Расписание для класса {class_name} "
                f"на {weekday_name_to_russian(weekday_name)}"
            )
        )
    return True


def send_daily_schedule(force_day=None, only_chat_id=None):
    users = get_all_users()

    if not users:
        print("Нет пользователей для рассылки.")
        return 0, 0

    sent_count = 0
    error_count = 0

    if force_day:
        print(f"Ручной запуск рассылки за день: {force_day}")
    else:
        print("Запущена обычная рассылка...")

    for chat_id, user_data in users.items():
        if only_chat_id is not None and int(chat_id) != int(only_chat_id):
            continue

        class_name = user_data.get("class_name")

        if not class_name:
            continue

        try:
            success = send_schedule_to_user(
                int(chat_id),
                class_name,
                weekday_name=force_day
            )
            if success:
                sent_count += 1
                print(f"Отправлено пользователю {chat_id} ({class_name})")
            time.sleep(0.3)
        except Exception as error:
            error_count += 1
            print(f"Ошибка при отправке пользователю {chat_id}: {error}")

    print(f"Рассылка завершена. Успешно: {sent_count}, ошибок: {error_count}")
    return sent_count, error_count


def process_scheduled_sending():
    now_time = get_current_time_string()
    today_date = get_current_date_string()

    if is_weekend():
        return

    users = get_all_users()

    for chat_id, user_data in users.items():
        class_name = user_data.get("class_name")
        if not class_name:
            continue

        send_time = user_data.get("notification_time") or get_default_send_time()
        last_sent_date = user_data.get("last_sent_date")

        if send_time == now_time and last_sent_date != today_date:
            try:
                success = send_schedule_to_user(int(chat_id), class_name)
                if success:
                    update_user_last_sent_date(chat_id, today_date)
                    print(f"[AUTO] Отправлено пользователю {chat_id} в {send_time}")
                time.sleep(0.3)
            except Exception as error:
                print(f"[AUTO] Ошибка при отправке пользователю {chat_id}: {error}")


def sender_loop():
    print("Поток автоматической рассылки запущен.")
    while not stop_event.is_set():
        try:
            process_scheduled_sending()
            stop_event.wait(CHECK_INTERVAL_SECONDS)
        except Exception as error:
            print(f"Ошибка в sender_loop: {error}")
            stop_event.wait(5)
    print("Поток автоматической рассылки остановлен.")


def graceful_shutdown():
    if stop_event.is_set():
        return

    print("Запущено корректное завершение программы...")
    stop_event.set()

    try:
        bot.stop_polling()
    except Exception as error:
        print(f"Ошибка при остановке polling: {error}")


# ---------------- USER COMMANDS ----------------

@bot.message_handler(commands=["start"])
def start_command(message):
    user_class = get_user_class(message.chat.id)

    if user_class:
        text = (
            "С возвращением!\n\n"
            f"Сейчас у тебя выбран класс: {user_class}\n"
            "Используй кнопки меню ниже."
        )
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=create_main_menu_keyboard()
        )
    else:
        text = (
            "Привет! Я бот для рассылки школьного расписания.\n\n"
            "Сначала выбери свой класс."
        )
        bot.send_message(
            message.chat.id,
            text,
            reply_markup=create_classes_keyboard()
        )


@bot.message_handler(commands=["help"])
def help_command(message):
    text = (
        "Доступные команды:\n"
        "/start — запуск бота\n"
        "/help — список команд\n"
        "/schedule — расписание на сегодня\n"
        "/setclass — выбрать класс\n"
        "/settime — установить своё время уведомления\n"
        "/profile — показать профиль\n"
    )

    if is_admin(message.from_user.id):
        text += (
            "\nАдмин-команды:\n"
            "/admin — админ меню\n"
            "/adminusers — количество пользователей\n"
            "/adminstats — статистика\n"
            "/adminsend [day] — принудительная рассылка\n"
            "/admintime HH:MM — сменить время по умолчанию\n"
        )

    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["schedule"])
def schedule_command(message):
    user_class = get_user_class(message.chat.id)

    if not user_class:
        bot.send_message(
            message.chat.id,
            "Сначала выбери класс через /start или /setclass"
        )
        return

    send_schedule_to_user(message.chat.id, user_class)


@bot.message_handler(commands=["setclass"])
def set_class_command(message):
    bot.send_message(
        message.chat.id,
        "Выбери свой класс:",
        reply_markup=create_classes_keyboard()
    )


@bot.message_handler(commands=["settime"])
def set_time_command(message):
    current_time = get_user_effective_time(message.chat.id)
    bot.send_message(
        message.chat.id,
        f"Текущее время уведомления: {current_time}\n"
        "Отправь новое время в формате ЧЧ:ММ\n"
        "Например: 07:15"
    )
    bot.register_next_step_handler(message, process_user_time_input)


@bot.message_handler(commands=["profile"])
def profile_command(message):
    bot.send_message(
        message.chat.id,
        format_user_profile(message.chat.id),
        reply_markup=create_main_menu_keyboard()
    )


def process_user_time_input(message):
    if not message.text:
        bot.send_message(message.chat.id, "Время не распознано.")
        return

    user_input = message.text.strip()

    if not is_valid_time_format(user_input):
        bot.send_message(
            message.chat.id,
            "Неверный формат времени.\nИспользуй формат ЧЧ:ММ, например 07:15"
        )
        return

    normalized_time = normalize_time_string(user_input)
    save_user_notification_time(message.chat.id, normalized_time)

    bot.send_message(
        message.chat.id,
        f"Готово. Теперь уведомление будет приходить в {normalized_time}",
        reply_markup=create_main_menu_keyboard()
    )


# ---------------- ADMIN COMMANDS ----------------

@bot.message_handler(commands=["admin"])
def admin_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У тебя нет доступа к этой команде.")
        return

    text = (
        "Админ-меню:\n"
        "/adminusers — количество пользователей\n"
        "/adminstats — статистика бота\n"
        "/adminsend [monday|tuesday|wednesday|thursday|friday] — принудительная рассылка\n"
        "/admintime HH:MM — установить время по умолчанию\n"
    )

    bot.send_message(
        message.chat.id,
        text,
        reply_markup=create_admin_menu_keyboard()
    )


@bot.message_handler(commands=["adminusers"])
def admin_users_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У тебя нет доступа к этой команде.")
        return

    users = get_all_users()
    with_class = sum(1 for user in users.values() if user.get("class_name"))

    bot.send_message(
        message.chat.id,
        f"Всего пользователей в базе: {len(users)}\n"
        f"С выбранным классом: {with_class}"
    )


@bot.message_handler(commands=["adminstats"])
def admin_stats_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У тебя нет доступа к этой команде.")
        return

    users = get_all_users()
    uptime = datetime.now() - bot_started_at

    bot.send_message(
        message.chat.id,
        f"Статистика бота:\n"
        f"Пользователей: {len(users)}\n"
        f"Время по умолчанию: {get_default_send_time()}\n"
        f"Uptime: {str(uptime).split('.')[0]}\n"
        f"Поток рассылки активен: {'да' if not stop_event.is_set() else 'нет'}"
    )


@bot.message_handler(commands=["admintime"])
def admin_time_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У тебя нет доступа к этой команде.")
        return

    parts = message.text.split()

    if len(parts) != 2:
        bot.send_message(
            message.chat.id,
            "Использование: /admintime HH:MM\nНапример: /admintime 07:00"
        )
        return

    new_time = parts[1].strip()

    if not is_valid_time_format(new_time):
        bot.send_message(message.chat.id, "Неверный формат времени.")
        return

    new_time = normalize_time_string(new_time)
    set_default_send_time(new_time)

    bot.send_message(
        message.chat.id,
        f"Новое время рассылки по умолчанию установлено: {new_time}"
    )


@bot.message_handler(commands=["adminsend"])
def admin_send_command(message):
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "У тебя нет доступа к этой команде.")
        return

    parts = message.text.split()
    force_day = None

    if len(parts) == 2:
        candidate = parts[1].strip().lower()
        valid_days = ["monday", "tuesday", "wednesday", "thursday", "friday"]

        if candidate not in valid_days:
            bot.send_message(
                message.chat.id,
                "Неверный день.\n"
                "Используй: monday, tuesday, wednesday, thursday, friday"
            )
            return

        force_day = candidate

    sent_count, error_count = send_daily_schedule(force_day=force_day)

    if force_day:
        text = (
            f"Принудительная рассылка за {weekday_name_to_russian(force_day)} завершена.\n"
            f"Успешно: {sent_count}\nОшибок: {error_count}"
        )
    else:
        text = (
            f"Принудительная рассылка на сегодня завершена.\n"
            f"Успешно: {sent_count}\nОшибок: {error_count}"
        )

    bot.send_message(message.chat.id, text)


# ---------------- BUTTONS ----------------

@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in AVAILABLE_CLASSES)
def class_selected(message):
    class_name = message.text.strip().lower()
    save_user_class(message.chat.id, class_name)

    bot.send_message(
        message.chat.id,
        f"Класс {class_name} сохранён.\n"
        "Теперь используй кнопки меню ниже.",
        reply_markup=create_main_menu_keyboard()
    )


@bot.message_handler(func=lambda message: message.text == "📅 Моё расписание")
def button_schedule(message):
    schedule_command(message)


@bot.message_handler(func=lambda message: message.text == "🎓 Сменить класс")
def button_change_class(message):
    set_class_command(message)


@bot.message_handler(func=lambda message: message.text == "🕒 Время уведомления")
def button_set_time(message):
    set_time_command(message)


@bot.message_handler(func=lambda message: message.text == "👤 Мой профиль")
def button_profile(message):
    profile_command(message)


@bot.message_handler(func=lambda message: message.text == "📊 Админ: статистика")
def button_admin_stats(message):
    if is_admin(message.from_user.id):
        admin_stats_command(message)


@bot.message_handler(func=lambda message: message.text == "🚀 Админ: рассылка")
def button_admin_send(message):
    if is_admin(message.from_user.id):
        sent_count, error_count = send_daily_schedule()
        bot.send_message(
            message.chat.id,
            f"Принудительная рассылка завершена.\n"
            f"Успешно: {sent_count}\nОшибок: {error_count}",
            reply_markup=create_admin_menu_keyboard()
        )


@bot.message_handler(func=lambda message: message.text == "⏰ Админ: время")
def button_admin_time(message):
    if is_admin(message.from_user.id):
        bot.send_message(
            message.chat.id,
            f"Текущее время по умолчанию: {get_default_send_time()}\n"
            "Чтобы изменить его, используй команду:\n"
            "/admintime HH:MM"
        )


@bot.message_handler(func=lambda message: message.text == "🔙 Обычное меню")
def button_normal_menu(message):
    bot.send_message(
        message.chat.id,
        "Возвращаю обычное меню.",
        reply_markup=create_main_menu_keyboard()
    )


# ---------------- CONSOLE DEBUG ----------------

def console_commands_loop():
    print("Команды консоли: send, users, stats, stop")

    while not stop_event.is_set():
        try:
            command = input().strip().lower()

            if command == "send":
                send_daily_schedule()

            elif command == "users":
                users = get_all_users()
                print(f"Сохранено пользователей: {len(users)}")

            elif command == "stats":
                users = get_all_users()
                print(f"Пользователей: {len(users)}")
                print(f"Время по умолчанию: {get_default_send_time()}")

            elif command == "stop":
                graceful_shutdown()
                break

            elif command:
                print("Неизвестная команда. Доступно: send, users, stats, stop")

        except EOFError:
            break
        except Exception as error:
            print(f"Ошибка в консольной команде: {error}")


# ---------------- MAIN ----------------

def main():
    print("Бот запущен.")
    print(f"Время рассылки по умолчанию: {get_default_send_time()}")

    sender_thread = threading.Thread(target=sender_loop, daemon=True)
    sender_thread.start()

    console_thread = threading.Thread(target=console_commands_loop, daemon=True)
    console_thread.start()

    try:
        bot.infinity_polling(skip_pending=True, timeout=20, long_polling_timeout=20)
    except KeyboardInterrupt:
        print("Получен KeyboardInterrupt.")
    except Exception as error:
        print(f"Ошибка в polling: {error}")
    finally:
        graceful_shutdown()
        time.sleep(1)
        print("Программа завершена.")
        sys.exit(0)


if __name__ == "__main__":
    main()