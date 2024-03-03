#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import copy
from typing import Iterable, Self


class ByteBuffer(Iterable[int]):
    data: bytearray
    pointer: int

    def __init__(self, dataOrLength: Iterable[int] | int = 0):
        self.data = bytearray(dataOrLength) if isinstance(dataOrLength, int) else bytearray(
            dataOrLength)
        self.pointer = 0

    def readByte(self) -> int:
        self.assertHas(1)
        self.pointer += 1
        return self.data[self.pointer - 1]

    def readLastByte(self) -> int:
        assert len(self.data) > 0
        return self.data[-1]

    def read(self, amount: int) -> bytearray:
        if amount == 0:
            return bytearray()
        self.assertHas(amount)
        self.pointer += amount
        return self.data[self.pointer - amount:self.pointer]

    def readLine(self, newLine: bytes = b"\r\n") -> bytearray:
        amount: int = self.index(newLine)
        data: bytearray = self.read(amount) if amount > 0 else bytearray()
        self.skip(len(newLine))
        return data

    def index(self, seq: bytes) -> int:
        self.assertHas(len(seq))
        for i in range(len(self) - len(seq) + 1):
            if self.data[self.pointer + i:self.pointer + i + len(seq)] == seq:
                return i
        raise IndexError

    def skip(self, amount: int):
        assert amount > 0
        self.assertHas(amount)
        self.pointer += amount

    def back(self, amount: int):
        assert amount > 0
        self.assertHas(-amount)
        self.pointer -= amount

    def __len__(self) -> int:
        return len(self.data) - self.pointer

    def readRest(self) -> bytearray:
        if len(self) == 0:
            return bytearray(0)
        self.assertHas(1)
        amount = len(self)
        self.pointer += amount
        return self.data[self.pointer - amount:self.pointer]

    def writeByte(self, byte: int, i: int = -1) -> Self:
        if i == -1:
            self.data.append(byte)
        else:
            self.data.insert(i, byte)
        return self

    def write(self, data: Iterable[int], i: int = -1) -> Self:
        if i == -1:
            self.data.extend(data)
        else:
            for byteI, byte in enumerate(data):
                self.writeByte(byte, i + byteI)
        return self

    def export(self) -> bytes:
        return bytes(self.data)

    def reset(self, data: Iterable[int] | None = None) -> Self:
        self.resetPointer()
        self.data.clear()
        if data is not None:
            self.data.extend(data)
        return self

    def resetBeforePointer(self) -> Self:
        self.data = self.data[self.pointer:]
        self.resetPointer()
        return self

    def resetPointer(self) -> Self:
        self.pointer = 0
        return self

    def assertHas(self, amount: int) -> bool:
        if amount == 0:
            raise ValueError("Invalid amount")
        if amount < 0:
            if -amount > self.pointer:
                raise ValueError("Not enough bytes")
        else:
            if len(self.data) < self.pointer + amount:
                raise IndexError("Not enough bytes")
        return True

    def has(self, amount: int) -> bool:
        if amount == 0:
            return True
        if amount < 0:
            if -amount > self.pointer:
                return False
        else:
            if len(self.data) < self.pointer + amount:
                return False
        return True

    def copy(self) -> Self:
        copyBuff = ByteBuffer()
        copyBuff.data = copy.copy(self.data)
        copyBuff.pointer = self.pointer
        return copyBuff

    def __iter__(self):
        """Iterates over all bytes of the buffer, ignoring and not mutating the pointer."""
        for byte in self.data:
            yield byte
