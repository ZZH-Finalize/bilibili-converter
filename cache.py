import json
from logging import Logger

class cache:
    def __init__(self, fn: str, logger: Logger) -> None:
        self.fn = fn
        self.logger = logger
        self.mem = {}

    def update(self, owner_id: int, owner: str):
        self.logger.info(f'update cache ({owner_id} -> {owner})')
        self.mem.update({owner_id: owner})

    def get(self, owner_id: int) -> str | None:
        owner = self.mem.get(owner_id, None)
        self.logger.debug(f'get cache ({owner_id} -> {owner})')
        return owner

    def load(self, fn: str = ''):
        if fn != '':
            self.fn = fn
        self.mem = json.load(open(self.fn, encoding='utf-8'))
        self.logger.info(f'load cache from {self.fn}')

    def save(self):
        json.dump(self.mem, open(self.fn, 'w', encoding='utf-8'), indent=4, ensure_ascii=False)
        self.logger.info(f'save cache to {self.fn}')
