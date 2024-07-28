#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import copy
from typing import Iterable, Self, Optional, Iterator

from kutil.buffer.ByteBuffer import ByteBuffer, bCRLF


class MemoryByteBuffer(ByteBuffer[bytearray]):
    _data: bytearray
    _pointer: int
    _dataBuffer: Optional[object]  # DataBuffer

    def __init__(self, dataOrLength: Iterable[int] | int = 0):
        """
        Creates a MemoryByteBuffer either by a length or its initial data.
        :param dataOrLength: Data length or initial data
        """
        super(MemoryByteBuffer, self).__init__(bytearray(dataOrLength))

    def readByte(self) -> int:
        self.assertHas(1)
        self._pointer += 1
        return self._data[self._pointer - 1]

    def readLastByte(self) -> int:
        assert len(self._data) > 0
        return self._data[-1]

    def read(self, amount: int) -> bytearray:
        if amount == 0:
            return bytearray()
        self.assertHas(amount)
        self._pointer += amount
        return self._data[self._pointer - amount:self._pointer]

    def readLine(self, newLine: bytes = bCRLF) -> bytearray:
        amount: int = self.index(newLine)
        data: bytearray = self.read(amount) if amount > 0 else bytearray()
        self.skip(len(newLine))
        return data

    def index(self, seq: bytes) -> int:
        self.assertHas(len(seq))
        for i in range(self.leftLength() - len(seq) + 1):
            if self._data[self._pointer + i:self._pointer + i + len(seq)] == seq:
                return i
        raise IndexError

    def skip(self, amount: int) -> Self:
        assert amount > 0
        self.assertHas(amount)
        self._pointer += amount
        return self

    def back(self, amount: int) -> Self:
        assert amount > 0
        self.assertHas(-amount)
        self._pointer -= amount
        return self

    def fullLength(self) -> int:
        return len(self._data)

    def readRest(self) -> bytearray:
        amount: int = self.leftLength()
        if amount == 0:
            return bytearray(0)
        self.assertHas(1)
        self._pointer += amount
        return self._data[self._pointer - amount:self._pointer]

    def writeByte(self, byte: int, i: int = -1) -> Self:
        if i == -1:
            self._data.append(byte)
        else:
            self._data.insert(i, byte)
        return self

    def write(self, data: Iterable[int], i: int = -1) -> Self:
        if i == -1:
            self._data.extend(data)
        else:
            for byteI, byte in enumerate(data):
                self.writeByte(byte, i + byteI)
        return self

    def export(self) -> bytes:
        return bytes(self._data)

    def reset(self, data: Optional[Iterable[int]] = None) -> Self:
        self.resetPointer()
        self._data.clear()
        if data is not None:
            self._data.extend(data)
        return self

    def resetBeforePointer(self) -> Self:
        self._data = self._data[self._pointer:]
        self.resetPointer()
        return self

    def resetPointer(self) -> Self:
        self._pointer = 0
        return self

    def assertCanRead(self) -> None:
        pass  # Can read from

    def assertCanWrite(self) -> None:
        pass  # Can write to

    def copy(self) -> Self:
        copyBuff = MemoryByteBuffer()
        copyBuff._data = copy.copy(self._data)
        copyBuff._pointer = self._pointer
        return copyBuff

    def __repr__(self) -> str:
        return (f"MemoryByteBuffer(length={len(self._data)}, bytes_left={self.leftLength()}, "
                f"pointer={self._pointer}, cached_DataBuffer={self._dataBuffer is not None})")

    def __iter__(self) -> Iterator[int]:
        for byte in self._data:
            yield byte


__all__ = ["MemoryByteBuffer"]
