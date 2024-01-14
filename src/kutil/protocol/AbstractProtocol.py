#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Any
from abc import abstractmethod, ABC

from kutil.buffer import ByteBuffer


class NeedMoreDataError(BaseException): ...


class AbstractProtocol(ABC):
    name: str = "AbstractProtocol"
    connection: object

    def __init__(self, connection):
        from kutil.protocol.ProtocolConnection import ProtocolConnection
        if not isinstance(connection, ProtocolConnection):
            raise ValueError
        self.connection = connection

    @abstractmethod
    def unpackData(self, buff: ByteBuffer) -> Any:
        """Unpacks the data transferred by the protocol and returns it"""
        raise NotImplementedError

    @abstractmethod
    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        """Unpacks the data transferred by the protocol and returns the sub protocol's data"""
        raise NotImplementedError

    @abstractmethod
    def packData(self, data: Any, buff: ByteBuffer):
        """Packs the data transferred by the protocol into the provided (blank) buffer"""
        raise NotImplementedError

    @abstractmethod
    def packSubProtocol(self, buff: ByteBuffer):
        """Packs the data of a sub protocol into the protocol"""
        raise NotImplementedError
