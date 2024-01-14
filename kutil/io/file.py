#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import json
from typing import Literal, overload

from kutil.buffer.ByteBuffer import ByteBuffer

type OUTPUT_STR = Literal["text", "bytes", "bytearray", "json", "buffer"]
type OUTPUT = str | bytes | bytearray | dict | ByteBuffer


@overload  # https://mypy.readthedocs.io/en/latest/more_types.html#function-overloading
def readFile(path: str, output: Literal["text"], encoding: str = "utf-8") -> str: ...


@overload
def readFile(path: str, output: Literal["bytes"], encoding: str = "utf-8") -> bytes: ...


@overload
def readFile(path: str, output: Literal["bytearray"], encoding: str = "utf-8") -> bytearray: ...


@overload
def readFile(path: str, output: Literal["json"], encoding: str = "utf-8") -> dict: ...


@overload
def readFile(path: str, output: Literal["buffer"], encoding: str = "utf-8") -> ByteBuffer: ...


def readFile(path: str, output: OUTPUT_STR = "text", encoding: str = "utf-8") -> OUTPUT:
    with open(path, "rb") as f:
        content = f.read()
    if output == "bytes":
        return content
    elif output == "bytearray":
        return bytearray(content)
    elif output == "text":
        return content.decode(encoding)
    elif output == "json":
        return json.loads(content.decode(encoding))
    elif output == "buffer":
        return ByteBuffer(content)
    else:
        raise ValueError("Bad output kind.")


def writeFile(path: str, data: OUTPUT, encoding: str = "utf-8"):
    if isinstance(data, bytes):
        content = data
    elif isinstance(data, bytearray):
        content = bytes(data)
    elif isinstance(data, str):
        content = data.encode(encoding)
    elif isinstance(data, dict):
        content = json.dumps(data).encode(encoding)
    elif isinstance(data, ByteBuffer):
        content = data.export()
    else:
        raise ValueError("Bad data kind.")
    with open(path, "wb+") as f:
        f.write(content)
