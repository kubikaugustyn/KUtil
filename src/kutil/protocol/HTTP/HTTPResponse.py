#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from kutil.protocol.HTTP.HTTPRequest import HTTPThing
from kutil.protocol.AbstractProtocol import NeedMoreDataError
from typing import Optional


class HTTPResponse(HTTPThing):
    statusCode: int
    statusPhrase: str

    def __init__(self, statusCode: Optional[int] = None, statusPhrase: Optional[str] = None,
                 headers: Optional[HTTPHeaders] = None, body: Optional[bytes] = None):
        super().__init__(headers, body)
        self.statusCode = statusCode or 200
        self.statusPhrase = statusPhrase or "OK"

    def write(self, buff: ByteBuffer):
        # Status line
        buff.write(self.VERSION).write(self.SP).write(self.enc(str(self.statusCode)))
        buff.write(self.SP).write(self.enc(self.statusPhrase)).write(self.CRLF)
        # Rest
        self.writeRest(buff)

    def read(self, buff: ByteBuffer):
        # Status line
        version, statusCode, statusPhrase = buff.readLine(self.CRLF).split(self.SP, maxsplit=2)
        self.statusCode = int(self.dec(statusCode))
        self.statusPhrase = self.dec(statusPhrase)
        if version != self.VERSION:
            raise ValueError
        # Rest
        self.readRest(buff)
        # Content-Length is required lol, if not provided (None), throws ValueError --> NeedMoreDataError
        if int(self.headers.get("Content-Length")) > len(self.body):
            raise NeedMoreDataError

    def __str__(self) -> str:
        return (f"<HTTP Response - {self.dec(self.VERSION)} {self.statusCode} {self.statusPhrase}, "
                f"{len(self.headers)} headers, body length: {len(self.body)}>")
