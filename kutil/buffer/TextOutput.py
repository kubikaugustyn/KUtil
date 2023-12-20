#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Optional

from kutil.buffer.ByteBuffer import ByteBuffer


class TextOutput:
    NL: bytes = b"\r\n"

    buff: ByteBuffer
    encoding: str
    callPrint: bool

    def __init__(self, data: Optional[str] = None, buff: Optional[ByteBuffer] = None, encoding: str = "utf-8",
                 callPrint: bool = False):
        self.encoding = encoding
        self.buff = buff or ByteBuffer()
        self.callPrint = callPrint
        if data is not None:
            self.print(data)

    def clear(self):
        self.buff.reset()

    def __str__(self):
        return self.export()

    def print(self, *data: str, newline: bool = True, sep: str = " "):
        sepBytes: bytes = sep.encode(self.encoding)
        for i, thing in enumerate(data):
            self.buff.write(str(thing).encode(self.encoding))
            if len(data) > 1 and i < len(data) - 1:
                self.buff.write(sepBytes)
        if newline:
            self.buff.write(self.NL)
        if self.callPrint:
            print(*data, sep=sep, end=(self.NL if newline else ""))

    def export(self) -> str:
        return self.buff.export().decode(self.encoding)
