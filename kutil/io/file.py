#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import json
import os.path

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.FileByteBuffer import FileByteBuffer
from kutil.typing_help import FinalStr, Final, Literal, overload, BinaryIO

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
    f: BinaryIO | None = None
    try:
        f = open(path, "rb")

        # Streamable stuff
        if output == "json":
            return json.load(f)
        elif output == "buffer":
            return FileByteBuffer(f)

        # Non-streamable stuff
        content = f.read()
        if output == "bytes":
            return content
        elif output == "bytearray":
            return bytearray(content)
        elif output == "text":
            return content.decode(encoding)

        # Unknown
        else:
            raise ValueError("Unknown output kind.")
    # Make sure to close the file
    finally:
        if f is not None and not f.closed:
            f.close()


# Write file
def writeFile(path: str, data: OUTPUT, encoding: str = "utf-8") -> None:
    # Special case: JSON
    if isinstance(data, dict):
        with open(path, "w", encoding=encoding) as txtFile:
            json.dump(data, txtFile)
        return
    # Special case: FileByteBuffer
    elif isinstance(data, FileByteBuffer):
        with open(path, "wb") as f:
            # Copy the files very efficiently (hopefully)
            data.copyInto(FileByteBuffer(f))
        return

    # Other cases create a byte object in memory
    with open(path, "wb") as f:
        if isinstance(data, bytes):
            content = data
        elif isinstance(data, bytearray):
            content = bytes(data)
        elif isinstance(data, str):
            content = data.encode(encoding)
        elif isinstance(data, ByteBuffer):
            content = data.export()
        else:
            raise ValueError("Unknown data kind.")

        f.write(content)


# Newline stuff
type NL_TYPE = Literal["CR", "LF", "CRLF"]
NL_TYPES: set[str] = {"CR", "LF", "CRLF"}
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


# TODO Fix config and make this possible
# changeNewline(Config().io.newline)

def splitFileExtension(path: str) -> tuple[str, str]:
    fn, ext = os.path.splitext(os.path.basename(path))
    return fn, ext


def getFileName(path: str) -> str:
    return splitFileExtension(path)[0]


def getFileExtension(path: str) -> str:
    return splitFileExtension(path)[1]


__all__ = [
    "readFile", "writeFile",
    "CR", "LF", "CRLF",
    "bCR", "bLF", "bCRLF",
    "cCR", "cLF",
    "NL", "bNL",
    "changeNewline",
    "splitFileExtension", "getFileName", "getFileExtension"
]
