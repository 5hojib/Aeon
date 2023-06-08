import re
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
        if message.reply_to_message and message.reply_to_message.text:
            reply_to_text = message.reply_to_message.text
            url_match = re.search(r"(?P<url>https?://[^\s]+)", reply_to_text)
            if url_match:
                url = url_match.group("url")
                match = re.match(r"/index(?:\s(-s))?(?:\s(-u)\s(\S+))?(?:\s(-p)\s(\S+))?", message.text.strip())
                if match:
                    index_link = url
                    send_separately = bool(match.group(1))
                    username = match.group(3)
                    password = match.group(5)
                    if not index_link:
                        help_message = """No index link provided. Please use the /index command followed by the index link.

Usage:
/index index_link

Options:
• -s: Send each link separately.
• -u: Username
• -p: Password

Example:
/index https://example.com/index.html -s -u your_username -p your_password
"""
                        await client.send_message(message.chat.id, help_message)
                        return
                else:
                    index_link = url
                    send_separately = False
                    username = "username-default"
                    password = "password-default"
            else:
                return
        else:
            help_message = """No index link provided. Please use the /index command followed by the index link.

Usage:
/index index_link

Options:
• -s: Send each link separately.
• -u: Username
• -p: Password

Example:
/index https://example.com/index.html -s -u your_username -p your_password
"""
            await client.send_message(message.chat.id, help_message)
            return
    else:
        split_text = message.text.split()

        if split_text[0] != "/index":
            return

        url_match = re.search(r"(?P<url>https?://[^\s]+)", split_text[1])
        if url_match:
            url = url_match.group("url")
            index_link = url
            send_separately = False
            username = "username-default"
            password = "password-default"

            for i in range(2, len(split_text)):
                if split_text[i] == "-s":
                    send_separately = True
                elif split_text[i] == "-u" and i + 1 < len(split_text):
                    username = split_text[i + 1]
                elif split_text[i] == "-p" and i + 1 < len(split_text):
                    password = split_text[i + 1]

    if send_separately:
        # Send each link separately
        result = await get_direct_download_links(index_link, username, password)
        links = result.split('\n')
        total_files = len(links)
        for link in links:
            await client.send_message(message.chat.id, link)
            await asyncio.sleep(1)
        completion_message = f"Your task is done, total files: {total_files}"
        await client.send_message(message.chat.id, completion_message)
    else:
        # Save links to a text file
        result = await get_direct_download_links(index_link, username, password)
        file_path = "extracted_links.txt"
        with open(file_path, "w") as file:
            file.write(result)

        # Send the text file as a document
        await client.send_document(message.chat.id, file_path)

        # Remove the text file
        os.remove(file_path)


bot.add_handler(MessageHandler(extract_url, filters=command("index")))
