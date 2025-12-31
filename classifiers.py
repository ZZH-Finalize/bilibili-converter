import os
import re
import json
from pydantic import BaseModel, Field, field_validator
from typing import Protocol, runtime_checkable
from abc import abstractmethod
from pathlib import Path
import util

from vidinfo import Vidinfo
from log import logger

@runtime_checkable
class Classifier(Protocol):
    @classmethod
    @abstractmethod
    def match(cls, info: Vidinfo) -> Path | None: ...

# 按照up主分类, 这是一个基础分类器
class Owner:
    @classmethod
    def match(cls, info: Vidinfo) -> Path:
        path = info.owner if info.owner is not None else 'unknown'
        return Path(path)

class MatchKeywords(BaseModel):
    common: list[re.Pattern] = Field(default=[], description='Used for all field match')
    title: list[re.Pattern] = Field(default=[], description='Used for title match')
    up: list[re.Pattern] = Field(default=[], description='Used for up match')

    @field_validator('common', 'title', 'up', mode='before')
    @classmethod
    def compile_patterns(cls, v):
        if isinstance(v, list):
            return [re.compile(pattern, flags=re.IGNORECASE) if isinstance(pattern, str) else pattern for pattern in v]
        return v

# 根据标题, up主名称等信息, 判断视频的内容类型
class ContentClassifier(BaseModel):
    name: str = Field(default='', description='Classifier name')
    output_dir: Path = Field(description='Which dir should be selected when matched with this classifier')
    regexp: MatchKeywords = Field(description='Regex used for match')
    priority: int = Field(default=9, description='Classifier priority')
    with_upinfo: bool = Field(default=False, description='Controls the final output dir')

    @staticmethod
    def match_field(pattern: re.Pattern, *args: str | None):
        for arg in args:
            if arg and pattern.search(arg):
                return True

    def match(self, info: Vidinfo) -> Path | None:
        # up主匹配
        for pattern in self.regexp.up:
            if ContentClassifier.match_field(pattern, info.owner):
                return Path(self.output_dir)

        # 标题匹配
        for pattern in self.regexp.title:
            if ContentClassifier.match_field(pattern, info.title):
                return Path(self.output_dir)

        # 全匹配
        for pattern in self.regexp.common:
            if ContentClassifier.match_field(pattern, info.title, info.owner):
                return Path(self.output_dir)

classifiers: dict[int, list[ContentClassifier]] = {}

def add_classifier(fn: Path):
    if os.path.exists(fn):
        logger.info(f'load classifier from: {fn}')
        json_data = json.load(open(fn, 'r', encoding='utf-8'))

        for key, classifier_def in json_data.items():
            classifier_def['name'] = key

            try:
                classifier = ContentClassifier.model_validate(classifier_def)
            except Exception as e:
                logger.error(f'{key} validate fail, skip!')
                continue

            if classifier.priority not in classifiers.keys():
                classifiers.update({classifier.priority: []})
            classifiers[classifier.priority].append(classifier)

def load_classifiers(path: Path):
    for fn in filter(lambda x: str(x).endswith('.json'), util.listdir(path)):
        add_classifier(fn)

def __classify(info: Vidinfo):
    for i in range(max(classifiers.keys()) + 1):
        if i in classifiers.keys():
            for classifier in classifiers[i]:
                content_type = classifier.match(info)
                if content_type is not None:
                    logger.info(f'{info.title} matched with: {classifier.name}')
                    return content_type, classifier.with_upinfo
    return None, False

def classify(info: Vidinfo) -> Path:
    content_type = None
    with_upinfo = False

    content_type, with_upinfo = __classify(info)

    if content_type is None:
        content_type = Path('unknown')

    if with_upinfo:
        return content_type / Owner.match(info)
    else:
        return content_type
