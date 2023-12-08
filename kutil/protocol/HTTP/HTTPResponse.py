#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from kutil.protocol.HTTP.HTTPRequest import HTTPRequest
from kutil.protocol.AbstractProtocol import NeedMoreDataError
from typing import Final, Optional


class HTTPResponse:
    VERSION: Final[bytes] = HTTPRequest.VERSION
    CRLF: Final[bytes] = HTTPRequest.CRLF
    SP: Final[bytes] = HTTPRequest.SP
    HEADER_SEP: Final[bytes] = HTTPRequest.HEADER_SEP

    statusCode: int
    statusPhrase: str
    headers: HTTPHeaders
    body: bytes

    def __init__(self, statusCode: Optional[int] = None, statusPhrase: Optional[str] = None,
                 headers: Optional[HTTPHeaders] = None, body: Optional[bytes] = None):
        self.statusCode = statusCode or 200
        self.statusPhrase = statusPhrase or "OK"
        self.headers = headers or {}
        self.body = body or b''

    def write(self, buff: ByteBuffer):
        # Status line
        buff.write(self.VERSION).write(self.SP).write(self.enc(str(self.statusCode)))
        buff.write(self.SP).write(self.enc(self.statusPhrase)).write(self.CRLF)
        # Headers
        for name, value in self.headers.items():
            buff.write(self.enc(name)).write(self.HEADER_SEP).write(self.enc(value)).write(self.CRLF)
        buff.write(self.CRLF)
        # Body
        buff.write(self.body)

    def read(self, buff: ByteBuffer):
        version, statusCode, statusPhrase = buff.readLine(self.CRLF).split(self.SP, maxsplit=2)
        self.statusCode = int(self.dec(statusCode))
        self.statusPhrase = self.dec(statusPhrase)
        if version != self.VERSION:
            raise ValueError
        line: bytearray = buff.readLine(self.CRLF)
        self.headers = HTTPHeaders()
        while len(line) > 0:
            name, value = line.split(self.HEADER_SEP, maxsplit=1)
            self.headers[self.dec(name)] = self.dec(value)
            line = buff.readLine(self.CRLF)
        self.body = bytes(buff.readAll())
        # Content-Length is required lol, is not provided (None), throws ValueError --> NeedMoreDataError
        if int(self.headers.get("Content-Length")) > len(self.body):
            raise NeedMoreDataError

    @staticmethod
    def enc(thing: str) -> bytes:
        return HTTPRequest.enc(thing)

    @staticmethod
    def dec(thing: bytes) -> str:
        return HTTPRequest.dec(thing)
