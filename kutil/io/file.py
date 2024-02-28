#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import json

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.typing_help import FinalStr, Final, Literal, overload

type OUTPUT_STR = Literal["text", "bytes", "bytearray", "json", "buffer"]
type OUTPUT = str | bytes | bytearray | dict | ByteBuffer


# Read file
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


# Write file
def writeFile(path: str, data: OUTPUT, encoding: str = "utf-8") -> None:
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


# Newline stuff
type NL_TYPE = Literal["CR", "LF", "CRLF"]
CR: FinalStr = "\r"  # Carriage return
LF: FinalStr = "\n"  # Line feed
CRLF: FinalStr = "\r\n"  # CRLF
bCR: Final[bytes] = b"\r"  # Bytes carriage return
bLF: Final[bytes] = b"\n"  # Bytes line feed
bCRLF: Final[bytes] = b"\r\n"  # Bytes CRLF
cCR: Final[int] = ord("\r")  # Char carriage return
cLF: Final[int] = ord("\n")  # Char line feed

NL: str = CRLF  # Newline
bNL: bytes = bCRLF  # Bytes newline


def changeNewline(nlType: NL_TYPE) -> None:
    """
    Changes the newline used.
    :param nlType: The new type
    """
    global NL, bNL
    if nlType == "CR":
        NL, bNL = CR, bCR
    elif nlType == "LF":
        NL, bNL = LF, bLF
    elif nlType == "CRLF":
        NL, bNL = CRLF, bCRLF
    else:
        raise ValueError


__all__ = [
    "readFile", "writeFile",
    "CR", "LF", "CRLF",
    "bCR", "bLF", "bCRLF",
    "cCR", "cLF",
    "NL", "bNL",
    "changeNewline"
]
