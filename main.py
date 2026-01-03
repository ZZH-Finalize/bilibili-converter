import os, sys
import asyncio
import json
import logging
import aiohttp
import util

from vidinfo import Vidinfo
from cache import cache, CACHE_DIR
from mediatypes import handlers

ref_path: list[str] = []
output_path: str = ''
debug = False
cmdq = asyncio.Queue()
script_path = os.path.dirname(sys.argv[0])
logger = logging.getLogger('bili-conv')

uid_cache = cache('cache/uid.json', logger)

ENTRY_FILE = 'entry.json'
MEDIA_TYPE_MAPPING = [None, ]

MKDIRS = [CACHE_DIR]

def parse_arg():
    global ref_path, output_path, debug
    from argparse import ArgumentParser
    parser = ArgumentParser('bili-conv', description='convert bilibili videos')
    parser.add_argument('ref_path', help='input video paths', nargs='+', type=str)
    parser.add_argument('-o', '--output', dest='output', help='output video path', type=str, default='output')
    parser.add_argument('-v', '--verbose', help='verbose level', dest='verbose', type=str, choices=logging._nameToLevel.keys(), default='INFO')
    parser.add_argument('-d', '--debug-mode', help='debug mode (print command only)', dest='debug', action='store_true')

    args = parser.parse_args()
    logger.setLevel(args.verbose)
    ref_path.extend(args.ref_path)
    debug = args.debug
    output_path = args.output

async def request_info(aid: int):
    logger.info(f'request for {aid}')
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://uapis.cn/api/v1/social/bilibili/videoinfo', params=f'aid={aid}') as resp:
            json = await resp.json()
            logger.debug(f'get resp: {json}')
            return json

async def execute(cmd: str):
    await cmdq.put(cmd)

async def execute_task():
    while True:
        cmd_str: str = await cmdq.get()
        cmd_part = cmd_str.split(' ')
        cmd = cmd_part[0]
        args = cmd_part[1:]

        if cmd == 'exit':
            break
        elif cmd == 'skip':
            continue

        if debug is True:
            print(f'exec: {cmd}')
        else:
            await asyncio.to_thread(os.execvp, cmd, args)

async def parse_entry(entry_fn: str) -> Vidinfo:
    json_data = json.load(open(entry_fn, encoding='utf-8'))
    media_type = json_data['media_type']
    title = json_data['title']
    page = json_data['page_data']['page']
    avid = json_data['avid']
    # bvid = json_data.get('bvid', None)
    owner_id = json_data.get('owner_id', None)
    if 1 != page:
        title = f'{title}-p{page}'
    logger.info(f'convert: {title}:{media_type}-{entry_fn}')

    owner = uid_cache.get(owner_id)
    if None == owner:
        resp = await request_info(avid)

        # 源视频还在的情况
        if 'owner' in resp:
            owner_id = resp['owner']['mid']
            owner = resp['owner']['name']
        # 源视频不存在了
        else:
            owner = 'unknow_owner'
        uid_cache.update(owner_id, owner)
    # 从缓存里获取到了owner
    else:
        logger.info(f'fetch owner({owner}) from cache')

    return Vidinfo(type=media_type, title=title, owner=owner, output_path='')

async def scan_path(path: str):
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        data_path = list(filter(os.path.isdir, util.listdir(entry_path)))[0]
        logger.debug(f'entry_path: {entry_path}')
        logger.debug(f'data_path: {data_path}')

        vidinfo = await parse_entry(os.path.join(entry_path, ENTRY_FILE))
        cmd = handlers[vidinfo.type].gen_cmd(data_path)
        logger.info(cmd)

    await execute('exit')

async def main():
    parse_arg()

    uid_cache.load()

    MKDIRS.append(output_path)

    for dir in MKDIRS:
        if not os.path.exists(dir):
            os.mkdir(dir)

    logger.addHandler(logging.StreamHandler(sys.stdout))

    # resp = await request_info(15786518)
    # print(resp['title'])
    # print(resp['owner']['mid'])
    # print(resp['owner']['name'])

    task = asyncio.create_task(execute_task())

    for ref in ref_path:
        for path in os.listdir(ref):
            await scan_path(os.path.join(ref, path))

    task.cancel()
    uid_cache.save()

if __name__ == '__main__':
    asyncio.run(main())
