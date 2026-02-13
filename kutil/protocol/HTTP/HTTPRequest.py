#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import json

from kutil.buffer.ByteBuffer import ByteBuffer, ByteBufferLike
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
    body: ByteBufferLike

    def __init__(self, headers: Optional[HTTPHeaders] = None,
                 body: Optional[ByteBufferLike] = None):
        self.headers = headers or {}
        self.body = body or b''

    def write(self, buff: ByteBuffer):
        raise NotImplementedError

    def writeRest(self, buff: ByteBuffer):
        # Make sure the content-length is present and correct
        if self.headers.get("X-Omit-Content-Length", "0") != "1":
            self.headers["Content-Length"] = str(len(self.body))
        else:
            # The magic header is the only way to implement SSE
            del self.headers["X-Omit-Content-Length"]

        for name, value in self.headers.items():
            buff.write(self.enc(str(name))).write(self.HEADER_SEP).write(self.enc(value)).write(
                self.CRLF)
        buff.write(self.CRLF)
        buff.write(self.body)

    def read(self, buff: ByteBuffer):
        raise NotImplementedError

    def readRest(self, buff: ByteBuffer):
        line: bytearray = buff.readLine(self.CRLF)
        self.headers = HTTPHeaders()
        while len(line) > 0:
            name, value = line.split(self.HEADER_SEP, maxsplit=1)
            self.headers[self.dec(name)] = self.dec(value)
            line = buff.readLine(self.CRLF)
        try:
            bodySize: int = max(0, int(self.headers.get("Content-Length", "0")))
        except (ValueError, TypeError):
            bodySize: int = 0
        self.body = bytes(buff.read(bodySize))

    @property
    def json(self) -> dict:
        if self.body is None or len(self.body) == 0:
            raise ValueError("Empty body")
        try:
            text = HTTPThing.dec(bytes(self.body))
        except UnicodeDecodeError as e:
            raise ValueError("Invalid body format") from e

        return json.loads(text)

    @property
    def text(self) -> str:
        if self.body is None or len(self.body) == 0:
            return ""
        try:
            text = HTTPThing.dec(bytes(self.body))
        except UnicodeDecodeError as e:
            raise ValueError("Invalid body format") from e

        return text

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
        buff.write(self.method.value).write(self.SP).write(self.enc(self.requestURI)).write(
            self.SP).write(self.VERSION)
        buff.write(self.CRLF)
        self.writeRest(buff)

    def read(self, buff: ByteBuffer):
        method, requestURI, version = buff.readLine(self.CRLF).split(self.SP)
        self.method = HTTPMethod(method)
        self.requestURI = self.dec(requestURI)
        if version != self.VERSION:
            raise ValueError(f"Unsupported HTTP version - supported {self.VERSION}, got {version}")
        self.readRest(buff)

    def __str__(self) -> str:
        return (f"<HTTP Request - {self.method.name} {self.requestURI} {self.dec(self.VERSION)}, "
                f"{len(self.headers)} headers, body length: {len(self.body)}>")
