import os
from datetime import datetime, timedelta
from config import SCHEDULES_DIR


WEEKDAY_NAMES = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday"
}

RUS_WEEKDAY_NAMES = {
    "monday": "понедельник",
    "tuesday": "вторник",
    "wednesday": "среда",
    "thursday": "четверг",
    "friday": "пятница"
}


def get_today_weekday_name():
    weekday_number = datetime.now().weekday()
    return WEEKDAY_NAMES.get(weekday_number)


def get_tomorrow_weekday_name():
    tomorrow = datetime.now() + timedelta(days=1)
    weekday_number = tomorrow.weekday()
    return WEEKDAY_NAMES.get(weekday_number)


def get_schedule_path(class_name, weekday_name=None):
    if weekday_name is None:
        weekday_name = get_today_weekday_name()

    if weekday_name is None:
        return None

    filename = f"{class_name}_{weekday_name}.png"
    full_path = os.path.join(SCHEDULES_DIR, filename)

    if os.path.exists(full_path):
        return full_path

    return None


def is_weekend(date_obj=None):
    if date_obj is None:
        date_obj = datetime.now()
    return date_obj.weekday() >= 5


def get_current_date_string():
    return datetime.now().strftime("%Y-%m-%d")


def get_current_time_string():
    return datetime.now().strftime("%H:%M")


def is_valid_time_format(time_str):
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False


def normalize_time_string(time_str):
    return datetime.strptime(time_str, "%H:%M").strftime("%H:%M")


def weekday_name_to_russian(weekday_name):
    return RUS_WEEKDAY_NAMES.get(weekday_name, weekday_name)