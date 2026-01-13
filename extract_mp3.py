import os
import sys
from pathlib import Path
import asyncio
import logging
from argparse import ArgumentParser
import subprocess
import util


# 创建独立的logger
logger = logging.getLogger('extract_mp3')
logger.setLevel(logging.DEBUG)  # 设置为最低级别，让处理器决定实际输出级别


def parse_arg():
    """解析命令行参数"""
    parser = ArgumentParser('extract-mp3', description='Extract MP3 audio from MP4 files')
    parser.add_argument('input_path', help='Input MP4 file or directory', type=str)
    parser.add_argument('-o', '--output', dest='output', help='Output MP3 file or directory', type=str, default='output')
    parser.add_argument('-v', '--verbose', help='verbose level', dest='verbose', type=str,
                        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], default='INFO')
    
    args = parser.parse_args()
    
    # 设置日志级别
    log_level = getattr(logging, args.verbose)
    logger.setLevel(log_level)
    
    return Path(args.input_path), Path(args.output)


async def convert_file(input_file: Path, output_file: Path):
    """将单个MP4文件转换为MP3"""
    # 确保输出目录存在
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f'Converting {input_file} to {output_file}')
    
    # 使用FFmpeg进行转换
    cmd = [
        'ffmpeg',
        '-i', str(input_file),
        '-vn',  # 不包含视频
        '-acodec', 'mp3',  # 音频编码为MP3
        '-y',  # 覆盖输出文件
        str(output_file)
    ]
    
    logger.debug(f'Executing command: {" ".join(cmd)}')
    
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    stdout, stderr = await process.communicate()
    
    if process.returncode == 0:
        logger.info(f'Successfully converted {input_file} to {output_file}')
    else:
        logger.error(f'Failed to convert {input_file} to {output_file}')
        logger.error(f'FFmpeg error: {stderr.decode()}')


async def scan_and_convert(input_path: Path, output_path: Path):
    """扫描输入路径并转换所有MP4文件"""
    tasks = []
    
    if input_path.is_file():
        # 如果输入是单个文件
        if input_path.suffix.lower() == '.mp4':
            output_file = output_path.with_suffix('.mp3') if output_path.suffix else output_path / f"{input_path.stem}.mp3"
            task = asyncio.create_task(convert_file(input_path, output_file))
            tasks.append(task)
        else:
            logger.warning(f'Input file is not MP4: {input_path}')
    elif input_path.is_dir():
        # 如果输入是目录，则递归搜索所有MP4文件
        mp4_files = []
        for root, dirs, files in os.walk(input_path):
            for file in files:
                if file.lower().endswith('.mp4'):
                    mp4_files.append(Path(root) / file)
        
        for mp4_file in mp4_files:
            # 计算输出路径，保持相对目录结构
            rel_path = mp4_file.relative_to(input_path)
            output_file = output_path / rel_path.with_suffix('.mp3')
            task = asyncio.create_task(convert_file(mp4_file, output_file))
            tasks.append(task)
    
    # 等待所有转换任务完成
    if tasks:
        await asyncio.gather(*tasks)


async def main():
    # 设置日志处理器
    logger.addHandler(logging.StreamHandler(sys.stdout))
    
    # 创建logs目录并设置文件处理器
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / 'extract_mp3_audio.log'  # 使用不同的文件名避免冲突
    file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 解析命令行参数
    input_path, output_path = parse_arg()
    
    # 创建输出目录
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 执行转换
    await scan_and_convert(input_path, output_path)
    
    logger.info('All tasks done!')


if __name__ == '__main__':
    asyncio.run(main())
