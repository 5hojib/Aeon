from typing import List, Union

import telegram
from telegram import raw
from telegram import types
from ..object import Object


class ReplyKeyboardMarkup(Object):
    def __init__(
        self,
        keyboard: List[List[Union["types.KeyboardButton", str]]],
        is_persistent: bool = None,
        resize_keyboard: bool = None,
        one_time_keyboard: bool = None,
        selective: bool = None,
        placeholder: str = None
    ):
        super().__init__()

        self.keyboard = keyboard
        self.is_persistent = is_persistent
        self.resize_keyboard = resize_keyboard
        self.one_time_keyboard = one_time_keyboard
        self.selective = selective
        self.placeholder = placeholder

    @staticmethod
    def read(kb: "raw.base.ReplyMarkup"):
        keyboard = []

        for i in kb.rows:
            row = []

            for j in i.buttons:
                row.append(types.KeyboardButton.read(j))

            keyboard.append(row)

        return ReplyKeyboardMarkup(
            keyboard=keyboard,
            is_persistent=kb.persistent,
            resize_keyboard=kb.resize,
            one_time_keyboard=kb.single_use,
            selective=kb.selective,
            placeholder=kb.placeholder
        )

    async def write(self, _: "telegram.Client"):
        return raw.types.ReplyKeyboardMarkup(
            rows=[raw.types.KeyboardButtonRow(
                buttons=[
                    types.KeyboardButton(j).write()
                    if isinstance(j, str) else j.write()
                    for j in i
                ]
            ) for i in self.keyboard],
            resize=self.resize_keyboard or None,
            single_use=self.one_time_keyboard or None,
            selective=self.selective or None,
            persistent=self.is_persistent or None,
            placeholder=self.placeholder or None
        )
