from time import sleep
from requests import get as rget
from os import environ
from logging import getLogger, FileHandler, StreamHandler, INFO, basicConfig, error as logerror

basicConfig(format='%(asctime)s - %(name)s %(levelname)s : %(message)s [%(module)s:%(lineno)d]',
            handlers=[FileHandler('log.txt'), StreamHandler()],
            level=INFO)

BASE_URL = environ.get('BASE_URL', None)
try:
    if len(BASE_URL) == 0:
        BASE_URL = 'http://127.0.0.1'
    BASE_URL = BASE_URL.rstrip("/")

PORT = environ.get('PORT', None)
if PORT is not None and BASE_URL is not None:
    while True:
        try:
            rget(BASE_URL).status_code
            sleep(60)
        except Exception as e:
            logerror(f"alive.py: {e}")
            sleep(2)
            continue
