#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Iterable, TypeVar, Iterator

TBidirectionalByteArray = TypeVar("TBidirectionalByteArray", bound="BidirectionalByteArray")


class BidirectionalByteArray:
    data: bytearray
    dataNegative: bytearray

    def __init__(self):
        self.data = bytearray(1)
        self.dataNegative = bytearray(0)

    def read(self, pos: int) -> int:
        try:
            self.has(pos)
        except AssertionError:
            self.extendTo(pos)
        if pos >= 0:
            return self.data[pos]
        else:
            return self.dataNegative[abs(pos) - 1]

    def __len__(self) -> int:
        return len(self.data) + len(self.dataNegative)

    def writeByte(self, byte: int, pos: int) -> TBidirectionalByteArray:
        self.extendTo(pos)
        if pos >= 0:
            self.data[pos] = byte
        else:
            self.dataNegative[abs(pos) - 1] = byte
        return self

    def export(self) -> bytes:
        return bytes(self.dataNegative) + bytes(self.data)

    def getOffset(self) -> int:
        return -len(self.dataNegative)

    def reset(self, data: Iterable[int] | None = None, offset: int = 0) -> TBidirectionalByteArray:
        self.data.clear()
        assert data is None
        # if data is not None:
        #     self.data.extend(data)
        return self

    def has(self, pos: int) -> bool:
        if pos >= 0:
            assert len(self.data) >= pos + 1, "Not enough bytes"
        else:
            assert len(self.dataNegative) >= abs(pos), "Not enough bytes"
        return True

    def extendTo(self, pos: int):
        if pos >= 0:
            arr = self.data
            amount = pos + 1 - len(self.data)
        else:
            arr = self.dataNegative
            amount = abs(pos) - len(self.dataNegative)
        if amount <= 0:
            return
        arr.extend([0] * amount)

    def enumerate(self) -> Iterator[tuple[int, int]]:
        for i in range(len(self.dataNegative) - 1, -1, -1):
            yield -i - 1, self.dataNegative[i]
        for i, byte in enumerate(self.data):
            yield i, byte

    def __iter__(self):
        """Iterates over all bytes of the bytearray, ignoring the negative position."""
        for byte in self.export():
            yield byte
