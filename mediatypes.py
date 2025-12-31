import os
import util
from tempfile import NamedTemporaryFile
from typing import Protocol, runtime_checkable
from abc import abstractmethod
from pathlib import Path

from convert import ConvertTask
from log import logger

@runtime_checkable
class Handler(Protocol):
    @staticmethod
    @abstractmethod
    def gen_task(data_path: Path) -> ConvertTask: ...

class BLVHandler:
    @staticmethod
    def gen_task(data_path: Path) -> ConvertTask:
        is_match = lambda fn: os.path.isfile(fn) and str(fn).endswith('.blv')
        blv_files = list(filter(is_match, util.listdir(data_path)))

        if len(blv_files) == 1:
            blv_file = blv_files[0]
            logger.info(f'single blv: {blv_file}')
            return ConvertTask(['-i', str(blv_file)])
        else:
            logger.info(f'multiple blv files: {list(map(str, blv_files))}')

            f = NamedTemporaryFile('w', suffix='.txt', delete=False)
            # f = open('test.txt', 'w')
            for blv in blv_files:
                blv_abs_path = os.path.abspath(blv)
                f.write(f'file \'{blv_abs_path}\'\n')
            f.close()

            def clean_tmp_file():
                logger.debug(f'remove tmp file: {f.name}')
                os.remove(f.name)

            return ConvertTask(['-f', 'concat', '-safe', '0', '-i', f.name], clean_tmp_file)
            # return ConvertTask(['-f', 'concat', '-safe', '0', '-i', f.name])

class M4SHandler:
    @staticmethod
    def gen_task(data_path: Path) -> ConvertTask:
        video_path = data_path / 'video.m4s'
        audio_path = data_path / 'audio.m4s'

        args = []

        if video_path.exists():
            args.extend(['-i', str(video_path)])
        else:
            logger.warning(f'no video file in: {data_path}')

        if audio_path.exists():
            args.extend(['-i', str(audio_path)])
        else:
            logger.warning(f'no audio file in: {data_path}')

        return ConvertTask(args)

# 为handlers列表添加类型注解
HANDLERS: list[Handler] = [Handler, BLVHandler, M4SHandler]
