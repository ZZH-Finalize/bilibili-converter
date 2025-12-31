import os
import asyncio
import subprocess
from typing import Callable, Protocol, runtime_checkable
from abc import abstractmethod
from pathlib import Path

from log import logger, LOG_DIR

cmdq = asyncio.Queue()

ffmpeg_log = None

@runtime_checkable
class Task(Protocol):
    @abstractmethod
    async def exec(self, debug: bool): ...

class EndTask:
    async def exec(self, debug: bool):
        if debug is True:
            logger.info('all convert task complete!')

class ConvertTask:
    def __init__(self, args: list[str], final: Callable | None = None):
        self.args = ['ffmpeg', *args, '-codec', 'copy']
        self.final = final

    def add_output_fn(self, output_fn: Path):
        self.args.append(str(output_fn))

    async def exec(self, debug: bool):
        cmd_str = ''
        for arg in self.args:
            cmd_str += arg + ' '
        logger.info('exec: ' + cmd_str)

        if debug == False:
            await asyncio.to_thread(subprocess.run, self.args,
                                stdout=ffmpeg_log, stderr=ffmpeg_log)

        if self.final is not None:
            logger.debug('exec final')
            self.final()

async def execute(task: ConvertTask | EndTask):
    await cmdq.put(task)

async def execute_task(debug: bool):
    global ffmpeg_log
    ffmpeg_log = open(LOG_DIR / 'ffmpeg.log', 'w', encoding='utf-8')

    while True:
        task: ConvertTask | EndTask = await cmdq.get()

        await task.exec(debug)
        cmdq.task_done()

        if isinstance(task, EndTask):
            ffmpeg_log.close()
            break
