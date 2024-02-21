#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import gzip

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.storage.bon.shared import *
from kutil.storage.bon.converter import int_to_bytes, float_to_bytes, str_to_bytes, uint32_to_bytes


class BonEncodeError(Exception):
    pass


class BonEncoder:
    """
    Non-extensible BON encoder for Python data structures.

    Supports the following objects and types by default:

    +-------------------+---------------+
    | Python            | BON           |
    +===================+===============+
    | dict              | object        |
    +-------------------+---------------+
    | list              | array         |
    +-------------------+---------------+
    | str               | string        |
    +-------------------+---------------+
    | int               | int           |
    +-------------------+---------------+
    | float             | float         |
    +-------------------+---------------+
    | True, False       | boolean       |
    +-------------------+---------------+
    | None              | null          |
    +-------------------+---------------+
    | bytes             | bytes         |
    +-------------------+---------------+
    """

    def encode(self, buff: ByteBuffer, data: BonData, encoding: EncodingType):
        pool = []

        self._gen_pool(pool, data)

        assert pool[0] == data

        encoded_pool = [None] * len(pool)

        self._encode_item(data, pool, encoded_pool)

        buff.write(MAGIC)  # Write the magic number

        self._encode_encoded_pool_raw_value(0, buff)  # Write a pointer to the pool at index 0

        self._encode_encoded_pool(encoded_pool, buff)  # Write the pool

        if encoding == RAW:
            return
        elif encoding == GZIP:
            buff.reset(gzip.compress(buff.export()))
            return
        raise BonEncodeError(f"Invalid encoding {encoding}")

    def _encode_encoded_pool(self, encoded_pool: list, buff: ByteBuffer):
        buff.write(uint32_to_bytes(len(encoded_pool)))
        for item in encoded_pool:
            if isinstance(item, dict):
                buff.writeByte(ValueType.OBJECT)
                buff.write(uint32_to_bytes(len(item)))  # Set object length
                for key, value in item.items():
                    buff.write(str_to_bytes(key))  # Store object key
                    self._encode_encoded_pool_raw_value(value, buff)  # Store object value
            else:
                buff.writeByte(ValueType.ARRAY)
                buff.write(uint32_to_bytes(len(item)))  # Set list length
                for value in item:
                    self._encode_encoded_pool_raw_value(value, buff)  # Store list item

    @staticmethod
    def _encode_encoded_pool_raw_value(value: bytes | int, buff: ByteBuffer):
        if isinstance(value, bytes):
            buff.write(value)
        else:
            buff.writeByte(ValueType.ADDRESS)
            buff.write(uint32_to_bytes(value))

    def _encode_object(self, data: dict, pool: list, encoded_pool: list) -> dict:
        encoded: dict = {}
        for key, value in data.items():
            encoded[key] = self._encode_item(value, pool, encoded_pool)
        return encoded

    def _encode_array(self, data: list, pool: list, encoded_pool: list) -> list:
        encoded: list = [None] * len(data)
        for i, value in enumerate(data):
            encoded[i] = self._encode_item(value, pool, encoded_pool)
        return encoded

    def _encode_item(self, value, pool: list, encoded_pool: list):
        if isinstance(value, dict):
            i = pool.index(value)
            if encoded_pool[i] is None:
                encoded_pool[i] = True
                encoded_pool[i] = self._encode_object(value, pool, encoded_pool)
            elif encoded_pool[i] is True:
                # If the object is currently being worked on, return
                # a pointer to it to prevent recursion
                return bytes([ValueType.ADDRESS]) + uint32_to_bytes(i)
            return i
        elif isinstance(value, list):
            i = pool.index(value)
            if encoded_pool[i] is None:
                encoded_pool[i] = True
                encoded_pool[i] = self._encode_array(value, pool, encoded_pool)
            elif encoded_pool[i] is True:
                # If the array is currently being worked on, return
                # a pointer to it to prevent recursion
                return bytes([ValueType.ADDRESS]) + uint32_to_bytes(i)
            return i
        else:
            return self._encode_other_data(value)

    @staticmethod
    def _encode_other_data(data) -> bytes:
        if isinstance(data, str):
            encoded = str_to_bytes(data)
            valueType = ValueType.STRING
        elif isinstance(data, bool):
            encoded = b''
            valueType = ValueType.BOOL_TRUE if data else ValueType.BOOL_FALSE
        elif isinstance(data, int):
            encoded = int_to_bytes(data)
            valueType = ValueType.INT
        elif isinstance(data, float):
            encoded = float_to_bytes(data)
            valueType = ValueType.FLOAT
        elif isinstance(data, bytes):
            encoded = uint32_to_bytes(len(data)) + data
            valueType = ValueType.BYTES
        elif data is None:
            encoded = b''
            valueType = ValueType.NONE
        else:
            raise BonEncodeError(f"Cannot encode {type(data).__class__.__name__} which is not"
                                 f" BON serializable")

        return bytes([valueType.value]) + encoded

    def _gen_pool(self, pool: list, data: BonData):
        if data in pool:
            return

        if isinstance(data, list):
            pool.append(data)
            for val in data:
                self._gen_pool(pool, val)
        elif isinstance(data, dict):
            pool.append(data)
            for val in data.values():
                self._gen_pool(pool, val)
        elif not (isinstance(data, str) or
                  isinstance(data, int) or
                  isinstance(data, float) or
                  isinstance(data, bool) or
                  isinstance(data, bytes) or
                  data is None):
            raise BonEncodeError(f"Cannot encode {type(data).__class__.__name__} which is not"
                                 f" BON serializable")
