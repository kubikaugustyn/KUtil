#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Optional
from random import randint

from kutil.typing_help import neverCall
from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.Serializable import Serializable
from kutil.protocol.HTTP.HTTPRequest import HTTPThing


class SSEMessage(Serializable):
    eventName: Optional[str]
    data: bytes
    eventID: bytes

    def __init__(self, eventName: Optional[str] = None, data: Optional[bytes] = None,
                 eventID: Optional[bytes] = None):
        self.eventName = eventName
        self.data = data if data is not None else b''
        self.eventID = eventID or HTTPThing.enc(str(randint(0, 0xFFFFFFFF)))

    def write(self, buff: ByteBuffer):
        if self.eventName is not None:
            buff.write(b'event: ').write(HTTPThing.enc(self.eventName)).write(HTTPThing.CRLF)
        buff.write(b'data: ').write(self.data).write(HTTPThing.CRLF)
        if self.eventID is not None:
            buff.write(b'id: ').write(self.eventID).write(HTTPThing.CRLF)
        buff.write(HTTPThing.CRLF)

    def read(self, buff: ByteBuffer):
        # TODO Actually implement a SSE client
        neverCall(buff)  # SSE is only meant to be sent
