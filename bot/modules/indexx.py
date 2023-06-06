import requests
import base64
import json
import urllib
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

next_page = False
next_page_token = ""


def authorization_token(username, password):
    user_pass = f"{username}:{password}"
    return f"Basic {base64.b64encode(user_pass.encode()).decode()}"


def decrypt(string):
    return base64.b64decode(string[::-1][24:-20]).decode("utf-8")


def func(payload_input, url, username, password):
    global next_page
    global next_page_token

    url = f"{url}/" if url[-1] != "/" else url

    try:
        headers = {"authorization": authorization_token(username, password)}
    except:
        return "username/password combination is wrong"

    encrypted_response = requests.post(url, data=payload_input, headers=headers)
    if encrypted_response.status_code == 401:
        return "username/password combination is wrong"

    try:
        decrypted_response = json.loads(decrypt(encrypted_response.text))
    except:
        return "something went wrong. check index link/username/password field again"

    page_token = decrypted_response.get("nextPageToken")
    if page_token is None:
        next_page = False
    else:
        next_page = True
        next_page_token = page_token

    if decrypted_response.get("data") and decrypted_response["data"].get("files"):
        file_length = len(decrypted_response["data"]["files"])
        links = []

        for i in range(file_length):
            file_data = decrypted_response["data"]["files"][i]
            files_type = file_data.get("mimeType")
            if files_type != "application/vnd.google-apps.folder":
                files_name = file_data.get("name")
                if files_name:
                    direct_download_link = url + urllib.parse.quote(files_name)
                    links.append(direct_download_link)

        result = '\n'.join(links)
        return result


@Client.on_message(filters.command("index"))
def index_command(client, message):
    # Get the index link from the command message
    index_link = message.text.split('/index ')[1]
    username = "username-default"  # optional
    password = "password-default"  # optional

    payload = {"page_token": next_page_token, "page_index": 0}
    output = func(payload, index_link, username, password)

    # Send the output to the user
    client.send_message(message.chat.id, output)


app = Client("my_bot")
app.run()
