#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import unique, IntEnum
from typing import Literal

type BonData = dict | list | str | int | float | bool | bytes
type EncodingType = Literal[1, 2]

RAW: EncodingType = 1
GZIP: EncodingType = 2

MAGIC: bytes = b'BON'


@unique
class ValueType(IntEnum):
    ADDRESS = 0x00  # A pointer
    NONE = 0x01  # None data type
    OBJECT = 0x02  # Object data type
    ARRAY = 0x03  # Array data type
    INT = 0x04  # Int data type
    FLOAT = 0x05  # Float data type
    STRING = 0x06  # String data type
    BOOL_TRUE = 0x07  # Boolean True data type
    BOOL_FALSE = 0x08  # Boolean False data type
    BYTES = 0x09  # Bytes data type
