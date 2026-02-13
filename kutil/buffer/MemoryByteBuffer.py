#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import copy
from typing import Iterable, Self, Optional, Iterator, Never

from kutil.buffer.ByteBuffer import ByteBuffer, bCRLF


class MemoryByteBuffer(ByteBuffer[bytearray]):
    _data: bytearray

    def __init__(self, dataOrLength: Iterable[int] | int = 0):
        """
        Creates a MemoryByteBuffer either by a length or its initial data.
        :param dataOrLength: Data length or initial data
        """
        super(MemoryByteBuffer, self).__init__(bytearray(dataOrLength))

    def readByte(self) -> int:
        self.assertNotDestroyed()
        self.assertHas(1)
        self._pointer += 1
        return self._data[self._pointer - 1]

    def readLastByte(self) -> int:
        self.assertNotDestroyed()
        assert len(self._data) > 0
        return self._data[-1]

    def read(self, amount: int) -> bytearray:
        self.assertNotDestroyed()
        if amount == 0:
            return bytearray()
        self.assertHas(amount)
        self._pointer += amount
        return self._data[self._pointer - amount:self._pointer]

    def index(self, seq: bytes) -> int:
        self.assertNotDestroyed()
        self.assertHas(len(seq))
        for i in range(self.leftLength() - len(seq) + 1):
            if self._data[self._pointer + i:self._pointer + i + len(seq)] == seq:
                return i
        raise IndexError

    def fullLength(self) -> int:
        self.assertNotDestroyed()
        return len(self._data)

    def readRest(self) -> bytearray:
        self.assertNotDestroyed()
        amount: int = self.leftLength()
        if amount == 0:
            return bytearray(0)
        self.assertHas(1)
        self._pointer += amount
        return self._data[self._pointer - amount:self._pointer]

    def writeByte(self, byte: int, i: int = -1) -> Self:
        self.assertNotDestroyed()
        if i == -1:
            self._data.append(byte)
        else:
            self._data.insert(i, byte)
        return self

    def write(self, data: Iterable[int] | ByteBuffer, i: int = -1) -> Self:
        self.assertNotDestroyed()
        if i == -1:
            self._data.extend(data)
        else:
            for byteI, byte in enumerate(data):
                self.writeByte(byte, i + byteI)
        return self

    def export(self) -> bytes:
        self.assertNotDestroyed()
        return bytes(self._data)

    def reset(self, data: Optional[Iterable[int]] = None) -> Self:
        self.assertNotDestroyed()
        self.resetPointer()
        self._data.clear()
        if data is not None:
            self._data.extend(data)
        return self

    def resetBeforePointer(self) -> Self:
        self.assertNotDestroyed()
        self._data = self._data[self._pointer:]
        self.resetPointer()
        return self

    def resetPointer(self) -> Self:
        self.assertNotDestroyed()
        self._pointer = 0
        return self

    def assertCanRead(self) -> None:
        self.assertNotDestroyed()
        pass  # Can read from

    def assertCanWrite(self) -> None:
        self.assertNotDestroyed()
        pass  # Can write to

    def assertCanBeConvertedToAppended(self) -> None:
        self.assertNotDestroyed()
        pass # Can be converted to AppendedByteBuffer

    def copy(self) -> Self:
        self.assertNotDestroyed()
        copyBuff = MemoryByteBuffer()
        copyBuff._data = copy.copy(self._data)
        copyBuff._pointer = self._pointer
        return copyBuff

    def _destroyInner(self) -> None:
        self._data.clear()

    def __repr__(self) -> str:
        self.assertNotDestroyed()
        return (f"MemoryByteBuffer(length={self.fullLength()}, bytes_left={self.leftLength()}, "
                f"pointer={self._pointer}, cached_DataBuffer={self._dataBuffer is not None})")

    def __iter__(self) -> Iterator[int]:
        self.assertNotDestroyed()
        return iter(self._data)


__all__ = ["MemoryByteBuffer"]
