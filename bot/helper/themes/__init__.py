from random import choice as rchoice
from bot import config_dict, LOGGER
from bot.helper.themes import minimal

AVL_THEMES = {'minimal': minimal}

def BotTheme(var_name, **format_vars):
    theme_ = 'minimal'

    if theme_ in AVL_THEMES:
        text = getattr(AVL_THEMES[theme_].style(), var_name)
    elif theme_ == 'random':
        rantheme = rchoice(list(AVL_THEMES.values()))
        LOGGER.info(f"Random Theme Chosen: {rantheme}")
        text = getattr(rantheme.style(), var_name)
    else:
        text = getattr(minimal.style(), var_name)

    return text.format_map(format_vars)