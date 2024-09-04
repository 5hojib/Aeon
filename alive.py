import os
import time
import logging

import requests

BASE_URL = os.environ.get("BASE_URL", None)

try:
    if not BASE_URL:
        raise TypeError
    BASE_URL = BASE_URL.rstrip("/")
except TypeError:
    BASE_URL = None

PORT = os.environ.get("PORT", None)


def check_status():
    try:
        requests.get(BASE_URL).status_code
    except Exception as e:
        logging.error(f"alive.py: {e}")
        return False
    return True


if PORT and BASE_URL:
    while True:
        if check_status():
            time.sleep(400)
        else:
            time.sleep(2)
