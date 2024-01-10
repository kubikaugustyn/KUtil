#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import math, struct

from kutil.buffer.ByteBuffer import ByteBuffer


def int_to_bytes(number: int) -> bytes:
    num_bytes = math.ceil(number.bit_length() / 8)
    return (num_bytes.to_bytes(4, "big", signed=False) +
            number.to_bytes(num_bytes, "big", signed=True))


def int_from_bytes(buff: ByteBuffer) -> int:
    num_bytes = int.from_bytes(buff.read(4), byteorder="big", signed=False)
    return int.from_bytes(buff.read(num_bytes), "big", signed=True)


def uint32_to_bytes(number: int) -> bytes:
    return number.to_bytes(4, "big", signed=False)


def uint32_from_bytes(buff: ByteBuffer) -> int:
    return int.from_bytes(buff.read(4), "big", signed=False)


FLOAT_FLAG_NAN = 0x01
FLOAT_FLAG_INF = 0x02
FLOAT_FLAG_NEG = 0x04
FLOAT_FLAG_VAL = 0x08


def float_to_bytes(number: float) -> bytes:
    flags = 0

    if number in (float("nan"), float("inf"), float("-inf")):
        postfix = b''
        if number == float("nan"):
            flags |= FLOAT_FLAG_NAN
        elif number == float("inf"):
            flags |= FLOAT_FLAG_INF
        elif number == float("-inf"):
            flags |= FLOAT_FLAG_INF
            flags |= FLOAT_FLAG_NEG
    else:
        flags |= FLOAT_FLAG_VAL
        postfix = struct.pack("d", number)

    return bytes([flags]) + postfix


def float_from_bytes(buff: ByteBuffer) -> float:
    flags = buff.readByte()

    if flags & FLOAT_FLAG_VAL != 0:
        return struct.unpack("d", buff.read(8))[0]
    elif flags & FLOAT_FLAG_NAN != 0:
        return float("nan")
    elif flags & FLOAT_FLAG_INF != 0:
        if flags & FLOAT_FLAG_NEG != 0:
            return float("-inf")
        else:
            return float("inf")
    else:
        raise ValueError("Bad float format")


def str_to_bytes(string: str) -> bytes:
    return uint32_to_bytes(len(string)) + string.encode("utf-8")


def str_from_bytes(buff: ByteBuffer) -> str:
    length = uint32_from_bytes(buff)

    return buff.read(length).decode("utf-8")
