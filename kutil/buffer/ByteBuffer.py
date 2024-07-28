#  -*- coding: utf-8 -*-
"""
>>> buff = ByteBuffer()
>>> _ = buff.writeByte(0x45).write(b'ab').write([0x45]) # I have to set it to _ to pass the test
>>> from kutil.buffer.DataBuffer import DataBuffer
>>> dBuff = DataBuffer(buff)
>>> hex(dBuff.readUInt32()) # 0x45, 'a', 'b', 0x45 in hex
'0x45616245'
>>> id(buff) == id(dBuff.buff)
True
>>> id(dBuff) == id(DataBuffer(buff)) # Check if the cache works
True
"""
__author__ = "kubik.augustyn@post.cz"

import copy
from typing import Iterable, Self, Optional


class OutOfBoundsReadError(BaseException):
    pass


class OutOfBoundsUndoError(BaseException):
    pass


class ByteBuffer(Iterable[int]):
    _data: bytearray
    _pointer: int
    _dataBuffer: Optional[object]  # DataBuffer

    def __init__(self, dataOrLength: Iterable[int] | int = 0):
        """
        Creates a ByteBuffer either by a length or its initial data.
        :param dataOrLength: Data length or initial data
        """
        self._data = bytearray(dataOrLength)
        self._pointer = 0
        self._dataBuffer = None

    def readByte(self) -> int:
        """
        Reads the next byte from the buffer at the pointer.
        :return: The read byte
        """
        self.assertHas(1)
        self._pointer += 1
        return self._data[self._pointer - 1]

    def readLastByte(self) -> int:
        """
        Reads the last byte from the buffer.
        :return: The last byte
        """
        assert len(self._data) > 0
        return self._data[-1]

    def read(self, amount: int) -> bytearray:
        """
        Reads the next amount bytes from the buffer at the pointer.
        :return: The read bytes
        """
        if amount == 0:
            return bytearray()
        self.assertHas(amount)
        self._pointer += amount
        return self._data[self._pointer - amount:self._pointer]

    def readLine(self, newLine: bytes = b"\r\n") -> bytearray:
        """
        Reads the next bytes from the buffer at the pointer to a new line.
        :param newLine: The new line bytes to read until
        :return: The read line
        """
        amount: int = self.index(newLine)
        data: bytearray = self.read(amount) if amount > 0 else bytearray()
        self.skip(len(newLine))
        return data

    def index(self, seq: bytes) -> int:
        """
        Returns the index of the first byte in seq within the buffer from the pointer.
        :param seq: The bytes to find the index of.
        :return: The index of the first byte in seq within the buffer from the pointer
        :exception IndexError: If the sequence is not found
        """
        self.assertHas(len(seq))
        for i in range(len(self) - len(seq) + 1):
            if self._data[self._pointer + i:self._pointer + i + len(seq)] == seq:
                return i
        raise IndexError

    def skip(self, amount: int) -> Self:
        """
        Skips the amount bytes of the buffer at the pointer.
        :param amount: The amount to skip
        :return: Self to support chaining
        """
        assert amount > 0
        self.assertHas(amount)
        self._pointer += amount
        return self

    def back(self, amount: int) -> Self:
        """
        Goes back the amount bytes of the buffer from the pointer.
        :param amount: The amount to go back by
        :return: Self to support chaining
        """
        assert amount > 0
        self.assertHas(-amount)
        self._pointer -= amount
        return self

    def __len__(self) -> int:
        """
        Returns the length left of the buffer from the pointer.
        :return:
        """
        return len(self._data) - self._pointer

    def readRest(self) -> bytearray:
        """
        Reads all bytes from the buffer starting at the pointer.
        :return: All the bytes left
        """
        if len(self) == 0:
            return bytearray(0)
        self.assertHas(1)
        amount = len(self)
        self._pointer += amount
        return self._data[self._pointer - amount:self._pointer]

    def writeByte(self, byte: int, i: int = -1) -> Self:
        """
        Writes a byte at the end or a particular index of the buffer,
        not caring about the current pointer.
        :param byte: The byte to write
        :param i: An index to write it to, -1 for the end
        :return: Self to support chaining
        """
        if i == -1:
            self._data.append(byte)
        else:
            self._data.insert(i, byte)
        return self

    def write(self, data: Iterable[int], i: int = -1) -> Self:
        """
        Writes data at the end or a particular index of the buffer,
        not caring about the current pointer.
        :param data: The bytes to write
        :param i: An index to write it to, -1 for the end
        :return: Self to support chaining
        """
        if i == -1:
            self._data.extend(data)
        else:
            for byteI, byte in enumerate(data):
                self.writeByte(byte, i + byteI)
        return self

    def export(self) -> bytes:
        """
        Returns the current buffer's bytes.
        :return: The current buffer's bytes
        """
        return bytes(self._data)

    def reset(self, data: Optional[Iterable[int]] = None) -> Self:
        """
        Resets the buffer's data to the given data if provided and sets the pointer to 0.
        :param data: The data to reset the buffer with (optional)
        :return: Self to support chaining
        """
        self.resetPointer()
        self._data.clear()
        if data is not None:
            self._data.extend(data)
        return self

    def resetBeforePointer(self) -> Self:
        """
        Removes the buffer's data before the pointer, setting the pointer to 0.
        :return: Self to support chaining
        """
        self._data = self._data[self._pointer:]
        self.resetPointer()
        return self

    def resetPointer(self) -> Self:
        """
        Sets the pointer to 0.
        :return: Self to support chaining
        """
        self._pointer = 0
        return self

    def assertHas(self, amount: int) -> None:
        """
        Checks if the buffer can read/undo the given number of bytes.

        See also has()
        :param amount: The amount to check
        :exception OutOfBoundsReadError: If the amount is positive and out of bounds
        :exception OutOfBoundsUndoError: If the amount is negative and out of bounds
        """
        if amount == 0:
            raise ValueError("Invalid amount")
        bytesLeft: int = len(self._data) - self._pointer
        if amount < 0:
            if -amount > self._pointer:
                raise OutOfBoundsUndoError(
                    f"Not enough bytes (going back by {-amount}, but {self._pointer} had been read)")
        else:
            if len(self._data) < self._pointer + amount:
                raise OutOfBoundsReadError(
                    f"Not enough bytes (reading {amount}, but {bytesLeft} are available)")

    def has(self, amount: int) -> bool:
        """
        Checks if the buffer can read/undo the given number of bytes.

        See also assertHas()
        :param amount: The amount to check
        :returns: True if the buffer can read/undo the given number of bytes, otherwise False
        """
        if amount == 0:
            return True
        if amount < 0:
            if -amount > self._pointer:
                return False
        else:
            if len(self._data) < self._pointer + amount:
                return False
        return True

    def copy(self) -> Self:
        """
        Copies a buffer into a new buffer, with a new data copy.
        :return: The copied buffer
        """
        copyBuff = ByteBuffer()
        copyBuff._data = copy.copy(self._data)
        copyBuff._pointer = self._pointer
        return copyBuff

    def getDataBuffer(self):
        """
        Returns the cached data buffer if it exists, otherwise returns None.

        For internal use only.
        :return: The DataBuffer or None
        """
        return self._dataBuffer

    def setDataBuffer(self, buffer):
        """
        Caches the data buffer.

        For internal use only.
        :param buffer: The data buffer to set
        """
        from kutil.buffer.DataBuffer import DataBuffer  # Hope it's cached
        assert isinstance(buffer, DataBuffer)
        self._dataBuffer = buffer

    def __str__(self) -> str:
        return repr(self)

    def __repr__(self) -> str:
        return (f"ByteBuffer(length={len(self._data)}, bytes_left={len(self)}, "
                f"pointer={self._pointer}, cached_DataBuffer={self._dataBuffer is not None})")

    def __iter__(self):
        """Iterates over all bytes of the buffer, ignoring and not mutating the pointer."""
        for byte in self._data:
            yield byte
