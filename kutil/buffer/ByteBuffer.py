#  -*- coding: utf-8 -*-
"""
>>> from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer
>>> buff = MemoryByteBuffer()
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

from typing import Iterable, Self, Optional, Iterator, Any, final
from abc import ABC, abstractmethod

try:
    from kutil.io.file import bCRLF
except ImportError:
    bCRLF = b'\r\n'  # A lazy way to resolve circular imports


class OutOfBoundsReadError(BaseException):
    pass


class OutOfBoundsUndoError(BaseException):
    pass


class ByteBuffer[TData: Any](Iterable[int], ABC):
    _data: TData
    _pointer: int
    _dataBuffer: Optional[object]  # DataBuffer

    def __init__(self, data: TData):
        """
        Creates a ByteBuffer by its data.
        Called by subclasses.
        :param data: The data
        """
        self._data = data
        self._pointer = 0
        self._dataBuffer = None

    def __new__(cls, *args, **kwargs):
        if cls is ByteBuffer:
            import warnings
            from deprecation import \
                DeprecatedWarning  # FIXME Start using warnings.deprecated in Python 3.13
            from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer

            # Create a MemoryByteBuffer instead (for backwards compatability)
            instance = super().__new__(MemoryByteBuffer)

            # Deprecation warning, see where you instantiate ByteBuffer(...)
            warn = DeprecatedWarning(deprecated_in="0.0.12",
                                     details="You should not construct a raw ByteBuffer, as it is"
                                             " now an abstract base class. Use MemoryByteBuffer "
                                             "instead. It will construct a MemoryByteBuffer "
                                             "internally if you use it anyway.",
                                     removed_in=None,
                                     function="ByteBuffer.__init__(dataOrLength)")
            warnings.warn(warn, category=DeprecationWarning,
                          stacklevel=2)
        else:
            instance = super().__new__(cls)
        instance.__init__(*args, **kwargs)
        return instance

    @abstractmethod
    def readByte(self) -> int:
        """
        Reads the next byte from the buffer at the pointer.
        :return: The read byte
        """
        ...

    @abstractmethod
    def readLastByte(self) -> int:
        """
        Reads the last byte from the buffer, without modifying the pointer.
        :return: The last byte
        """
        ...

    @abstractmethod
    def read(self, amount: int) -> bytearray:
        """
        Reads the next amount bytes from the buffer at the pointer.
        :return: The read bytes
        """
        ...

    @abstractmethod
    def readLine(self, newLine: bytes = bCRLF) -> bytearray:
        """
        Reads the next bytes from the buffer at the pointer to a new line.
        :param newLine: The new line bytes to read until
        :return: The read line
        """
        ...

    @abstractmethod
    def index(self, seq: bytes) -> int:
        """
        Returns the index of the first byte in seq within the buffer from the pointer.
        :param seq: The bytes to find the index of.
        :return: The index of the first byte in seq within the buffer from the pointer
        :exception IndexError: If the sequence is not found
        """
        ...

    @abstractmethod
    def skip(self, amount: int) -> Self:
        """
        Skips the amount bytes of the buffer at the pointer.
        :param amount: The amount to skip
        :return: Self to support chaining
        """
        ...

    @abstractmethod
    def back(self, amount: int) -> Self:
        """
        Goes back the amount bytes of the buffer from the pointer.
        :param amount: The amount to go back by
        :return: Self to support chaining
        """
        ...

    @abstractmethod
    def fullLength(self) -> int:
        """
        Returns the full length of the buffer.
        :return: The full length
        """
        ...

    def leftLength(self) -> int:
        """
        Returns the length left of the buffer from the pointer.
        :return: The length left
        """
        return self.fullLength() - self._pointer

    @final
    def __len__(self) -> int:
        """
        Returns the length left of the buffer from the pointer.
        :return: The length left
        """
        return self.leftLength()

    @abstractmethod
    def readRest(self) -> bytearray:
        """
        Reads all bytes from the buffer starting at the pointer.
        :return: All the bytes left
        """
        ...

    @abstractmethod
    def writeByte(self, byte: int, i: int = -1) -> Self:
        """
        Writes a byte at the end or a particular index of the buffer,
        not caring about the current pointer.
        :param byte: The byte to write
        :param i: An index to write it to, -1 for the end
        :return: Self to support chaining
        """
        ...

    @abstractmethod
    def write(self, data: Iterable[int], i: int = -1) -> Self:
        """
        Writes data at the end or a particular index of the buffer,
        not caring about the current pointer.
        :param data: The bytes to write
        :param i: An index to write it to, -1 for the end
        :return: Self to support chaining
        """
        ...

    @abstractmethod
    def export(self) -> bytes:
        """
        Returns the current buffer's bytes.
        :return: The current buffer's bytes
        """
        ...

    @abstractmethod
    def reset(self, data: Optional[Iterable[int]] = None) -> Self:
        """
        Resets the buffer's data to the given data if provided and sets the pointer to 0.
        :param data: The data to reset the buffer with (optional)
        :return: Self to support chaining
        """
        ...

    @abstractmethod
    def resetBeforePointer(self) -> Self:
        """
        Removes the buffer's data before the pointer, setting the pointer to 0.
        :return: Self to support chaining
        """
        ...

    @abstractmethod
    def resetPointer(self) -> Self:
        """
        Sets the pointer to 0.
        :return: Self to support chaining
        """
        ...

    @final
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
        bytesLeft: int = self.leftLength()
        if amount < 0:
            if -amount > self._pointer:
                raise OutOfBoundsUndoError(f"Not enough bytes (going back by {-amount}, "
                                           f"but {self._pointer} had been read)")
        else:
            self.assertCanRead()
            if bytesLeft < amount:
                raise OutOfBoundsReadError(
                    f"Not enough bytes (reading {amount}, but {bytesLeft} are available)")

    @abstractmethod
    def assertCanRead(self) -> None:
        """
        Checks if the buffer can be read from.

        :exception UnsupportedOperation: If the buffer cannot be read from or seeked
        """
        ...

    @abstractmethod
    def assertCanWrite(self) -> None:
        """
        Checks if the buffer can be written to.

        :exception UnsupportedOperation: If the buffer cannot be written to or seeked
        """
        ...

    @final
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
            if self.leftLength() < amount:
                return False
        return True

    @abstractmethod
    def copy(self) -> Self:
        """
        Copies a buffer into a new buffer, with a new data copy.
        :return: The copied buffer
        """
        ...

    @final
    def getDataBuffer(self):
        """
        Returns the cached data buffer if it exists, otherwise returns None.

        For internal use only.
        :return: The DataBuffer or None
        """
        return self._dataBuffer

    @final
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

    @abstractmethod
    def __repr__(self) -> str:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[int]:
        """Iterates over all bytes of the buffer, ignoring and not mutating the pointer."""
        ...


