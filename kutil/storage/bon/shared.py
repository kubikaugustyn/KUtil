#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Literal

type BonData = dict | list
type EncodingType = Literal[1, 2]

RAW: EncodingType = 1
GZIP: EncodingType = 2

MAGIC: bytes = b'BON'
INT_SIZE = 4
FLOAT_SIZE = 4

FLAG_ADDRESS: int = 0b00000001  # A pointer
FLAG_NONE: int = 0b00000010  # None data type
FLAG_OBJECT: int = 0b00000100  # Object data type
FLAG_ARRAY: int = 0b00001000  # Array data type
FLAG_INT: int = 0b00010000  # Int data type
FLAG_FLOAT: int = 0b00100000  # Float data type
FLAG_STRING: int = 0b01000000  # String data type
FLAG_BOOL: int = 0b10000000  # Boolean data type
