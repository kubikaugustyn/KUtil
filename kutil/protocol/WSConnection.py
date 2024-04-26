#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from base64 import b64encode
from hashlib import sha1
from typing import Any, Optional

from kutil.protocol.AbstractProtocol import AbstractProtocol, NeedMoreDataError
from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.ProtocolConnection import ProtocolConnection, ConnectionClosed
from kutil.protocol.WS import WSMessage, WSOpcode, WSData


class WSProtocol(AbstractProtocol):
    name = "WSProtocol"

    def unpackData(self, buff: ByteBuffer) -> WSMessage:
        # print("WS message:", buff.data)
        msg = WSMessage()
        try:
            msg.read(buff)
        except Exception:
            raise NeedMoreDataError
        return msg

    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        raise RuntimeError  # Not possible
        # return buff  # Nothing lol

    def packData(self, data: WSData | WSMessage, buff: ByteBuffer):
        if isinstance(data, WSData):
            msg: WSMessage = WSMessage()
            msg.opcode = WSOpcode.BINARY_FRAME if data.isBinary else WSOpcode.TEXT_FRAME
            msg.isFin = True
            msg.payload = data
            msg.write(buff)
            return
        data.write(buff)

    def packSubProtocol(self, buff: ByteBuffer):
        raise RuntimeError  # Not possible
        # pass  # Nothing lol

    @staticmethod
    def createAcceptHeader(key: str) -> str:
        acceptHash: sha1 = sha1()
        acceptHash.update(key.encode("utf-8"))
        acceptHash.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
        return b64encode(acceptHash.digest()).decode("utf-8")


class WSConnection(ProtocolConnection):
    dataBuffer: ByteBuffer

    def init(self):
        self.dataBuffer = ByteBuffer()

    def onDataInner(self, data: WSMessage, stoppedUnpacking: bool = False,
                    layer: Optional[AbstractProtocol] = None) -> bool | WSData:
        if data.opcode in (WSOpcode.BINARY_FRAME, WSOpcode.TEXT_FRAME):
            self.dataBuffer.write(data.payload.superSecretRawAccess)
            if data.isFin:
                message: WSData = WSData(self.dataBuffer.export())
                message.isBinary = data.opcode == WSOpcode.BINARY_FRAME
                return message
            return False
        if data.opcode == WSOpcode.CONNECTION_CLOSE:
            self.close(ConnectionClosed())
            return False
        print("Unknown frame:", data.opcode.name)
        self.close(ValueError("Unknown frame:" + data.opcode.name))
        return False


if __name__ == '__main__':
    assert WSProtocol.createAcceptHeader(
        "x3JJHMbDL1EzLkh9GBhXDw==") == "HSmrc0sMlYUkAGmm5OPpG2HaGWk="
