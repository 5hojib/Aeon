import asyncio
import os

from json import loads as jloads
from requests import post as rpost
from base64 import b64encode, b64decode
from urllib.parse import quote as uquote

from bot import bot
from pyrogram import filters
from pyrogram.filters import command
from pyrogram.handlers import MessageHandler


def authorization_token(username, password):
    user_pass = f"{username}:{password}"
    return f"Basic {b64encode(user_pass.encode()).decode()}"


def decrypt(string):
    return b64decode(string[::-1][24:-20]).decode("utf-8")


async def get_direct_download_links(url, username="none", password="none"):
    next_page = True
    next_page_token = ""
    links = []

    while next_page:
        payload = {"page_token": next_page_token, "page_index": len(links)}
        url = f"{url}/" if url[-1] != "/" else url

        try:
            headers = {"authorization": authorization_token(username, password)}
        except:
            return "username/password combination is wrong"

        encrypted_response = rpost(url, data=payload, headers=headers)
        if encrypted_response.status_code == 401:
            return "username/password combination is wrong"

        try:
            decrypted_response = jloads(decrypt(encrypted_response.text))
        except:
            return "something went wrong. check index link/username/password field again"

        page_token = decrypted_response.get("nextPageToken")
        if not page_token:
            next_page = False
        else:
            next_page_token = page_token

        if "error" not in decrypted_response.get("data", {}):
            files = decrypted_response.get("data", {}).get("files", [])
            for file in files:
                if file["mimeType"] != "application/vnd.google-apps.folder":
                    file_name = file["name"]
                    direct_download_link = url + uquote(file_name)
                    links.append(direct_download_link)

    return '\n'.join(links)


async def extract_url(client, message):
    if len(message.text.split()) < 2:
        # Check if message is a reply and extract the URL from the replied message
        if len(message.text) == 0 and message.reply_to_message:
            reply_to_text = message.reply_to_message.text
            if reply_to_text:
                url = reply_to_text.split(maxsplit=1)[0].strip()
                if url.startswith("http"):
                    split_text = ["/index", url]
                else:
                    split_text = ["/index"]
        else:
            help_message = """No index link provided. Please use the /index command followed by the index link.

Usage:
/index index_link

Options:
• -s: Send each link separately.

Example:
/index https://example.com/index.html -s
"""
            await client.send_message(message.chat.id, help_message)
            return
    else:
        split_text = message.text.split()

    if len(split_text) < 2:
        help_message = """No index link provided. Please use the /index command followed by the index link.

Usage:
/index index_link

Options:
• -s: Send each link separately.

Example:
/index https://example.com/index.html -s
"""
        await client.send_message(message.chat.id, help_message)
        return

    index_link = split_text[1]
    username = "username-default"
    password = "password-default"
    result = await get_direct_download_links(index_link, username, password)

    if len(split_text) > 2 and split_text[2] == "-s":
        # Send each link separately with a delay of one second
        links = result.split('\n')
        total_files = len(links)
        for link in links:
            await client.send_message(message.chat.id, link)
            await asyncio.sleep(1)
        completion_message = f"Your task done, total files: {total_files}"
        await client.send_message(message.chat.id, completion_message)
    else:
        # Save links to a text file
        file_path = "extracted_links.txt"
        with open(file_path, "w") as file:
            file.write(result)

        # Send the text file as a document
        await client.send_document(message.chat.id, file_path)

        # Remove the text file
        os.remove(file_path)


bot.add_handler(MessageHandler(extract_url, filters=command("index")))