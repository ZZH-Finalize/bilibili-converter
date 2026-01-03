import os

def listdir(path: str):
    return map(lambda x: os.path.join(path, x), os.listdir(path))
