from telegram import Update
from pymongo import MongoClient
from telegram.ext import CommandHandler

from bot import app, OWNER_ID, DATABASE_URL, dispatcher
from bot.helper.telegram_helper.filters import CustomFilters


def dbusers(update, context):
    if not DATABASE_URL:
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"DATABASE_URL not provided")
    else:
        client = MongoClient(DATABASE_URL)
        db = client["mltb"]
        count = db.users.count_documents({})
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Total users in database: {count}")


def get_id(update: Update, context):
    chat_id = update.effective_chat.id
    if update.effective_chat.type == 'private':
        user_id = update.message.from_user.id
        context.bot.send_message(chat_id=user_id, text=f"Your user ID is: <code>{user_id}</code>")
    else:
        context.bot.send_message(chat_id=chat_id, text=f"This group's ID is: <code>{chat_id}</code>")


dbusers_handler = CommandHandler("dbusers", dbusers, filters=CustomFilters.owner_filter | CustomFilters.sudo_user)
id_handler = CommandHandler("id", get_id)

dispatcher.add_handler(dbusers_handler)
dispatcher.add_handler(id_handler)
