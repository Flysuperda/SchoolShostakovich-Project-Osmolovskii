import os
from datetime import datetime
from config import SCHEDULES_DIR


WEEKDAY_NAMES = {
    0: "monday",
    1: "tuesday",
    2: "wednesday",
    3: "thursday",
    4: "friday"
}


def get_today_weekday_name():
    weekday_number = datetime.now().weekday()
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


def is_weekend():
    return datetime.now().weekday() >= 5