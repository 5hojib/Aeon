from importlib import import_module

from pyrogram.raw import types, functions, base, core
from pyrogram.raw.all import objects

for k, v in objects.items():
    path, name = v.rsplit(".", 1)
    objects[k] = getattr(import_module(path), name)
