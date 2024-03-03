#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Callable

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.AbstractProtocol import AbstractProtocol, NeedMoreDataError
from kutil.protocol.ProtocolConnection import ProtocolConnection
from kutil.protocol.TCPConnection import TCPProtocol
from kutil.protocol.HTTP.HTTPRequest import HTTPRequest
from kutil.protocol.HTTP.HTTPResponse import HTTPResponse

type OnHTTPDataListener = Callable[[ProtocolConnection, HTTPResponse], None]


class HTTPProtocol(AbstractProtocol):
    name = "HTTPProtocol"

    def unpackData(self, buff: ByteBuffer) -> HTTPResponse:
        resp = HTTPResponse()
        resp.read(buff)  # Don't catch errors!
        return resp

    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        return buff  # Nothing lol

    def packData(self, data: HTTPRequest, buff: ByteBuffer):
        data.write(buff)

    def packSubProtocol(self, buff: ByteBuffer):
        pass  # Nothing lol


class HTTPConnection(ProtocolConnection):
    def __init__(self, address: tuple[str, int], onData: OnHTTPDataListener):
        super().__init__(address, [TCPProtocol(self), HTTPProtocol(self)], onData)
