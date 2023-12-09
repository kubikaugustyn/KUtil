#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.Serializable import Serializable
from kutil.protocol.HTTP.HTTPMethod import HTTPMethod
from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from typing import Final, Optional


class HTTPThing(Serializable):
    VERSION: Final[bytes] = b"HTTP/1.1"
    CRLF: Final[bytes] = b"\r\n"
    SP: Final[bytes] = b" "
    HEADER_SEP: Final[bytes] = b": "

    headers: HTTPHeaders
    body: bytes

    def __init__(self, headers: Optional[HTTPHeaders] = None, body: Optional[bytes] = None):
        self.headers = headers or {}
        self.body = body or b''

    def write(self, buff: ByteBuffer):
        raise NotImplementedError

    def writeRest(self, buff: ByteBuffer):
        for name, value in self.headers.items():
            buff.write(self.enc(str(name))).write(self.HEADER_SEP).write(self.enc(value)).write(self.CRLF)
        buff.write(self.CRLF)
        buff.write(self.body)

    def read(self, buff: ByteBuffer):
        raise NotImplementedError

    def readRest(self, buff: ByteBuffer):
        line: bytearray = buff.readLine(self.CRLF)
        self.headers = HTTPHeaders()
        while len(line) > 0:
            name, value = line.split(self.HEADER_SEP)
            self.headers[self.dec(name)] = self.dec(value)
            line = buff.readLine(self.CRLF)
        self.body = bytes(buff.readAll())

    @staticmethod
    def enc(thing: str) -> bytes:
        return thing.encode("utf-8")

    @staticmethod
    def dec(thing: bytes) -> str:
        return thing.decode("utf-8")


class HTTPRequest(HTTPThing):
    method: HTTPMethod
    requestURI: str

    def __init__(self, method: Optional[HTTPMethod] = None, requestURI: Optional[str] = None,
                 headers: Optional[HTTPHeaders] = None, body: Optional[bytes] = None):
        super().__init__(headers, body)
        self.method = method or HTTPMethod.GET
        self.requestURI = requestURI or "/"

    def write(self, buff: ByteBuffer):
        buff.write(self.method.value).write(self.SP).write(self.enc(self.requestURI)).write(self.SP).write(self.VERSION)
        buff.write(self.CRLF)
        self.writeRest(buff)

    def read(self, buff: ByteBuffer):
        method, requestURI, version = buff.readLine(self.CRLF).split(self.SP)
        self.method = HTTPMethod(method)
        self.requestURI = self.dec(requestURI)
        if version != self.VERSION:
            raise ValueError
        self.readRest(buff)

    def __str__(self) -> str:
        return (f"<HTTP Request - {self.method.name} {self.requestURI} {self.dec(self.VERSION)}, "
                f"{len(self.headers)} headers, body length: {len(self.body)}>")
