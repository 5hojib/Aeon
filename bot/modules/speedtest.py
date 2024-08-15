from speedtest import Speedtest
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler

from bot import LOGGER, bot
from bot.helper.ext_utils.bot_utils import new_task, get_readable_file_size
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import (
    editMessage,
    sendMessage,
    deleteMessage,
)


@new_task
async def speedtest(_, message):
    speed = await sendMessage(message, "Initializing Speedtest...")

    def get_speedtest_results():
        test = Speedtest()
        test.get_best_server()
        test.download()
        test.upload()
        return test.results

    result = await bot.loop.run_in_executor(None, get_speedtest_results)

    if not result:
        await editMessage(speed, "Speedtest failed to complete.")
        return

    string_speed = "<b>SPEEDTEST INFO</b>\n\n"
    string_speed += f"<b>• Ping:</b> <code>{result.ping} ms</code>\n"
    string_speed += f"<b>• Upload:</b> <code>{get_readable_file_size(result.upload / 8)}/s</code>\n"
    string_speed += f"<b>• Download:</b> <code>{get_readable_file_size(result.download / 8)}/s</code>\n"
    string_speed += f"<b>• IP Address:</b> <code>{result.client['ip']}</code>"

    try:
        await sendMessage(message, string_speed, photo=result.share())
        await deleteMessage(speed)
    except Exception as e:
        LOGGER.error(str(e))
        await editMessage(speed, string_speed)


bot.add_handler(
    MessageHandler(
        speedtest,
        filters=command(BotCommands.SpeedCommand) & CustomFilters.authorized,
    )
)
