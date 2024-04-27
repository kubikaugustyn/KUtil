#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Optional
from random import randint

from kutil.typing_help import neverCall
from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.Serializable import Serializable
from kutil.protocol.HTTP.HTTPRequest import HTTPThing


class SSEMessage(Serializable):
    eventName: str
    data: Optional[bytes]
    eventID: bytes

    def __init__(self, eventName: Optional[str] = None, data: Optional[bytes] = None,
                 eventID: Optional[bytes] = None):
        self.eventName = eventName or "message"
        self.data = data
        self.eventID = eventID or HTTPThing.enc(str(randint(0, 0xFFFFFFFF)))

    def write(self, buff: ByteBuffer):
        buff.write(b'event: ').write(HTTPThing.enc(self.eventName)).write(HTTPThing.CRLF)
        if self.data:
            buff.write(b'data: ').write(self.data).write(HTTPThing.CRLF)
        if self.eventID:
            buff.write(b'id: ').write(self.eventID).write(HTTPThing.CRLF)
        buff.write(HTTPThing.CRLF)

    def read(self, buff: ByteBuffer):
        # TODO Actually implement a SSE client
        neverCall(buff)  # SSE is only meant to be sent
