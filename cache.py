import os
import json
from log import logger
from pathlib import Path

CACHE_DIR = Path('cache')

class cache:
    def __init__(self, fn: str) -> None:
        self.fn = fn
        self.mem = {}

    def update(self, owner_id: int, owner: str | None):
        logger.info(f'update cache ({owner_id} -> {owner})')
        self.mem.update({str(owner_id): owner})

    def get(self, owner_id: int) -> str | None:
        owner = self.mem.get(str(owner_id), None)
        logger.debug(f'get cache ({owner_id} -> {owner})')
        return owner

    def load(self, fn: str = ''):
        if fn != '':
            self.fn = fn

        if os.path.exists(self.fn):
            self.mem = json.load(open(self.fn, encoding='utf-8'))
            logger.info(f'load cache from {self.fn}')

    def save(self):
        json.dump(self.mem, open(self.fn, 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
        logger.info(f'save cache to {self.fn}')
