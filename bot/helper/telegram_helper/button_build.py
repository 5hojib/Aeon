from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class ButtonMaker:
    def __init__(self):
        self.main_buttons = []
        self.header_buttons = []
        self.footer_buttons = []

    def url(self, text, url, position=None):
        button = InlineKeyboardButton(text=text, url=url)
        if position == "header":
            self.header_buttons.append(button)
        elif position == "footer":
            self.footer_buttons.append(button)
        else:
            self.main_buttons.append(button)

    def callback(self, text, callback_data, position=None):
        button = InlineKeyboardButton(text=text, callback_data=callback_data)
        if position == "header":
            self.header_buttons.append(button)
        elif position == "footer":
            self.footer_buttons.append(button)
        else:
            self.main_buttons.append(button)

    def column(self, main_columns=1, header_columns=8, footer_columns=8):
        keyboard = [
            self.main_buttons[i : i + main_columns]
            for i in range(0, len(self.main_buttons), main_columns)
        ]

        if self.header_buttons:
            if len(self.header_buttons) > header_columns:
                header_chunks = [
                    self.header_buttons[i : i + header_columns]
                    for i in range(0, len(self.header_buttons), header_columns)
                ]
                keyboard = header_chunks + keyboard
            else:
                keyboard.insert(0, self.header_buttons)

        if self.footer_buttons:
            if len(self.footer_buttons) > footer_columns:
                footer_chunks = [
                    self.footer_buttons[i : i + footer_columns]
                    for i in range(0, len(self.footer_buttons), footer_columns)
                ]
                keyboard += footer_chunks
            else:
                keyboard.append(self.footer_buttons)

        return InlineKeyboardMarkup(keyboard)
