from io import BytesIO, StringIO
from os import path, chdir, getcwd
from re import match
from textwrap import indent
from traceback import format_exc
from contextlib import suppress, redirect_stdout

from aiofiles import open as aiopen
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler, EditedMessageHandler

from bot import LOGGER, bot, user
from bot.helper.ext_utils.bot_utils import new_task
from bot.helper.telegram_helper.filters import CustomFilters
from bot.helper.telegram_helper.bot_commands import BotCommands
from bot.helper.telegram_helper.message_utils import sendFile, send_message


def create_execution_environment(message):
    return {
        "__builtins__": globals()["__builtins__"],
        "bot": bot,
        "message": message,
        "user": user,
    }


def log_input(message):
    LOGGER.info(
        f"INPUT: {message.text} (User ID={message.from_user.id} | Chat ID={message.chat.id})"
    )


async def send_response(msg, message):
    if len(str(msg)) > 2000:
        with BytesIO(str.encode(msg)) as out_file:
            out_file.name = "output.txt"
            await sendFile(message, out_file)
    else:
        LOGGER.info(f"OUTPUT: '{msg}'")
        if not msg or msg == "\n":
            msg = "MessageEmpty"
        elif not bool(match(r"<(spoiler|b|i|code|s|u)>", msg)):
            msg = f"<pre>{msg}</pre>"
        await send_message(message, msg)


@new_task
async def evaluate(_, message):
    content = message.text.split(maxsplit=1)
    if len(content) == 1:
        await send_response("No command to execute.", message)
    else:
        await send_response(await execute_code(eval, message), message)


@new_task
async def execute(_, message):
    content = message.text.split(maxsplit=1)
    if len(content) == 1:
        await send_response("No command to execute.", message)
    else:
        await send_response(await execute_code(exec, message), message)


def cleanup_code(code):
    if code.startswith("```") and code.endswith("```"):
        return "\n".join(code.split("\n")[1:-1])
    return code.strip("` \n")


async def execute_code(func, message):
    log_input(message)
    content = message.text.split(maxsplit=1)[-1]
    code = cleanup_code(content)
    env = create_execution_environment(message)

    chdir(getcwd())
    async with aiopen(path.join(getcwd(), "bot/modules/temp.txt"), "w") as temp_file:
        await temp_file.write(code)

    stdout = StringIO()
    to_compile = f'async def func():\n{indent(code, "  ")}'

    try:
        exec(to_compile, env)
    except Exception as e:
        return f"{e.__class__.__name__}: {e}"

    func = env["func"]

    try:
        with redirect_stdout(stdout):
            func_return = await func()
    except Exception:
        return f"{stdout.getvalue()}{format_exc()}"
    else:
        result = stdout.getvalue()
        if func_return is not None:
            result += str(func_return)
        elif not result:
            with suppress(Exception):
                result = repr(eval(code, env))
        return result


bot.add_handler(
    MessageHandler(
        evaluate, filters=command(BotCommands.EvalCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    MessageHandler(
        execute, filters=command(BotCommands.ExecCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    EditedMessageHandler(
        evaluate, filters=command(BotCommands.EvalCommand) & CustomFilters.sudo
    )
)
bot.add_handler(
    EditedMessageHandler(
        execute, filters=command(BotCommands.ExecCommand) & CustomFilters.sudo
    )
)
