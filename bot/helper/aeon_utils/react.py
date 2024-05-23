from random import choice
from bot import bot

async def react(message):
    chat_id = int(message.chat.id)
    chat_info = await bot.get_chat(chat_id)
    available_reactions = chat_info.available_reactions
    
    full_emoji_set = {'👌', '🔥', '🥰', '❤️', '❤️‍🔥', '💯', '⚡', '💋', '😘', '🤩', '😍'}
    
    if available_reactions:
        if getattr(available_reactions, "all_are_enabled", False):
            emojis = full_emoji_set
        else:
            emojis = {reaction.emoji for reaction in available_reactions.reactions}
        
        await message.react(choice(list(emojis)), big=True)