import os, sys, util

class BLVHandler:
    @staticmethod
    def is_match(fn: str) -> bool:
        return os.path.isfile(fn) and fn.endswith('.blv')

    @staticmethod
    def gen_cmd(data_path: str) -> list[str]:
        cmds = []

        for file in filter(BLVHandler.is_match, util.listdir(data_path)):
            cmds.append(f'ffmpeg -i {file} -codec copy')

        return cmds

class M4SHandler:
    @staticmethod
    def is_match(fn: str) -> bool:
        return os.path.isfile(fn) and fn.endswith('.m4s')

    @staticmethod
    def gen_cmd(data_path: str) -> list[str]:
        video_path = os.path.join(data_path, 'video.m4s')
        audio_path = os.path.join(data_path, 'audio.m4s')

        return [f'ffmpeg -i {video_path} -i {audio_path} -codec copy']
    

handlers = [None, BLVHandler, M4SHandler]
