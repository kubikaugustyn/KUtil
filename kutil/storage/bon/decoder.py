#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import gzip

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.storage.bon.shared import *
from kutil.storage.bon.converter import str_from_bytes, uint32_from_bytes, int_from_bytes, \
    float_from_bytes


class BonDecodeError(Exception):
    pass


class BonDecoderAddressPointer:
    address: int

    def __init__(self, address: int):
        self.address = address

    def find(self, pool: list):
        return pool[self.address]


class BonDecoder:
    """
    Non-extensible BON decoder for Python data structures.

    Performs the following translations in decoding by default:

    +---------------+-------------------+
    | BON           | Python            |
    +===============+===================+
    | object        | dict              |
    +---------------+-------------------+
    | array         | list              |
    +---------------+-------------------+
    | string        | str               |
    +---------------+-------------------+
    | int           | int               |
    +---------------+-------------------+
    | float         | float             |
    +---------------+-------------------+
    | boolean       | True, False       |
    +---------------+-------------------+
    | null          | None              |
    +---------------+-------------------+
    | bytes         | bytes             |
    +---------------+-------------------+
    """

    def decode(self, buff: ByteBuffer, encoding: EncodingType) -> BonData:
        if encoding == GZIP:
            buff.reset(gzip.decompress(buff.export()))
        else:
            if encoding != RAW:
                raise BonDecodeError(f"Invalid encoding {encoding}")

        if buff.read(len(MAGIC)) != MAGIC:
            raise BonDecodeError(f"Invalid magic number, should be {MAGIC}")

        entry = self._decode_raw_value(buff, [])

        poolLength = uint32_from_bytes(buff)

        pool = [None] * poolLength

        for i in range(poolLength):
            pool[i] = self._decode_raw_value(buff, pool)

        self._process_pool_for_pointers(pool)

        if isinstance(entry, BonDecoderAddressPointer):
            return entry.find(pool)
        return entry

    def _process_pool_for_pointers(self, pool: list):
        for i, entry in enumerate(pool):
            if isinstance(entry, dict):
                self._process_object_for_pointers(entry, pool)
            elif isinstance(entry, list):
                self._process_array_for_pointers(entry, pool)
            elif isinstance(entry, BonDecoderAddressPointer):
                pool[i] = entry.find(pool)
            else:
                continue  # If the pool contains something like this, skip it

    def _process_object_for_pointers(self, obj: dict, pool: list):
        for key, value in obj.items():
            if isinstance(value, BonDecoderAddressPointer):
                obj[key] = value.find(pool)
            elif isinstance(value, dict):
                self._process_object_for_pointers(value, pool)
            elif isinstance(value, list):
                self._process_array_for_pointers(value, pool)

    def _process_array_for_pointers(self, array: list, pool: list):
        for i, entry in enumerate(array):
            if isinstance(entry, BonDecoderAddressPointer):
                array[i] = entry.find(pool)
            elif isinstance(entry, dict):
                self._process_object_for_pointers(entry, pool)
            elif isinstance(entry, list):
                self._process_array_for_pointers(entry, pool)

    def _decode_raw_value(self, buff: ByteBuffer, pool: list):
        typeByte: int = buff.readByte()
        try:
            valueType: ValueType = ValueType(typeByte)
        except Exception as e:
            raise BonDecodeError(f"Cannot decode value with unknown type {hex(typeByte)}") from None

        if valueType == ValueType.ADDRESS:
            return BonDecoderAddressPointer(uint32_from_bytes(buff))
        elif valueType == ValueType.OBJECT:
            return self._decode_object(buff, pool)  # Added to the pool manually
        elif valueType == ValueType.ARRAY:
            return self._decode_array(buff, pool)  # Added to the pool manually
        elif valueType == ValueType.STRING:
            return str_from_bytes(buff)
        elif valueType == ValueType.INT:
            return int_from_bytes(buff)
        elif valueType == ValueType.FLOAT:
            return float_from_bytes(buff)
        elif valueType == ValueType.BOOL_TRUE:
            return True
        elif valueType == ValueType.BOOL_FALSE:
            return False
        elif valueType == ValueType.BYTES:
            size = uint32_from_bytes(buff)
            return buff.read(size)
        elif valueType == ValueType.NONE:
            return None
        else:
            raise TypeError(f"Unknown value kind {valueType.name}")

    def _decode_object(self, buff: ByteBuffer, pool: list) -> dict:
        obj: dict = {}

        length = uint32_from_bytes(buff)
        if length == 0:
            return {}

        for _ in range(length):
            key = str_from_bytes(buff)
            value = self._decode_raw_value(buff, pool)
            obj[key] = value

        return obj

    def _decode_array(self, buff: ByteBuffer, pool: list) -> list:
        length = uint32_from_bytes(buff)
        if length == 0:
            return []

        array: list = [None] * length

        for i in range(length):
            value = self._decode_raw_value(buff, pool)
            array[i] = value

        return array
