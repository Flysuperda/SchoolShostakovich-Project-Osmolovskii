import threading
import time

import telebot
from telebot import types
import schedule

from config import TOKEN, SEND_TIME, AVAILABLE_CLASSES
from storage import save_user_class, get_user_class, get_all_users
from schedule_utils import get_schedule_path, is_weekend

bot = telebot.TeleBot(TOKEN)


def create_classes_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    buttons = []
    for class_name in AVAILABLE_CLASSES:
        buttons.append(types.KeyboardButton(class_name))

    markup.add(*buttons)
    return markup


def send_schedule_to_user(chat_id, class_name):
    if is_weekend():
        bot.send_message(chat_id, "Сегодня выходной, расписания нет.")
        return

    schedule_path = get_schedule_path(class_name)

    if not schedule_path:
        bot.send_message(
            chat_id,
            f"Не найден файл расписания для класса {class_name} на сегодня."
        )
        return

    with open(schedule_path, "rb") as photo:
        bot.send_photo(
            chat_id,
            photo,
            caption=f"Расписание для класса {class_name} на сегодня"
        )


@bot.message_handler(commands=["start"])
def start_command(message):
    user_class = get_user_class(message.chat.id)

    text = (
        "Привет! Я бот для рассылки школьного расписания.\n\n"
        "Выбери свой класс, и я смогу отправлять тебе расписание.\n"
        "Также ты можешь получить расписание вручную командой /schedule"
    )

    if user_class:
        text += f"\n\nСейчас у тебя выбран класс: {user_class}"

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
        "/setclass — выбрать класс заново\n"
        "/schedule — получить расписание на сегодня\n\n"
        "Также можно просто нажать на кнопку с классом."
    )
    bot.send_message(message.chat.id, text)


@bot.message_handler(commands=["setclass"])
def set_class_command(message):
    bot.send_message(
        message.chat.id,
        "Выбери свой класс:",
        reply_markup=create_classes_keyboard()
    )


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


@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in AVAILABLE_CLASSES)
def class_selected(message):
    class_name = message.text.strip().lower()
    save_user_class(message.chat.id, class_name)

    bot.send_message(
        message.chat.id,
        f"Класс {class_name} сохранён.\nТеперь ты будешь получать расписание для этого класса."
    )


def send_daily_schedule():
    users = get_all_users()

    if not users:
        print("Нет пользователей для рассылки.")
        return

    print("Запущена рассылка...")

    sent_count = 0
    error_count = 0

    for chat_id, user_data in users.items():
        class_name = user_data.get("class_name")

        if not class_name:
            continue

        try:
            send_schedule_to_user(int(chat_id), class_name)
            sent_count += 1
            print(f"Отправлено пользователю {chat_id} ({class_name})")
            time.sleep(0.5)
        except Exception as error:
            error_count += 1
            print(f"Ошибка при отправке пользователю {chat_id}: {error}")

    print(f"Рассылка завершена. Успешно: {sent_count}, ошибок: {error_count}")


def scheduler_loop():
    schedule.every().day.at(SEND_TIME).do(send_daily_schedule)
    print(f"Автоматическая рассылка запланирована на {SEND_TIME}")

    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as error:
            print(f"Ошибка в планировщике: {error}")
            time.sleep(5)


def console_commands_loop():
    print("Команды консоли: send, users, exit")

    while True:
        try:
            command = input().strip().lower()

            if command == "send":
                print("Ручной запуск рассылки...")
                send_daily_schedule()

            elif command == "users":
                users = get_all_users()
                print(f"Сохранено пользователей: {len(users)}")

            elif command == "exit":
                print("Остановка бота...")
                break

            elif command:
                print("Неизвестная команда. Доступно: send, users, exit")

        except Exception as error:
            print(f"Ошибка в консольной команде: {error}")


def main():
    print("Бот запущен.")

    scheduler_thread = threading.Thread(target=scheduler_loop, daemon=True)
    scheduler_thread.start()

    console_thread = threading.Thread(target=console_commands_loop, daemon=True)
    console_thread.start()

    bot.infinity_polling(skip_pending=True)


if __name__ == "__main__":
    main()