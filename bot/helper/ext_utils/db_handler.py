#!/usr/bin/env python3
from os import environ

from aiofiles import open as aiopen
from aiofiles.os import makedirs
from aiofiles.os import path as aiopath
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import PyMongoError
from time import time
from dotenv import dotenv_values

from bot import DATABASE_URL, LOGGER, aria2_options, bot_id, bot_loop, bot_name, config_dict, qbit_options, rss_dict, user_data

class DbManager:
    def __init__(self):
        self.__err = False
        self.__db = None
        self.__conn = None
        self.__connect()

    def __connect(self):
        try:
            self.__conn = AsyncIOMotorClient(DATABASE_URL)
            self.__db = self.__conn.luna
        except PyMongoError as e:
            LOGGER.error(f"Error in DB connection: {e}")
            self.__err = True

    async def db_load(self):
        if self.__err:
            return
        await self.__db.settings.config.update_one({'_id': bot_id}, {'$set': config_dict}, upsert=True)
        if await self.__db.settings.aria2c.find_one({'_id': bot_id}) is None:
            await self.__db.settings.aria2c.update_one({'_id': bot_id}, {'$set': aria2_options}, upsert=True)
        if await self.__db.settings.qbittorrent.find_one({'_id': bot_id}) is None:
            await self.__db.settings.qbittorrent.update_one({'_id': bot_id}, {'$set': qbit_options}, upsert=True)
        if await self.__db.users[bot_id].find_one():
            rows = self.__db.users[bot_id].find({})
            async for row in rows:
                uid = row['_id']
                del row['_id']
                thumb_path = f'Thumbnails/{uid}.jpg'
                rclone_path = f'tanha/{uid}.conf'
                if row.get('thumb'):
                    if not await aiopath.exists('Thumbnails'):
                        await makedirs('Thumbnails')
                    async with aiopen(thumb_path, 'wb+') as f:
                        await f.write(row['thumb'])
                    row['thumb'] = thumb_path
                if row.get('rclone'):
                    if not await aiopath.exists('tanha'):
                        await makedirs('tanha')
                    async with aiopen(rclone_path, 'wb+') as f:
                        await f.write(row['rclone'])
                    row['rclone'] = rclone_path
                user_data[uid] = row
            LOGGER.info("Users data has been imported from Database")
        if await self.__db.rss[bot_id].find_one():
            rows = self.__db.rss[bot_id].find({})
            async for row in rows:
                user_id = row['_id']
                del row['_id']
                rss_dict[user_id] = row
            LOGGER.info("Rss data has been imported from Database.")
        self.__conn.close

    async def update_config(self, dict_):
        if self.__err:
            return
        await self.__db.settings.config.update_one({'_id': bot_id}, {'$set': dict_}, upsert=True)
        self.__conn.close

    async def update_aria2(self, key, value):
        if self.__err:
            return
        await self.__db.settings.aria2c.update_one({'_id': bot_id}, {'$set': {key: value}}, upsert=True)
        self.__conn.close

    async def update_qbittorrent(self, key, value):
        if self.__err:
            return
        await self.__db.settings.qbittorrent.update_one({'_id': bot_id}, {'$set': {key: value}}, upsert=True)
        self.__conn.close

    async def update_private_file(self, path):
        if self.__err:
            return
        if await aiopath.exists(path):
            async with aiopen(path, 'rb+') as pf:
                pf_bin = await pf.read()
        else:
            pf_bin = ''
        path = path.replace('.', '__')
        await self.__db.settings.files.update_one({'_id': bot_id}, {'$set': {path: pf_bin}}, upsert=True)
        self.__conn.close

    async def update_user_data(self, user_id):
        if self.__err:
            return
        data = user_data[user_id]
        if data.get('thumb'):
            del data['thumb']
        if data.get('rclone'):
            del data['rclone']
        if data.get('token'):
            del data['token']
        if data.get('time'):
            del data['time']
        await self.__db.users[bot_id].replace_one({'_id': user_id}, data, upsert=True)
        self.__conn.close

    async def update_user_doc(self, user_id, key, path=''):
        if self.__err:
            return
        if path:
            async with aiopen(path, 'rb+') as doc:
                doc_bin = await doc.read()
        else:
            doc_bin = ''
        await self.__db.users[bot_id].update_one({'_id': user_id}, {'$set': {key: doc_bin}}, upsert=True)
        self.__conn.close

    async def get_pm_uids(self):
        if self.__err:
            return
        return [doc['_id'] async for doc in self.__db.pm_users[bot_id].find({})]
        
    async def update_pm_users(self, user_id):
        if self.__err:
            return
        if not bool(await self.__db.pm_users[bot_id].find_one({'_id': user_id})):
            await self.__db.pm_users[bot_id].insert_one({'_id': user_id})
            LOGGER.info(f'New PM User Added : {user_id}')
        self.__conn.close
        
    async def rm_pm_user(self, user_id):
        if self.__err:
            return
        await self.__db.pm_users[bot_id].delete_one({'_id': user_id})
        self.__conn.close
        
    async def rss_update_all(self):
        if self.__err:
            return
        for user_id in list(rss_dict.keys()):
            await self.__db.rss[bot_id].replace_one({'_id': user_id}, rss_dict[user_id], upsert=True)
        self.__conn.close

    async def rss_update(self, user_id):
        if self.__err:
            return
        await self.__db.rss[bot_id].replace_one({'_id': user_id}, rss_dict[user_id], upsert=True)
        self.__conn.close

    async def rss_delete(self, user_id):
        if self.__err:
            return
        await self.__db.rss[bot_id].delete_one({'_id': user_id})
        self.__conn.close

    async def add_incomplete_task(self, cid, link, tag):
        if self.__err:
            return
        await self.__db.tasks[bot_id].insert_one({'_id': link, 'cid': cid, 'tag': tag})
        self.__conn.close

    async def rm_complete_task(self, link):
        if self.__err:
            return
        await self.__db.tasks[bot_id].delete_one({'_id': link})
        self.__conn.close

    async def get_incomplete_tasks(self):
        notifier_dict = {}
        if self.__err:
            return notifier_dict
        if await self.__db.tasks[bot_id].find_one():
            rows = self.__db.tasks[bot_id].find({})
            async for row in rows:
                if row['cid'] in list(notifier_dict.keys()):
                    if row['tag'] in list(notifier_dict[row['cid']]):
                        notifier_dict[row['cid']][row['tag']].append(
                            row['_id'])
                    else:
                        notifier_dict[row['cid']][row['tag']] = [row['_id']]
                else:
                    notifier_dict[row['cid']] = {row['tag']: [row['_id']]}
        await self.__db.tasks[bot_id].drop()
        self.__conn.close
        return notifier_dict

    async def trunc_table(self, name):
        if self.__err:
            return
        await self.__db[name][bot_id].drop()
        self.__conn.close

    async def add_download_url(self, url: str, tag: str):
        if self.__err:
            return
        download = {'_id': url, 'tag': tag, 'botname': bot_name}
        await self.__db.download_links.update_one({'_id': url}, {'$set': download}, upsert=True)
        self.__conn.close

    async def check_download(self, url: str):
        if self.__err:
            return
        exist = await self.__db.download_links.find_one({'_id': url})
        self.__conn.close
        return exist

    async def clear_download_links(self, botName=None):
        if self.__err:
            return
        if not botName:
            botName = bot_name
        await self.__db.download_links.delete_many({'botname': botName})
        self.__conn.close

    async def remove_download(self, url: str):
        if self.__err:
            return
        await self.__db.download_links.delete_one({'_id': url})
        self.__conn.close

    async def update_user_tdata(self, user_id, token, time):
        if self.__err:
            return
        await self.__db.access_token.update_one({'_id': user_id}, {'$set': {'token': token, 'time': time}}, upsert=True)
        self.__conn.close

    async def update_user_token(self, user_id, token):
        if self.__err:
            return
        await self.__db.access_token.update_one({'_id': user_id}, {'$set': {'token': token}}, upsert=True)
        self.__conn.close

    async def get_token_expire_time(self, user_id):
        if self.__err:
            return None
        user_data = await self.__db.access_token.find_one({'_id': user_id})
        if user_data:
            return user_data.get('time')
        self.__conn.close
        return None

    async def get_user_token(self, user_id):
        if self.__err:
            return None
        user_data = await self.__db.access_token.find_one({'_id': user_id})
        if user_data:
            return user_data.get('token')
        self.__conn.close
        return None

    async def delete_all_access_tokens(self):
        if self.__err:
            return
        await self.__db.access_token.delete_many({})
        self.__conn.close

if DATABASE_URL:
    bot_loop.run_until_complete(DbManager().db_load())