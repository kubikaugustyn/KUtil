#  -*- coding: utf-8 -*-
"""
This is the binary object notation (BON, not JSON) library.
"""
__author__ = "kubik.augustyn@post.cz"

from typing import BinaryIO, Optional, Type

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.storage.bon.shared import *
from kutil.storage.bon.decoder import BonDecoder
from kutil.storage.bon.encoder import BonEncoder

_defaultDecoder = BonDecoder()
_defaultEncoder = BonEncoder()


def load(file: BinaryIO, encoding: EncodingType = GZIP,
         cls: Optional[Type[BonDecoder]] = None) -> BonData:
    data = file.read()
    file.close()
    return load_binary(data, encoding, cls)


def load_binary(data: bytes | bytearray, encoding: EncodingType = GZIP,
                cls: Optional[Type[BonDecoder]] = None) -> BonData:
    if not isinstance(data, bytes) and not isinstance(data, bytearray):
        raise TypeError(f"Data should be of type bytes, not {type(data).__class__.__name__}")
    if encoding not in (RAW, GZIP):
        raise ValueError(f"Invalid encoding provided: {encoding}")

    buff: ByteBuffer = ByteBuffer(data)
    if cls is None:
        return _defaultDecoder.decode(buff, encoding)
    return cls().decode(buff, encoding)


def dump(file: BinaryIO, data: BonData, encoding: EncodingType = GZIP,
         cls: Optional[Type[BonEncoder]] = None):
    file.write(dump_binary(data, encoding, cls))
    file.close()


def dump_binary(data: BonData, encoding: EncodingType = GZIP,
                cls: Optional[Type[BonEncoder]] = None) -> bytes:
    if not isinstance(data, dict) and not isinstance(data, list):
        raise TypeError(f"Data should be of type BonData (dict or list),"
                        f" not {type(data).__class__.__name__}")
    if encoding not in (RAW, GZIP):
        raise ValueError(f"Invalid encoding provided: {encoding}")

    buff: ByteBuffer = ByteBuffer()
    if cls is None:
        _defaultEncoder.encode(buff, data, encoding)
    else:
        cls().encode(buff, data, encoding)

    return buff.export()

# TODO Add object keys to the pool, saving some space with duplicate object keys
