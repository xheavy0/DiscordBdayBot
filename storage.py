# ============================
# საერთო: დრო და მონაცემების ფაილი
# ============================
import json
import os
from datetime import datetime, timedelta, timezone

# საქართველოს დრო (UTC+4, საზაფხულო დროზე არ გადავდივართ)
GEORGIA_TZ = timezone(timedelta(hours=4), name="Tbilisi")

DATA_FILE = "birthdays.json"


def now_ge() -> datetime:
    return datetime.now(GEORGIA_TZ)


def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data: dict):
    # ჯერ დროებით ფაილში ვწერთ, რომ ჩავარდნისას მონაცემები არ დაზიანდეს
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)
