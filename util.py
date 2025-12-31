import os
import re
from pathlib import Path

REPLACE_CHARS = [
    '\\',
    '/',
    ':',
    '*',
    '?',
    '"',
    '<',
    '>',
    '|',
]

SEQSPACE = re.compile(' +')
PRESPACE = re.compile('^ +')

def listdir(path: str | Path):
    return map(lambda x: Path(os.path.join(path, x)), os.listdir(path))

def unify_filename(fn: str):
    for ch in REPLACE_CHARS:
        fn = fn.replace(ch, ' ')

    fn = re.sub(PRESPACE, '', fn)
    return re.sub(SEQSPACE, ' ', fn)
