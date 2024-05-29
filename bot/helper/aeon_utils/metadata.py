import os
import json

from asyncio import create_subprocess_exec
from asyncio.subprocess import PIPE

from bot import LOGGER

async def change_metadata(file, dirpath, key):
    LOGGER.info(f"Trying to change metadata for file: {file}")
    temp_file = f"{file}.temp.mkv"

    full_file_path = os.path.join(dirpath, file)
    temp_file_path = os.path.join(dirpath, temp_file)

    cmd = [
        'ffprobe', '-hide_banner', '-loglevel', 'error', '-print_format', 'json', '-show_streams', full_file_path
    ]

    process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await process.communicate()

    if process.returncode != 0:
        LOGGER.error(f"Error getting stream info: {stderr.decode().strip()}")
        return file

    streams = json.loads(stdout)['streams']

    cmd = [
        'render', '-y', '-i', full_file_path, '-c', 'copy',
        '-metadata', f'title={key}',
        '-metadata:s:v:0', f'title={key}',
        '-metadata', 'copyright=',
        '-metadata', 'description=',
        '-metadata', 'license=',
        '-metadata', 'LICENSE=',
        '-metadata', 'author=',
        '-metadata', 'summary=',
        '-metadata', 'comment=',
        '-metadata', 'artist=',
        '-metadata', 'album=',
        '-metadata', 'genre=',
        '-metadata', 'date=',
        '-metadata', 'creation_time=',
        '-metadata', 'language=',
        '-metadata', 'publisher=',
        '-metadata', 'encoder=',
        '-metadata', 'SUMMARY=',
        '-metadata', 'AUTHOR=',
        '-metadata', 'WEBSITE=',
        '-metadata', 'COMMENT=',
        '-metadata', 'ENCODER=',
        '-metadata', 'FILENAME=',
        '-metadata', 'MIMETYPE='
    ]

    audio_index = 0
    subtitle_index = 0

    for stream in streams:
        stream_index = stream['index']
        stream_type = stream['codec_type']

        cmd.extend(['-map', f'0:{stream_index}'])
        cmd.extend([
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'title=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'author=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'AUTHOR=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'description=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'DESCRIPTION=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'copyright=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'COPYRIGHT=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'summary=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'SUMMARY=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'comment=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'COMMENT=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'author=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'WEBSITE=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'ENCODER=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'FILENAME=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'MIMETYPE=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'language=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'publisher=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'genre=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'date=',
            f'-metadata:s:{stream_type[0]}:{stream_index}', 'creation_time='
        ])
        
        if stream_type == 'audio':
            cmd.extend([f'-metadata:s:a:{audio_index}', f'title={key}'])
            audio_index += 1
        elif stream_type == 'subtitle':
            cmd.extend([f'-metadata:s:s:{subtitle_index}', f'title={key}'])
            subtitle_index += 1

    cmd.append(temp_file_path)

    process = await create_subprocess_exec(*cmd, stderr=PIPE)
    await process.wait()

    if process.returncode != 0:
        err = (await process.stderr.read()).decode().strip()
        LOGGER.error(err)
        LOGGER.error(f"Error changing metadata for file: {file}")
        return file

    os.replace(temp_file_path, full_file_path)
    LOGGER.info(f"Metadata changed successfully for file: {file}")
    return file


async def delete_attachments(file, dirpath):
    temp_file = f"{file}.temp.mkv"
    
    full_file_path = os.path.join(dirpath, file)
    temp_file_path = os.path.join(dirpath, temp_file)
    
    cmd = ['render', '-y', '-i', full_file_path, '-map', '0', '-map', '-0:t', '-c', 'copy', temp_file_path]
    
    process = await create_subprocess_exec(*cmd, stderr=PIPE)
    await process.wait()
    
    os.replace(temp_file_path, full_file_path)
    return file


async def delete_extra_video_streams(file, dirpath):
    temp_file = f"{file}.temp.mkv"
    
    full_file_path = os.path.join(dirpath, file)
    temp_file_path = os.path.join(dirpath, temp_file)
    
    cmd = ['ffprobe', '-hide_banner', '-loglevel', 'error', '-print_format', 'json', '-show_streams', full_file_path]
    process = await create_subprocess_exec(*cmd, stdout=PIPE, stderr=PIPE)
    stdout, stderr = await process.communicate()
    
    if process.returncode != 0:
        LOGGER.error(f"Error getting stream info: {stderr.decode().strip()}")
        return file
    
    streams = json.loads(stdout)['streams']
    
    cmd = ['render', '-y', '-i', full_file_path]
    
    first_video = False
    
    for stream in streams:
        stream_index = stream['index']
        stream_type = stream['codec_type']
        
        if stream_type == 'video':
            if not first_video:
                cmd.extend(['-map', f'0:{stream_index}'])
                first_video = True
        else:
            cmd.extend(['-map', f'0:{stream_index}'])
    
    cmd.extend(['-c', 'copy', temp_file_path])
    
    process = await create_subprocess_exec(*cmd, stderr=PIPE)
    await process.wait()
    
    os.replace(temp_file_path, full_file_path)
    return file
