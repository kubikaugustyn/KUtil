#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC
from kutil.buffer.ByteBuffer import ByteBuffer


class Serializable(ABC):
    @abstractmethod
    def write(self, buff: ByteBuffer):
        raise NotImplementedError

    @abstractmethod
    def read(self, buff: ByteBuffer):
        raise NotImplementedError
