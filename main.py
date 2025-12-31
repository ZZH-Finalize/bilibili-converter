import os, sys
from pathlib import Path
import asyncio
import json
import logging
import aiohttp
import util
import classifiers

from vidinfo import *
from cache import cache, CACHE_DIR
from mediatypes import HANDLERS
from log import logger, LOG_DIR
from convert import execute, execute_task, EndTask, cmdq

ref_path: list[str] = []
output_path: Path = Path()
classifier_dir: Path = Path()
debug = False
semaphore: asyncio.Semaphore

fnset = set()

script_path = os.path.dirname(sys.argv[0])
uid_cache = cache('cache/uid.json')

ENTRY_FILE = 'entry.json'
MKDIRS = [CACHE_DIR, LOG_DIR]

def parse_arg():
    global ref_path, output_path, classifier_dir, debug, semaphore
    from argparse import ArgumentParser
    parser = ArgumentParser('bili-conv', description='convert bilibili videos')
    parser.add_argument('ref_path', help='input video paths', nargs='+', type=str)
    parser.add_argument('-o', '--output', dest='output', help='output video path', type=str, default='output')
    parser.add_argument('-t', '--thread', dest='thread', help='max parallel task num', type=int, default=5)
    parser.add_argument('-c', '--classifiers', help='classifiers json file dirs', dest='classifier_dir', type=str, default='classifiers')
    parser.add_argument('-v', '--verbose', help='verbose level', dest='verbose', type=str, choices=logging._nameToLevel.keys(), default='INFO')
    parser.add_argument('-d', '--debug-mode', help='debug mode (print command only)', dest='debug', action='store_true')

    args = parser.parse_args()
    logger.setLevel(args.verbose)
    ref_path.extend(args.ref_path)
    debug = args.debug
    output_path = Path(args.output)
    classifier_dir = Path(args.classifier_dir)
    semaphore = asyncio.Semaphore(args.thread)
    logger.info(f'allow max {args.thread} parallel task')

async def request_info(aid: int):
    logger.info(f'request for {aid}')
    async with aiohttp.ClientSession() as session:
        async with session.get(f'https://uapis.cn/api/v1/social/bilibili/videoinfo', params={'aid': aid}) as resp:
            json = await resp.json()
            logger.debug(f'get resp: {json}')
            return json

async def parse_entry(entry_fn: Path) -> Vidinfo:
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
        try:
            resp = await request_info(avid)
        except Exception as e:
            resp = {}

        # 源视频还在的情况
        if 'owner' in resp:
            owner_id = resp['owner']['mid']
            owner = resp['owner']['name']
        uid_cache.update(owner_id, owner)
    # 从缓存里获取到了owner
    else:
        logger.info(f'fetch owner({owner}) from cache')

    return Vidinfo(type=media_type, title=title, owner=owner)

async def scan_path(path: Path):
    tasks = []
    for entry in os.listdir(path):
        entry_path = path / entry
        dirs = list(filter(os.path.isdir, util.listdir(entry_path)))
        if not dirs:
            logger.warning(f'No directories found in {entry_path}')
            continue
        data_path = dirs[0]
        logger.debug(f'entry_path: {entry_path}')
        logger.debug(f'data_path: {data_path}')

        # 创建异步任务来处理每个条目，直接使用信号量保护process_entry
        task = asyncio.create_task(process_entry_with_semaphore(entry_path, data_path))
        tasks.append(task)

    # 等待所有条目处理完成
    await asyncio.gather(*tasks)

async def process_entry_with_semaphore(entry_path: Path, data_path: Path):
    async with semaphore:  # 获取信号量许可
        await process_entry(entry_path, data_path)

async def process_entry(entry_path: Path, data_path: Path):
    vidinfo = await parse_entry(entry_path / ENTRY_FILE)

    if vidinfo.type >= len(HANDLERS):
        logger.warning(f'no handler for media type: {vidinfo.type}, skip!')
        return

    classified_path = classifiers.classify(vidinfo)
    output_dir = output_path / classified_path
    os.makedirs(output_dir, exist_ok = True)
    unified_title = util.unify_filename(vidinfo.title)
    output_fn = output_dir / f'{unified_title}.mp4'

    counter = 1
    while True:
        if output_fn in fnset:
            logger.warning(f'duplcate file: {output_fn}, apply auto rename')
            output_fn = output_dir / f'{unified_title}-{counter}.mp4'
            counter = counter + 1
        else:
            break
    
    fnset.add(output_fn)

    task = HANDLERS[vidinfo.type].gen_task(data_path)
    task.add_output_fn(output_fn)
    await execute(task)

async def scan_ref():
    scan_tasks = []
    for ref in ref_path:
        for path in util.listdir(ref):
            scan_tasks.append(asyncio.create_task(scan_path(path)))  # 收集所有扫描任务

    await asyncio.gather(*scan_tasks)  # 并发执行所有扫描任务
    await execute(EndTask())
    fnset.clear()

async def main():
    MKDIRS.append(output_path)

    for dir in MKDIRS:
        if not os.path.exists(dir):
            os.mkdir(dir)

    logger.addHandler(logging.StreamHandler(sys.stdout))
    logger.addHandler(logging.FileHandler(LOG_DIR / 'main.log', encoding='utf-8'))

    parse_arg()

    uid_cache.load()

    classifiers.load_classifiers(classifier_dir)

    asyncio.create_task(execute_task(debug))
    await scan_ref()
    await cmdq.join()

    logger.info('all task done!')

    uid_cache.save()

if __name__ == '__main__':
    asyncio.run(main())
