from asyncio import sleep as asleep

from telegraph import upload_file
from aiofiles.os import remove as aioremove
from pyrogram.filters import regex, command
from pyrogram.handlers import MessageHandler, CallbackQueryHandler

from bot import IMAGES, LOGGER, DATABASE_URL, bot
from bot.helper.ext_utils.bot_utils import new_task, handle_index
from bot.helper.ext_utils.db_handler import DbManager
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.button_build import ButtonMaker
from bot.helper.telegram_helper.message_utils import (
    edit_message,
    send_message,
    delete_message,
)


@new_task
async def picture_add(_, message):
    reply = message.reply_to_message
    msg = await send_message(message, "Fetching input...")

    if len(message.command) > 1 or (reply and reply.text):
        msg_text = reply.text if reply else message.command[1]
        if not msg_text.startswith("http"):
            return await edit_message(
                msg, "This is not a valid link. It must start with 'http'."
            )
        graph_url = msg_text.strip()
        await edit_message(msg, f"Adding your link: <code>{graph_url}</code>")

    elif reply and reply.photo:
        if reply.photo.file_size > 5242880 * 2:
            return await edit_message(
                msg, "Media format is not supported. Only photos are allowed."
            )

        try:
            photo_dir = await reply.download()
            await edit_message(
                msg, "Now, uploading to <code>graph.org</code>, Please Wait..."
            )
            await asleep(1)
            graph_url = f"https://graph.org{upload_file(photo_dir)[0]}"
            LOGGER.info(f"Telegraph link : {graph_url}")
        except Exception as e:
            LOGGER.error(f"Images Error: {e!s}")
            await edit_message(msg, str(e))
        finally:
            await aioremove(photo_dir)

    else:
        help_msg = f"Add an image using /{BotCommands.AddImageCommand} followed by IMAGE_LINK, or reply to an image with /{BotCommands.AddImageCommand}."
        return await edit_message(msg, help_msg)

    IMAGES.append(graph_url)

    if DATABASE_URL:
        await DbManager().update_config({"IMAGES": IMAGES})

    await asleep(1.5)
    await edit_message(
        msg,
        f"<b>Successfully added to the images list!</b>\n\n<b>Total images: {len(IMAGES)}</b>",
    )
    return None


async def pictures(_, message):
    if not IMAGES:
        await send_message(
            message,
            f"No images to display! Add images using /{BotCommands.AddImageCommand}.",
        )
    else:
        to_edit = await send_message(message, "Generating a grid of your images...")
        buttons = ButtonMaker()
        user_id = message.from_user.id
        buttons.callback("<<", f"images {user_id} turn -1")
        buttons.callback(">>", f"images {user_id} turn 1")
        buttons.callback("Remove image", f"images {user_id} remove 0")
        buttons.callback("Close", f"images {user_id} close")
        buttons.callback("Remove all", f"images {user_id} removeall", "footer")
        await delete_message(to_edit)
        await send_message(
            message,
            f"<b>Image No. : 1 / {len(IMAGES)}</b>",
            buttons.column(2),
            IMAGES[0],
        )


@new_task
async def pics_callback(_, query):
    message = query.message
    user_id = query.from_user.id
    data = query.data.split()

    if user_id != int(data[1]):
        await query.answer(text="Not authorized user!", show_alert=True)
        return

    if data[2] == "turn":
        await query.answer()
        ind = handle_index(int(data[3]), IMAGES)
        no = len(IMAGES) - abs(ind + 1) if ind < 0 else ind + 1
        pic_info = f"<b>Image No. : {no} / {len(IMAGES)}</b>"
        buttons = ButtonMaker()
        buttons.callback("<<", f"images {data[1]} turn {ind-1}")
        buttons.callback(">>", f"images {data[1]} turn {ind+1}")
        buttons.callback("Remove Image", f"images {data[1]} remove {ind}")
        buttons.callback("Close", f"images {data[1]} close")
        buttons.callback("Remove all", f"images {data[1]} removeall", "footer")
        await edit_message(message, pic_info, buttons.column(2), IMAGES[ind])

    elif data[2] == "remove":
        IMAGES.pop(int(data[3]))
        if DATABASE_URL:
            await DbManager().update_config({"IMAGES": IMAGES})
        query.answer("Image has been successfully deleted", show_alert=True)

        if len(IMAGES) == 0:
            await query.message.delete()
            await send_message(
                message,
                f"No images to display! Add images using /{BotCommands.AddImageCommand}.",
            )
            return

        ind = int(data[3]) + 1
        ind = len(IMAGES) - abs(ind) if ind < 0 else ind
        pic_info = f"<b>Image No. : {ind+1} / {len(IMAGES)}</b>"
        buttons = ButtonMaker()
        buttons.callback("<<", f"images {data[1]} turn {ind-1}")
        buttons.callback(">>", f"images {data[1]} turn {ind+1}")
        buttons.callback("Remove image", f"images {data[1]} remove {ind}")
        buttons.callback("Close", f"images {data[1]} close")
        buttons.callback("Remove all", f"images {data[1]} removeall", "footer")
        await edit_message(message, pic_info, buttons.column(2), IMAGES[ind])

    elif data[2] == "removeall":
        IMAGES.clear()
        if DATABASE_URL:
            await DbManager().update_config({"IMAGES": IMAGES})
        await query.answer(
            "All images have been successfully deleted.", show_alert=True
        )
        await send_message(
            message,
            f"No images to display! Add images using /{BotCommands.AddImageCommand}.",
        )
        await message.delete()
    else:
        await query.answer()
        await message.delete()
        await message.reply_to_message.delete()


bot.add_handler(
    MessageHandler(
        picture_add,
        filters=command(BotCommands.AddImageCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(
    MessageHandler(
        pictures,
        filters=command(BotCommands.ImagesCommand) & CustomFilters.authorized,
    )
)
bot.add_handler(CallbackQueryHandler(pics_callback, filters=regex(r"^images")))
