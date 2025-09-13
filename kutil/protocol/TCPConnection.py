#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Any, Callable

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.AbstractProtocol import AbstractProtocol
from kutil.protocol.ProtocolConnection import ProtocolConnection

type OnTCPDataListener = Callable[[ProtocolConnection, bytes], None]


class TCPProtocol(AbstractProtocol):
    name = "TCPProtocol"

    def unpackData(self, buff: ByteBuffer) -> bytes:
        return buff.readRest()

    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        return buff  # Nothing lol

    def packData(self, data: bytes, buff: ByteBuffer):
        buff.write(data)

    def packSubProtocol(self, buff: ByteBuffer):
        pass  # Nothing lol


class TCPConnection(ProtocolConnection):
    def __init__(self, address: tuple[str, int], onData: OnTCPDataListener):
        super().__init__(address, [TCPProtocol(self)], onData)
