import requests
from hashlib import sha256
from http.cookiejar import MozillaCookieJar
from json import loads
from os import path
from re import findall, match, search
from threading import Thread
from time import sleep
from urllib.parse import parse_qs, quote, urlparse
from uuid import uuid4

from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from lk21 import Bypass
from lxml.etree import HTML
from requests import Session, post
from requests import session as req_session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot import config_dict, LOGGER
from bot.helper.ext_utils.bot_utils import get_readable_time, is_share_link, text_size_to_bytes
from bot.helper.ext_utils.exceptions import DirectDownloadLinkException
from bot.helper.ext_utils.help_messages import PASSWORD_ERROR_MESSAGE


terabox_domain = ['terabox', 'nephobox', '4funbox', 'mirrobox', 'momerybox', 'teraboxapp', '1024tera']
streamtape_domain = ['streamtape.com', 'streamtape.co', 'streamtape.cc', 'streamtape.to', 'streamtape.net', 'streamta.pe', 'streamtape.xyz']
doods_domain = ['dood.watch', 'doodstream.com', 'dood.to', 'dood.so', 'dood.cx', 'dood.la', 'dood.ws', 'dood.sh', 'doodstream.co', 'dood.pm', 'dood.wf', 'dood.re', 'dood.video', 'dooood.com', 'dood.yt', 'dood.stream', 'doods.pro']
_caches = {}


def direct_link_generator(link):
    domain = urlparse(link).hostname
    if not domain:
        raise DirectDownloadLinkException("ERROR: Invalid URL")
    if 'youtube.com' in domain or 'youtu.be' in domain:
        raise DirectDownloadLinkException("ERROR: Use ytdl cmds for Youtube links")
    elif 'mediafire.com' in domain:
        return mediafire(link)
    elif 'uptobox.com' in domain:
        return uptobox(link)
    elif 'osdn.net' in domain:
        return osdn(link)
    elif 'github.com' in domain:
        return github(link)
    elif 'hxfile.co' in domain:
        return hxfile(link)
    elif '1drv.ms' in domain:
        return onedrive(link)
    elif 'pixeldrain.com' in domain:
        return pixeldrain(link)
    elif 'antfiles.com' in domain:
        return antfiles(link)
    elif any(x in domain for x in streamtape_domain):
        return streamtape(link)
    elif 'racaty' in domain:
        return racaty(link)
    elif '1fichier.com' in domain:
        return fichier(link)
    elif 'solidfiles.com' in domain:
        return solidfiles(link)
    elif 'krakenfiles.com' in domain:
        return krakenfiles(link)
    elif 'upload.ee' in domain:
        return uploadee(link)
    elif 'akmfiles' in domain:
        return akmfiles(link)
    elif 'linkbox' in domain:
        return linkbox(link)
    elif 'shrdsk' in domain:
        return shrdsk(link)
    elif 'letsupload.io' in domain:
        return letsupload(link)
    elif 'gofile.io' in domain:
        return gofile(link)
    elif 'send.cm' in domain:
        return send_cm(link)
    elif 'easyupload.io' in domain:
        return easyupload(link)
    elif 'hubdrive' in domain:
        return hubdrive(link)
    elif any(x in domain for x in doods_domain):
        return doods(link)
    elif any(x in domain for x in ['wetransfer.com', 'we.tl']):
        return wetransfer(link)
    elif any(x in domain for x in terabox_domain):
        return terabox(link)
    elif any(x in domain for x in ['filelions.com', 'filelions.live', 'filelions.to']):
        return filelions(link)
    elif is_share_link(link):
        if 'gdtot' in domain:
            return gdtot(link)
        elif 'filepress' in domain:
            return filepress(link)
        else:
            return sharer_scraper(link)
    else:
        raise DirectDownloadLinkException(f'EROOR: No Direct link function found for {link}')

def get_captcha_token(session, params):
    recaptcha_api = 'https://www.google.com/recaptcha/api2'
    res = session.get(f'{recaptcha_api}/anchor', params=params)
    anchor_html = HTML(res.text)
    if not (anchor_token:= anchor_html.xpath('//input[@id="recaptcha-token"]/@value')):
        return
    params['c'] = anchor_token[0]
    params['reason'] = 'q'
    res = session.post(f'{recaptcha_api}/reload', params=params)
    if token := findall(r'"rresp","(.*?)"', res.text):
        return token[0]

def uptobox(url):
    try:
        link = findall(r'\bhttps?://.*uptobox\.com\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No Uptobox links found")
    if link := findall(r'\bhttps?://.*\.uptobox\.com/dl\S+', url):
        return link[0]
    with create_scraper() as session:
        try:
            file_id = findall(r'\bhttps?://.*uptobox\.com/(\w+)', url)[0]
            if UPTOBOX_TOKEN := config_dict['UPTOBOX_TOKEN']:
                file_link = f'https://uptobox.com/api/link?token={UPTOBOX_TOKEN}&file_code={file_id}'
            else:
                file_link = f'https://uptobox.com/api/link?file_code={file_id}'
            res = session.get(file_link).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        if res['statusCode'] == 0:
            return res['data']['dlLink']
        elif res['statusCode'] == 16:
            sleep(1)
            waiting_token = res["data"]["waitingToken"]
            sleep(res["data"]["waiting"])
        elif res['statusCode'] == 39:
            raise DirectDownloadLinkException(
                f"ERROR: Uptobox is being limited please wait {get_readable_time(res['data']['waiting'])}")
        else:
            raise DirectDownloadLinkException(f"ERROR: {res['message']}")
        try:
            res = session.get(f"{file_link}&waitingToken={waiting_token}").json()
            return res['data']['dlLink']
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")


def mediafire(url, session=None):
    if '/folder/' in url:
        return mediafireFolder(url)
    if final_link := findall(r'https?:\/\/download\d+\.mediafire\.com\/\S+\/\S+\/\S+', url):
        return final_link[0]
    if session is None:
        session = Session()
    try:
        html = HTML(session.get(url).text)
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    if error:= html.xpath('//p[@class="notranslate"]/text()'):
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {error[0]}")
    if not (final_link := html.xpath("//a[@id='downloadButton']/@href")):
        session.close()
        raise DirectDownloadLinkException("ERROR: No links found in this page Try Again")
    if final_link[0].startswith('//'):
        return mediafire(f'https://{final_link[0][2:]}', session)
    session.close()
    return final_link[0]


def osdn(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        if not (direct_link:= html.xapth('//a[@class="mirror_link"]/@href')):
            raise DirectDownloadLinkException("ERROR: Direct link not found")
        return f'https://osdn.net{direct_link[0]}'


def github(url):
    try:
        findall(r'\bhttps?://.*github\.com.*releases\S+', url)[0]
    except IndexError:
        raise DirectDownloadLinkException("No GitHub Releases links found")
    with create_scraper() as session:
        _res = session.get(url, stream=True, allow_redirects=False)
        if 'location' in _res.headers:
            return _res.headers["location"]
        raise DirectDownloadLinkException("ERROR: Can't extract the link")


def hxfile(url):
    try:
        return Bypass().bypass_filesIm(url)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")


def letsupload(url):
    with create_scraper() as session:
        try:
            res = session.post(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if direct_link := findall(r"(https?://letsupload\.io\/.+?)\'", res.text):
            return direct_link[0]
        else:
            raise DirectDownloadLinkException('ERROR: Direct Link not found')


def onedrive(link):
    with create_scraper() as session:
        try:
            link = session.get(link).url
            parsed_link = urlparse(link)
            link_data = parse_qs(parsed_link.query)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        if not link_data:
            raise DirectDownloadLinkException("ERROR: Unable to find link_data")
        folder_id = link_data.get('resid')
        if not folder_id:
            raise DirectDownloadLinkException('ERROR: folder id not found')
        folder_id = folder_id[0]
        authkey = link_data.get('authkey')
        if not authkey:
            raise DirectDownloadLinkException('ERROR: authkey not found')
        authkey = authkey[0]
        boundary = uuid4()
        headers = {'content-type': f'multipart/form-data;boundary={boundary}'}
        data = f'--{boundary}\r\nContent-Disposition: form-data;name=data\r\nPrefer: Migration=EnableRedirect;FailOnMigratedFiles\r\nX-HTTP-Method-Override: GET\r\nContent-Type: application/json\r\n\r\n--{boundary}--'
        try:
            resp = session.get( f'https://api.onedrive.com/v1.0/drives/{folder_id.split("!", 1)[0]}/items/{folder_id}?$select=id,@content.downloadUrl&ump=1&authKey={authkey}', headers=headers, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if "@content.downloadUrl" not in resp:
        raise DirectDownloadLinkException('ERROR: Direct link not found')
    return resp['@content.downloadUrl']


def pixeldrain(url):
    url = url.strip("/ ")
    file_id = url.split("/")[-1]
    if url.split("/")[-2] == "l":
        info_link = f"https://pixeldrain.com/api/list/{file_id}"
        dl_link = f"https://pixeldrain.com/api/list/{file_id}/zip?download"
    else:
        info_link = f"https://pixeldrain.com/api/file/{file_id}/info"
        dl_link = f"https://pixeldrain.com/api/file/{file_id}?download"
    with create_scraper() as session:
        try:
            resp = session.get(info_link).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    if resp["success"]:
        return dl_link
    else:
        raise DirectDownloadLinkException(
            f"ERROR: Cant't download due {resp['message']}.")


def antfiles(url):
    try:
        return Bypass().bypass_antfiles(url)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")


def streamtape(url):
    splitted_url = url.split("/")
    _id = splitted_url[4] if len(splitted_url) >= 6 else splitted_url[-1]
    try:
        with Session() as session:
            html = HTML(session.get(url).text)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    if not (script := html.xpath("//script[contains(text(),'ideoooolink')]/text()")):
        raise DirectDownloadLinkException("ERROR: requeries script not found")
    if not (link := findall(r"(&expires\S+)'", script[0])):
        raise DirectDownloadLinkException("ERROR: Download link not found")
    return f"https://streamtape.com/get_video?id={_id}{link[-1]}"


def racaty(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            json_data = {
                'op': 'download2',
                'id': url.split('/')[-1]
            }
            html = HTML(session.post(url, data=json_data).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if (direct_link := html.xpath("//a[@id='uniqueExpirylink']/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Direct link not found')


def fichier(link):
    regex = r"^([http:\/\/|https:\/\/]+)?.*1fichier\.com\/\?.+"
    gan = match(regex, link)
    if not gan:
        raise DirectDownloadLinkException(
            "ERROR: The link you entered is wrong!")
    if "::" in link:
        pswd = link.split("::")[-1]
        url = link.split("::")[-2]
    else:
        pswd = None
        url = link
    cget = create_scraper().request
    try:
        if pswd is None:
            req = cget('post', url)
        else:
            pw = {"pass": pswd}
            req = cget('post', url, data=pw)
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    if req.status_code == 404:
        raise DirectDownloadLinkException("ERROR: File not found/The link you entered is wrong!")
    html = HTML(req.text)
    if dl_url:= html.xpath('//a[@class="ok btn-general btn-orange"]/@href'):
        return dl_url[0]
    if not (ct_warn := html.xpath('//div[@class="ct_warn"]')):
        raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")
    if len(ct_warn) == 3:
        str_2 = ct_warn[-1].text
        if "you must wait" in str_2.lower():
            if numbers := [int(word) for word in str_2.split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "protect access" in str_2.lower():
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(link)}")
        else:
            raise DirectDownloadLinkException("ERROR: Failed to generate Direct Link from 1fichier!")
    elif len(ct_warn) == 4:
        str_1 = ct_warn[-2].text
        str_3 = ct_warn[-1].text
        if "you must wait" in str_1.lower():
            if numbers := [int(word) for word in str_1.split() if word.isdigit()]:
                raise DirectDownloadLinkException(f"ERROR: 1fichier is on a limit. Please wait {numbers[0]} minute.")
            else:
                raise DirectDownloadLinkException("ERROR: 1fichier is on a limit. Please wait a few minutes/hour.")
        elif "bad password" in str_3.lower():
            raise DirectDownloadLinkException("ERROR: The password you entered is wrong!")
        else:
            raise DirectDownloadLinkException("ERROR: Error trying to generate Direct Link from 1fichier!")


def solidfiles(url):
    with create_scraper() as session:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_9_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/36.0.1985.125 Safari/537.36'
            }
            pageSource = session.get(url, headers=headers).text
            mainOptions = str(
                search(r'viewerOptions\'\,\ (.*?)\)\;', pageSource).group(1))
            return loads(mainOptions)["downloadUrl"]
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")


def krakenfiles(url):
    with Session() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        html = HTML(_res.text)
        if post_url:= html.xpath('//form[@id="dl-form"]/@action'):
            post_url = f'https:{post_url[0]}'
        else:
            raise DirectDownloadLinkException('ERROR: Unable to find post link.')
        if token:= html.xpath('//input[@id="dl-token"]/@value'):
            data = {'token': token[0]}
        else:
            raise DirectDownloadLinkException('ERROR: Unable to find token for post.')
        try:
            _json = session.post(post_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__} While send post request')
    if _json['status'] != 'ok':
        raise DirectDownloadLinkException("ERROR: Unable to find download after post request")
    return _json['url']


def uploadee(url):
    with create_scraper() as session:
        try:
            html = HTML(session.get(url).text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if link := html.xpath("//a[@id='d_l']/@href"):
        return link[0]
    else:
        raise DirectDownloadLinkException("ERROR: Direct Link not found")


def terabox(url):
    if not path.isfile('terabox.txt'):
        raise DirectDownloadLinkException("ERROR: terabox.txt not found")
    try:
        jar = MozillaCookieJar('terabox.txt')
        jar.load()
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
    cookies = {}
    for cookie in jar:
        cookies[cookie.name] = cookie.value
    details = {'contents':[], 'title': '', 'total_size': 0}
    details["header"] = ' '.join(f'{key}: {value}' for key, value in cookies.items())

    def __fetch_links(session, dir_='', folderPath=''):
        params = {
            'app_id': '250528',
            'jsToken': jsToken,
            'shorturl': shortUrl
            }
        if dir_:
            params['dir'] = dir_
        else:
            params['root'] = '1'
        try:
            _json = session.get("https://www.1024tera.com/share/list", params=params, cookies=cookies).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if _json['errno'] not in [0, '0']:
            if 'errmsg' in _json:
                raise DirectDownloadLinkException(f"ERROR: {_json['errmsg']}")
            else:
                raise DirectDownloadLinkException('ERROR: Something went wrong!')

        if "list" not in _json:
            return
        contents = _json["list"]
        for content in contents:
            if content['isdir'] in ['1', 1]:
                if not folderPath:
                    if not details['title']:
                        details['title'] = content['server_filename']
                        newFolderPath = path.join(details['title'])
                    else:
                        newFolderPath = path.join(details['title'], content['server_filename'])
                else:
                    newFolderPath = path.join(folderPath, content['server_filename'])
                __fetch_links(session, content['path'], newFolderPath)
            else:
                if not folderPath:
                    if not details['title']:
                        details['title'] = content['server_filename']
                    folderPath = details['title']
                item = {
                    'url': content['dlink'],
                    'filename': content['server_filename'],
                    'path' : path.join(folderPath),
                }
                if 'size' in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details['total_size'] += size
                details['contents'].append(item)

    with Session() as session:
        try:
            _res = session.get(url, cookies=cookies)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if jsToken := findall(r'window\.jsToken.*%22(.*)%22', _res.text):
            jsToken = jsToken[0]
        else:
            raise DirectDownloadLinkException('ERROR: jsToken not found!.')
        shortUrl = parse_qs(urlparse(_res.url).query).get('surl')
        if not shortUrl:
            raise DirectDownloadLinkException("ERROR: Could not find surl")
        try:
            __fetch_links(session)
        except Exception as e:
            raise DirectDownloadLinkException(e)
    if len(details['contents']) == 1:
        return details['contents'][0]['url']
    return details

def filepress(url):
    try:
        cget = requests.get(url, allow_redirects=False)
        if 'location' in cget.headers:
            url = cget.headers['location']
        raw = urlparse(url)
        json_data = {
            'id': raw.path.split('/')[-1],
            'method': 'publicDownlaod',}
        headers = {'Referer': f'{raw.scheme}://{raw.hostname}'}
        resp = requests.post(f'{raw.scheme}://{raw.hostname}/api/file/downlaod/', headers=headers, json=json_data)
        d_id = resp.json()
        if d_id.get('data', False):
            dl_link = f"https://drive.google.com/uc?id={d_id['data']}&export=download"
            dl_resp = requests.get(dl_link)
            parsed = BeautifulSoup(dl_resp.content, 'html.parser').find('span')
            combined = str(parsed).rsplit('(', maxsplit=1)
            name, size = combined[0], combined[1].replace(')', '') + 'B'
        del json_data['method']
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    return dl_link

def gdtot(url):
    cget = create_scraper().request
    try:
        res = cget('GET', f'https://gdtot.pro/file/{url.split("/")[-1]}')
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    token_url = HTML(res.text).xpath(
        "//a[contains(@class,'inline-flex items-center justify-center')]/@href")
    if not token_url:
        try:
            url = cget('GET', url).url
            p_url = urlparse(url)
            res = cget(
                "GET", f"{p_url.scheme}://{p_url.hostname}/ddl/{url.split('/')[-1]}")
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if (drive_link := findall(r"myDl\('(.*?)'\)", res.text)) and "drive.google.com" in drive_link[0]:
            return drive_link[0]
        else:
            raise DirectDownloadLinkException(
                'ERROR: Drive Link not found, Try in your broswer')
    token_url = token_url[0]
    try:
        token_page = cget('GET', token_url)
    except Exception as e:
        raise DirectDownloadLinkException(
            f'ERROR: {e.__class__.__name__} with {token_url}')
    path = findall('\("(.*?)"\)', token_page.text)
    if not path:
        raise DirectDownloadLinkException('ERROR: Cannot bypass this')
    path = path[0]
    raw = urlparse(token_url)
    final_url = f'{raw.scheme}://{raw.hostname}{path}'
    return sharer_scraper(final_url)


def sharer_scraper(url):
    cget = create_scraper().request
    try:
        url = cget('GET', url).url
        raw = urlparse(url)
        header = {
            "useragent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10"}
        res = cget('GET', url, headers=header)
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    key = findall('"key",\s+"(.*?)"', res.text)
    if not key:
        raise DirectDownloadLinkException("ERROR: Key not found!")
    key = key[0]
    if not HTML(res.text).xpath("//button[@id='drc']"):
        raise DirectDownloadLinkException("ERROR: This link don't have direct download button")
    boundary = uuid4()
    headers = {
        'Content-Type': f'multipart/form-data; boundary=----WebKitFormBoundary{boundary}',
        'x-token': raw.hostname,
        'useragent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US) AppleWebKit/534.10 (KHTML, like Gecko) Chrome/7.0.548.0 Safari/534.10'
    }

    data = f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action"\r\n\r\ndirect\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="key"\r\n\r\n{key}\r\n' \
        f'------WebKitFormBoundary{boundary}\r\nContent-Disposition: form-data; name="action_token"\r\n\r\n\r\n' \
        f'------WebKitFormBoundary{boundary}--\r\n'
    try:
        res = cget("POST", url, cookies=res.cookies,
                   headers=headers, data=data).json()
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if "url" not in res:
        raise DirectDownloadLinkException(
            'ERROR: Drive Link not found, Try in your broswer')
    if "drive.google.com" in res["url"]:
        return res["url"]
    try:
        res = cget('GET', res["url"])
    except Exception as e:
        raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if (drive_link := HTML(res.text).xpath("//a[contains(@class,'btn')]/@href")) and "drive.google.com" in drive_link[0]:
        return drive_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Drive Link not found, Try in your broswer')


def wetransfer(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            splited_url = url.split('/')
            json_data = {
                'security_hash': splited_url[-1],
                'intent': 'entire_transfer'
            }
            res = session.post(f'https://wetransfer.com/api/v4/transfers/{splited_url[-2]}/download', json=json_data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if "direct_link" in res:
        return res["direct_link"]
    elif "message" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['message']}")
    elif "error" in res:
        raise DirectDownloadLinkException(f"ERROR: {res['error']}")
    else:
        raise DirectDownloadLinkException("ERROR: cannot find direct link")


def akmfiles(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            json_data = {
                'op': 'download2',
                'id': url.split('/')[-1]
            }
            res = session.post('POST', url, data=json_data)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if (direct_link := HTML(res.text).xpath("//a[contains(@class,'btn btn-dow')]/@href")):
        return direct_link[0]
    else:
        raise DirectDownloadLinkException('ERROR: Direct link not found')


def shrdsk(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            res = session.get(f'https://us-central1-affiliate2apk.cloudfunctions.net/get_data?shortid={url.split("/")[-1]}')
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if res.status_code != 200:
        raise DirectDownloadLinkException(f'ERROR: Status Code {res.status_code}')
    res = res.json()
    if ("type" in res and res["type"].lower() == "upload" and "video_url" in res):
        return res["video_url"]
    raise DirectDownloadLinkException("ERROR: cannot find direct link")


def linkbox(url):
    with create_scraper() as session:
        try:
            url = session.get(url).url
            res = session.get(f'https://www.linkbox.to/api/file/detail?itemId={url.split("/")[-1]}').json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if 'data' not in res:
        raise DirectDownloadLinkException('ERROR: Data not found!!')
    data = res['data']
    if not data:
        raise DirectDownloadLinkException('ERROR: Data is None!!')
    if 'itemInfo' not in data:
        raise DirectDownloadLinkException('ERROR: itemInfo not found!!')
    itemInfo = data['itemInfo']
    if 'url' not in itemInfo:
        raise DirectDownloadLinkException('ERROR: url not found in itemInfo!!')
    if "name" not in itemInfo:
        raise DirectDownloadLinkException('ERROR: Name not found in itemInfo!!')
    name = quote(itemInfo["name"])
    raw = itemInfo['url'].split("/", 3)[-1]
    return f'https://wdl.nuplink.net/{raw}&filename={name}'


def gofile(url):
    try:
        if "::" in url:
            _password = url.split("::")[-1]
            _password = sha256(_password.encode("utf-8")).hexdigest()
            url = url.split("::")[-2]
        else:
            _password = ''
        _id = url.split("/")[-1]
    except Exception as e:
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")

    def __get_token(session):
        if 'gofile_token' in _caches:
            __url = f"https://api.gofile.io/getAccountDetails?token={_caches['gofile_token']}"
        else:
            __url = 'https://api.gofile.io/createAccount'
        try:
            __res = session.get(__url, verify=False).json()
            if __res["status"] != 'ok':
                if 'gofile_token' in _caches:
                    del _caches['gofile_token']
                return __get_token(session)
            _caches['gofile_token'] = __res["data"]["token"]
            return _caches['gofile_token']
        except Exception as e:
            raise e

    def __fetch_links(session, _id, folderPath=''):
        _url = f"https://api.gofile.io/getContent?contentId={_id}&token={token}&websiteToken=7fd94ds12fds4&cache=true"
        if _password:
            _url += f"&password={_password}"
        try:
            _json = session.get(_url, verify=False).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        if _json['status'] in 'error-passwordRequired':
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}")
        if _json['status'] in 'error-passwordWrong':
            raise DirectDownloadLinkException('ERROR: This password is wrong !')
        if _json['status'] in 'error-notFound':
            raise DirectDownloadLinkException("ERROR: File not found on gofile's server")
        if _json['status'] in 'error-notPublic':
            raise DirectDownloadLinkException("ERROR: This folder is not public")

        data = _json["data"]

        if not details['title']:
            details['title'] = data['name'] if data['type'] == "folder" else _id

        contents = data["contents"]
        for content in contents.values():
            if content["type"] == "folder":
                if not content['public']:
                    continue
                if not folderPath:
                    newFolderPath = path.join(details['title'], content["name"])
                else:
                    newFolderPath = path.join(folderPath, content["name"])
                __fetch_links(session, content["id"], newFolderPath)
            else:
                if not folderPath:
                    folderPath = details['title']
                item = {
                    "path": path.join(folderPath),
                    "filename": content["name"],
                    "url": content["link"],
                }
                if 'size' in content:
                    size = content["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details['total_size'] += size
                details['contents'].append(item)

    details = {'contents':[], 'title': '', 'total_size': 0}
    with Session() as session:
        try:
            token = __get_token(session)
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__}")
        details["header"] = f'Cookie: accountToken={token}'
        try:
            __fetch_links(session, _id)
        except Exception as e:
            raise DirectDownloadLinkException(e)

    if len(details['contents']) == 1:
        return (details['contents'][0]['url'], details['header'])
    return details

def mediafireFolder(url):
    try:
        raw = url.split('/', 4)[-1]
        folderkey = raw.split('/', 1)[0]
        folderkey = folderkey.split(',')
    except:
        raise DirectDownloadLinkException('ERROR: Could not parse ')
    if len(folderkey) == 1:
        folderkey = folderkey[0]
    details = {'contents': [], 'title': '', 'total_size': 0, 'header': ''}
    
    session = req_session()
    adapter = HTTPAdapter(max_retries=Retry(
        total=10, read=10, connect=10, backoff_factor=0.3))
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session = create_scraper(
        browser={"browser": "firefox", "platform": "windows", "mobile": False},
        delay=10,
        sess=session,
    )
    folder_infos = []

    def __get_info(folderkey):
        try:
            if isinstance(folderkey, list):
                folderkey = ','.join(folderkey)
            _json = session.post('https://www.mediafire.com/api/1.5/folder/get_info.php', data={
                'recursive': 'yes',
                'folder_key': folderkey,
                'response_format': 'json'
            }).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__} While getting info")
        _res = _json['response']
        if 'folder_infos' in _res:
            folder_infos.extend(_res['folder_infos'])
        elif 'folder_info' in _res:
            folder_infos.append(_res['folder_info'])
        elif 'message' in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        else:
            raise DirectDownloadLinkException("ERROR: something went wrong!")


    try:
        __get_info(folderkey)
    except Exception as e:
        raise DirectDownloadLinkException(e)

    details['title'] = folder_infos[0]["name"]

    def __scraper(url):
        try:
            html = HTML(session.get(url).text)
        except:
            return
        if final_link := html.xpath("//a[@id='downloadButton']/@href"):
            return final_link[0]

    def __get_content(folderKey, folderPath='', content_type='folders'):
        try:
            params = {
                'content_type': content_type,
                'folder_key': folderKey,
                'response_format': 'json',
            }
            _json = session.get('https://www.mediafire.com/api/1.5/folder/get_content.php', params=params).json()
        except Exception as e:
            raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__} While getting content")
        _res = _json['response']
        if 'message' in _res:
            raise DirectDownloadLinkException(f"ERROR: {_res['message']}")
        _folder_content = _res['folder_content']
        if content_type == 'folders':
            folders = _folder_content['folders']
            for folder in folders:
                if folderPath:
                    newFolderPath = path.join(folderPath, folder["name"])
                else:
                    newFolderPath = path.join(folder["name"])
                __get_content(folder['folderkey'], newFolderPath)
            __get_content(folderKey, folderPath, 'files')
        else:
            files = _folder_content['files']
            for file in files:
                item = {}
                if not (_url := __scraper(file['links']['normal_download'])):
                    continue
                item['filename'] = file["filename"]
                if not folderPath:
                    folderPath = details['title']
                item['path'] = path.join(folderPath)
                item['url'] = _url
                if 'size' in file:
                    size = file["size"]
                    if isinstance(size, str) and size.isdigit():
                        size = float(size)
                    details['total_size'] += size
                details['contents'].append(item)
    try:
        threads = []
        for folder in folder_infos:
            thread = Thread(target=__get_content, args=(folder['folderkey'], folder['name']))
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(e)
    session.close()
    if len(details['contents']) == 1:
        return (details['contents'][0]['url'], details['header'])
    return details

def cf_bypass(url):
    "DO NOT ABUSE THIS"
    try:
        data = {
            "cmd": "request.get",
            "url": url,
            "maxTimeout": 60000
        }
        _json = post("https://cf.jmdkh.eu.org/v1", headers={"Content-Type": "application/json"}, json=data).json()
        if _json['status'] == 'ok':
            return _json['solution']["response"]
    except Exception as e:
        e
    raise DirectDownloadLinkException("ERROR: Con't bypass cloudflare")

def send_cm_file(url, file_id=None):
    if "::" in url:
        _password = url.split("::")[-1]
        url = url.split("::")[-2]
    else:
        _password = ''
    _passwordNeed = False
    with create_scraper() as session:
        if file_id is None:
            try:
                html = HTML(session.get(url).text)
            except Exception as e:
                raise DirectDownloadLinkException(
                    f'ERROR: {e.__class__.__name__}')
            if html.xpath("//input[@name='password']"):
                _passwordNeed = True
            if not (file_id := html.xpath("//input[@name='id']/@value")):
                raise DirectDownloadLinkException('ERROR: file_id not found')
        try:
            data = {'op': 'download2', 'id': file_id}
            if _password and _passwordNeed:
                data["password"] = _password
            _res = session.post('https://send.cm/', data=data, allow_redirects=False)
            if 'Location' in _res.headers:
                return (_res.headers['Location'], 'Referer: https://send.cm/')
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        if _passwordNeed:
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}")
        raise DirectDownloadLinkException("ERROR: Direct link not found")

def send_cm(url):
    if '/d/' in url:
        return send_cm_file(url)
    elif '/s/' not in url:
        file_id = url.split("/")[-1]
        return send_cm_file(url, file_id)
    splitted_url = url.split("/")
    details = {'contents': [], 'title': '', 'total_size': 0,
               'header': 'Referer: https://send.cm/'}
    if len(splitted_url) == 5:
        url += '/'
        splitted_url = url.split("/")
    if len(splitted_url) >= 7:
        details['title'] = splitted_url[5]
    else:
        details['title'] = splitted_url[-1]
    session = Session()

    def __collectFolders(html):
        folders = []
        folders_urls = html.xpath('//h6/a/@href')
        folders_names = html.xpath('//h6/a/text()')
        for folders_url, folders_name in zip(folders_urls, folders_names):
            folders.append({'folder_link':folders_url.strip(),'folder_name':folders_name.strip()})
        return folders

    def __getFile_link(file_id):
        try:
            _res = session.post(
                'https://send.cm/', data={'op': 'download2', 'id': file_id}, allow_redirects=False)
            if 'Location' in _res.headers:
                return _res.headers['Location']
        except:
            pass

    def __getFiles(html):
        files = []
        hrefs = html.xpath('//tr[@class="selectable"]//a/@href')
        file_names = html.xpath('//tr[@class="selectable"]//a/text()')
        sizes = html.xpath('//tr[@class="selectable"]//span/text()')
        for href, file_name, size_text in zip(hrefs, file_names, sizes):
            files.append({'file_id':href.split('/')[-1], 'file_name':file_name.strip(), 'size':text_size_to_bytes(size_text.strip())})
        return files

    def __writeContents(html_text, folderPath=''):
        folders = __collectFolders(html_text)
        for folder in folders:
            _html = HTML(cf_bypass(folder['folder_link']))
            __writeContents(_html, path.join(folderPath, folder['folder_name']))
        files = __getFiles(html_text)
        for file in files:
            if not (link := __getFile_link(file['file_id'])):
                continue
            item = {'url': link,
                    'filename': file['filename'], 'path': folderPath}
            details['total_size'] += file['size']
            details['contents'].append(item)
    try:
        mainHtml = HTML(cf_bypass(url))
    except DirectDownloadLinkException as e:
        session.close()
        raise e
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__} While getting mainHtml")
    try:
        __writeContents(mainHtml, details['title'])
    except DirectDownloadLinkException as e:
        session.close()
        raise e
    except Exception as e:
        session.close()
        raise DirectDownloadLinkException(f"ERROR: {e.__class__.__name__} While writing Contents")
    session.close()
    if len(details['contents']) == 1:
        return (details['contents'][0]['url'], details['header'])
    return details

def doods(url):
    if "/e/" in url:
        url = url.replace("/e/", "/d/")
    parsed_url = urlparse(url)
    with create_scraper() as session:
        try:
            _res = session.get(url)
            html = HTML(_res.text)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__} While fetching token link')
        if not (link := html.xpath("//div[@class='download-content']//a/@href")):
            raise DirectDownloadLinkException('ERROR: Token Link not found')
        link = f'{parsed_url.scheme}://{parsed_url.hostname}/{link[0]}'
        try:
            _res = session.get(link)
        except Exception as e:
            raise DirectDownloadLinkException(
                f'ERROR: {e.__class__.__name__} While fetching download link')
    if not (link := search(r"window\.open\('(\S+)'", _res.text)):
        raise DirectDownloadLinkException("ERROR: Download link not found try again")
    return (link.group(1), f'Referer: {parsed_url.scheme}://{parsed_url.hostname}/')


def hubdrive(url):
    try:
        rs = Session()
        resp = rs.get(url)
        title = findall(r'>(.*?)<\/h4>', resp.text)[0]
        size = findall(r'>(.*?)<\/td>', resp.text)[1]
        p_url = urlparse(url)
        js_query = rs.post(f"{p_url.scheme}://{p_url.hostname}/ajax.php?ajax=direct-download", data={'id': str(url.split('/')[-1])}, headers={'x-requested-with': 'XMLHttpRequest'}).json()
        if str(js_query['code']) == '200':
            dlink = f"{p_url.scheme}://{p_url.hostname}{js_query['file']}"
            res = rs.get(dlink)
            soup = BeautifulSoup(res.text, 'html.parser')
            gd_data = soup.select('a[class="btn btn-primary btn-user"]')
            gd_link = gd_data[0]['href']
        return gd_link
    except Exception as e:
        raise DirectDownloadLinkException('ERROR: Download link not found try again')


def easyupload(url):
    if "::" in url:
        _password = url.split("::")[-1]
        url = url.split("::")[-2]
    else:
        _password = ''
    file_id = url.split("/")[-1]
    with create_scraper() as session:
        try:
            _res = session.get(url)
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
        first_page_html = HTML(_res.text)
        if first_page_html.xpath("//h6[contains(text(),'Password Protected')]") and not _password:
            raise DirectDownloadLinkException(f"ERROR:\n{PASSWORD_ERROR_MESSAGE.format(url)}")
        if not (match := search(r'https://eu(?:[1-9][0-9]?|100)\.easyupload\.io/action\.php', _res.text)):
            raise DirectDownloadLinkException("ERROR: Failed to get server for EasyUpload Link")
        action_url = match.group()
        session.headers.update({'referer': 'https://easyupload.io/'})
        recaptcha_params = {
            'k': '6LfWajMdAAAAAGLXz_nxz2tHnuqa-abQqC97DIZ3',
            'ar': '1',
            'co': 'aHR0cHM6Ly9lYXN5dXBsb2FkLmlvOjQ0Mw..',
            'hl': 'en',
            'v': '0hCdE87LyjzAkFO5Ff-v7Hj1',
            'size': 'invisible',
            'cb': 'c3o1vbaxbmwe'
        }
        if not (captcha_token :=get_captcha_token(session, recaptcha_params)):
            raise DirectDownloadLinkException('ERROR: Captcha token not found')
        try:
            data = {'type': 'download-token',
                    'url': file_id,
                    'value': _password,
                    'captchatoken': captcha_token,
                    'method': 'regular'}
            json_resp = session.post(url=action_url, data=data).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if 'download_link' in json_resp:
        return json_resp['download_link']
    elif 'data' in json_resp:
        raise DirectDownloadLinkException(f"ERROR: Failed to generate direct link due to {json_resp['data']}")
    raise DirectDownloadLinkException("ERROR: Failed to generate direct link from EasyUpload.")

def filelions(url):
    if not config_dict['FILELION_API']:
        raise DirectDownloadLinkException('ERROR: FILELION_API is not provided get it from https://filelions.com/?op=my_account')
    file_code = url.split('/')[-1]
    quality = ''
    if bool(file_code.endswith(('_o', '_h', '_n', '_l'))):
        spited_file_code = file_code.rsplit('_', 1)
        quality = spited_file_code[1]
        file_code = spited_file_code[0]
    with Session() as session:
        try:
            _res = session.get('https://api.filelions.com/api/file/direct_link', params={'key': config_dict['FILELION_API'], 'file_code': file_code, 'hls': '1'}).json()
        except Exception as e:
            raise DirectDownloadLinkException(f'ERROR: {e.__class__.__name__}')
    if _res['status'] != 200:
        raise DirectDownloadLinkException(f"ERROR: {_res['msg']}")
    result = _res['result']
    if not result['versions']:
        raise DirectDownloadLinkException("ERROR: No versions available")
    error = '\nProvide a quality to download the video\nAvailable Quality:'
    for version in result['versions']:
        if quality == version['name']:
            return version['url']
        elif version['name'] == 'l':
            error += f"\nLow"
        elif version['name'] == 'n':
            error += f"\nNormal"
        elif version['name'] == 'o':
            error += f"\nOriginal"
        elif version['name'] == "h":
            error += f"\nHD"
        error +=f" <code>{url}_{version['name']}</code>"
    raise DirectDownloadLinkException(f'ERROR: {error}')