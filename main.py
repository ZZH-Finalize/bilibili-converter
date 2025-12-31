import os, sys
import asyncio
import json
import logging
import aiohttp

from vidinfo import vidinfo
from cache import cache

ref_path: list[str] = []
debug = False
cmdq = asyncio.Queue()
script_path = os.path.dirname(sys.argv[0])
logger = logging.getLogger('bili-conv')

uid_cache = cache('cache/uid.json', logger)

ENTRY_FILE = 'entry.json'
ACCEPT_EXTS = ['m4s','flv']

def parse_arg():
    global ref_path, debug
    from argparse import ArgumentParser
    parser = ArgumentParser('bili-conv', description='convert bilibili videos')
    parser.add_argument('ref_path', help='input video paths', nargs='+', type=str)
    parser.add_argument('-v', '--verbose', help='verbose level', dest='verbose', type=str, choices=logging._nameToLevel.keys(), default='INFO')
    parser.add_argument('-d', '--debug-mode', help='debug mode (print command only)', dest='debug', action='store_true')

    args = parser.parse_args()
    logger.setLevel(args.verbose)
    ref_path.extend(args.ref_path)
    debug = args.debug

async def request_info(aid: int):
    logger.info(f'request for {aid}')
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://uapis.cn/api/v1/social/bilibili/videoinfo', params=f'aid={aid}') as resp:
            json = await resp.json()
            logger.debug(f'get resp: {json}')
            return json

async def execute(cmd: str, *args):
    await cmdq.put((cmd, args))

async def execute_task():
    while True:
        cmd, args = await cmdq.get()
        if cmd == 'exit':
            break
        if debug is True:
            print(f'exec: {cmd}')
        else:
            await asyncio.to_thread(os.execv, cmd, args)

async def parse_entry(entry_fn: str) -> vidinfo:
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

    return vidinfo(type=media_type, title=title, owner=owner, output_path='')

async def scan_path(path: str):
    for entry in os.listdir(path):
        entry_path = os.path.join(path, entry)
        logger.debug(f'entry_path: {entry_path}')

        await parse_entry(os.path.join(entry_path, ENTRY_FILE))

    # for dirs in os.listdir(path):
        
    #     for a, b, c in os.walk(dirs):
    #         await execute(f'a: {a}, b: {b}, c: {c}')

    await execute('exit')

async def main():
    parse_arg()

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
