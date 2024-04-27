#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.protocol.AbstractProtocol import AbstractProtocol, NeedMoreDataError
from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.ProtocolConnection import ProtocolConnection, ConnectionClosed
from kutil.protocol.SSE import SSEMessage


class SSEProtocol(AbstractProtocol):
    name = "SSEProtocol"

    def unpackData(self, buff: ByteBuffer) -> SSEMessage:
        # print("SSE message:", buff.data)
        msg = SSEMessage()
        try:
            msg.read(buff)
        except Exception:
            raise NeedMoreDataError
        return msg

    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        raise RuntimeError  # Not possible
        # return buff  # Nothing lol

    def packData(self, data: SSEMessage, buff: ByteBuffer):
        data.write(buff)

    def packSubProtocol(self, buff: ByteBuffer):
        raise RuntimeError  # Not possible
        # pass  # Nothing lol


class SSEConnection(ProtocolConnection):
    pass
