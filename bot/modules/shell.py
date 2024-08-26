from io import BytesIO

from pyrogram.filters import command
from pyrogram.handlers import MessageHandler, EditedMessageHandler

from bot import bot
from bot.helper.ext_utils.bot_utils import cmd_exec, new_task
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendFile, send_message


@new_task
async def shell(_, message):
    cmd = message.text.split(maxsplit=1)
    if len(cmd) == 1:
        await send_message(message, "No command to execute was provided.")
        return
    cmd = cmd[1]
    stdout, stderr, _ = await cmd_exec(cmd, shell=True)
    reply = ""

    if len(stdout) != 0:
        reply += f"<b>Stdout</b>\n<pre>{stdout}</pre>\n"

    if len(stderr) != 0:
        reply += f"<b>Stderr</b>\n<pre>{stderr}</pre>"

    if len(reply) > 3000:
        with BytesIO(str.encode(reply)) as out_file:
            out_file.name = "shell_output.txt"
            await sendFile(message, out_file)
    elif len(reply) != 0:
        await send_message(message, reply)
    else:
        await send_message(message, "No Reply")


bot.add_handler(
    MessageHandler(
        shell, filters=command(BotCommands.ShellCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    EditedMessageHandler(
        shell, filters=command(BotCommands.ShellCommand) & CustomFilters.sudo
    )
)
