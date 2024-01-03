#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Iterable, TypeVar

TByteBuffer = TypeVar("TByteBuffer", bound="ByteBuffer")


class ByteBuffer(Iterable[int]):
    data: bytearray
    pointer: int

    def __init__(self, dataOrLength: Iterable[int] | int = 0):
        self.data = bytearray(dataOrLength) if isinstance(dataOrLength, int) else bytearray(
            dataOrLength)
        self.pointer = 0

    def readByte(self) -> int:
        self.has(1)
        self.pointer += 1
        return self.data[self.pointer - 1]

    def read(self, amount: int) -> bytearray:
        self.has(amount)
        self.pointer += amount
        return self.data[self.pointer - amount:self.pointer]

    def readLine(self, newLine: bytes = b"\r\n") -> bytearray:
        amount: int = self.index(newLine)
        data: bytearray = self.read(amount) if amount > 0 else bytearray()
        self.skip(len(newLine))
        return data

    def index(self, seq: bytes) -> int:
        self.has(len(seq))
        for i in range(len(self) - len(seq) + 1):
            if self.data[self.pointer + i:self.pointer + i + len(seq)] == seq:
                return i
        raise IndexError

    def skip(self, amount: int):
        self.has(amount)
        self.pointer += amount

    def __len__(self) -> int:
        return len(self.data) - self.pointer

    def readAll(self) -> bytearray:
        if len(self) == 0:
            return bytearray(0)
        self.has(1)
        amount = len(self)
        self.pointer += amount
        return self.data[self.pointer - amount:self.pointer]

    def writeByte(self, byte: int, i: int = -1) -> TByteBuffer:
        if i == -1:
            self.data.append(byte)
        else:
            self.data.insert(i, byte)
        return self

    def write(self, data: Iterable[int], i: int = -1) -> TByteBuffer:
        if i == -1:
            self.data.extend(data)
        else:
            for byteI, byte in enumerate(data):
                self.writeByte(byte, i + byteI)
        return self

    def export(self) -> bytes:
        return bytes(self.data)

    def reset(self, data: Iterable[int] | None = None) -> TByteBuffer:
        self.resetPointer()
        self.data.clear()
        if data is not None:
            self.data.extend(data)
        return self

    def resetPointer(self) -> TByteBuffer:
        self.pointer = 0
        return self

    def has(self, amount: int) -> bool:
        if amount <= 0:
            raise ValueError("Invalid amount")
        if len(self.data) < self.pointer + amount:
            raise IndexError("Not enough bytes")
        return True

    def __iter__(self):
        """Iterates over all bytes of the buffer, ignoring and not mutating the pointer."""
        for byte in self.data:
            yield byte
