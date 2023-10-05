from secrets import token_hex
from asyncio import sleep
from telegraph.aio import Telegraph
from telegraph.exceptions import RetryAfterError

from bot import LOGGER, bot_loop

class TelegraphHelper:
    def __init__(self):
        self.telegraph = Telegraph(domain='graph.org')
        self.short_name = token_hex(4)
        self.access_token = None
        self.author_name = 'Aeon'
        self.author_url = 'https://t.me/ProjectAeon'
        self.create_account()

    def create_account(self):
        try:
            self.telegraph.create_account(
                short_name = self.short_name,
                author_name = self.author_name,
                author_url = self.author_url)
            self.access_token = self.telegraph.get_access_token()
            LOGGER.info("Creating Telegraph Account")
        except Exception as e:
            LOGGER.error(f"Telegraph account creation failed: {str(e)}")

    def handle_retry_error(self, method, *args, **kwargs):
        try:
            return method(*args, **kwargs)
        except RetryAfterError as st:
            LOGGER.warning(f'Telegraph Flood control exceeded. Sleeping for {st.retry_after} seconds.')
            sleep(st.retry_after)
            return self.handle_retry_error(method, *args, **kwargs)

    def create_page(self, title, content):
        try:
            return self.handle_retry_error(
                self.telegraph.create_page,
                title = title,
                author_name = self.author_name,
                author_url = self.author_url,
                html_content = content)
        except Exception as e:
            LOGGER.error(f"Telegraph page creation failed: {str(e)}")

    def edit_page(self, path, title, content):
        try:
            return self.handle_retry_error(
                self.telegraph.edit_page,
                path = path,
                title = title,
                author_name = self.author_name,
                author_url = self.author_url,
                html_content = content)
        except Exception as e:
            LOGGER.error(f"Telegraph page editing failed: {str(e)}")

    def edit_telegraph(self, path, telegraph_content):
        nxt_page = 1
        prev_page = 0
        num_of_path = len(path)
        
        for content in telegraph_content:
            if nxt_page == 1:
                content += f'<b><a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                nxt_page += 1
            else:
                if prev_page <= num_of_path:
                    content += f'<b><a href="https://telegra.ph/{path[prev_page]}">Prev</a></b>'
                    prev_page += 1
                if nxt_page < num_of_path:
                    content += f'<b> | <a href="https://telegra.ph/{path[nxt_page]}">Next</a></b>'
                    nxt_page += 1
            self.edit_page(
                path = path[prev_page],
                title = "Torrent Search",
                content = content)

telegraph = TelegraphHelper()
bot_loop.run_until_complete(telegraph.create_account())
