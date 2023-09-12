import os
import time
import logging
import requests

BASE_URL = os.environ.get('BASE_URL', None)
try:
    if len(BASE_URL) == 0:
        raise TypeError
    BASE_URL = BASE_URL.rstrip("/")
except TypeError:
    BASE_URL = None
PORT = os.environ.get('PORT', None)
if PORT is not None and BASE_URL is not None:
    while True:
        try:
            requests.get(BASE_URL).status_code
            time.sleep(400)
        except Exception as e:
            logging.error(f"alive.py: {e}")
            time.sleep(2)
            continue