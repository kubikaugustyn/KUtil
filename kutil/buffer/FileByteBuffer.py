#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

from typing import Iterable, Self, Optional, BinaryIO, Iterator

from kutil.buffer.ByteBuffer import ByteBuffer, OutOfBoundsReadError, bCRLF


class FileByteBuffer(ByteBuffer[BinaryIO]):
    _data: BinaryIO

    def __init__(self, file: BinaryIO | None):
        """
        Creates a FileByteBuffer either blank or by an open binary file handle.
        :param file: The open binary file handle or None for an in-memory file handle
         (not recommended)
        """
        from kutil.io.native_io_wrapper import BytesIO
        super(FileByteBuffer, self).__init__(file if file is not None else BytesIO(b''))

    def _readInnerWithoutPointer(self, *, pointer: int, amount: int) -> bytes:
        self.assertCanRead()

        self._syncPointer(pointer)
        data: bytes = self._data.read(amount)
        if len(data) < amount:
            raise OutOfBoundsReadError(f"Not enough bytes (reading {amount}, but {len(data)}"
                                       f" are available until EOF)")
        assert len(data) == amount
        return data

    def _readInner(self, *, amount: int) -> bytes:
        self.assertHas(amount)

        data: bytes = self._readInnerWithoutPointer(pointer=self._pointer, amount=amount)
        self._pointer += amount
        return data

    def readByte(self) -> int:
        return self._readInner(amount=1)[0]

    def readLastByte(self) -> int:
        return self._readInnerWithoutPointer(pointer=-1, amount=1)[0]

    def read(self, amount: int) -> bytearray:
        if amount == 0:
            return bytearray()
        elif amount < 0:
            raise ValueError("Cannot read a negative amount of bytes")
        return bytearray(self._readInner(amount=amount))

    def readLine(self, newLine: bytes = bCRLF) -> bytearray:
        amount: int = self.index(newLine)
        data: bytearray = self.read(amount) if amount > 0 else bytearray()
        self.skip(len(newLine))
        return data

    def index(self, seq: bytes) -> int:
        self.assertHas(len(seq))

        for ptr, i in enumerate(range(self.leftLength() - len(seq) + 1), start=self._pointer):
            part: bytes = self._readInnerWithoutPointer(pointer=ptr, amount=len(seq))
            if part == seq:
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
        self._syncPointer(-1)
        fileLen: int = self._data.tell()
        return fileLen

    def leftLength(self) -> int:
        return self.fullLength() - self._pointer

    def readRest(self) -> bytearray:
        if self.leftLength() == 0:
            return bytearray(0)
        self.assertHas(1)
        self._syncPointer()
        dataLeft: bytes = self._data.read()  # Read until EOF
        self._pointer += len(dataLeft)
        return bytearray(dataLeft)

    def _syncPointer(self, pointer: int | None = None) -> None:
        """
        Synchronizes the pointer of the buffer with the BinaryIO object
        ("pointer" is left intact, and the BinaryIO's pointer is set to "pointer")

        The synchronization is hopefully a little bit optimized,
        see https://stackoverflow.com/a/51801410 for a reason why.

        :param pointer: The pointer to synchronize the BinaryIO's pointer to.
         If set to ``None``, ``self._pointer`` is used.
         If set to ``-1``, the pointer is set to EOF.
         Otherwise, the argument is used.
        """
        from kutil.io.native_io_wrapper import SEEK_SET, SEEK_CUR, SEEK_END
        self.assertCanSeek()

        if pointer is None:
            pointer = self._pointer
        elif pointer == -1:  # Special case - sync to EOF
            self._data.seek(0, SEEK_END)
            return
        assert pointer >= 0

        if self._data.tell() == pointer:
            return  # No movement is required

        deltaCur: int = pointer - self._data.tell()
        deltaSet: int = pointer  # Must be inherently >= 0

        if abs(deltaCur) > deltaSet:  # SEEK_SET has a lower delta (is closer)
            assert self._data.seek(deltaSet, SEEK_SET) == pointer
        else:  # SEEK_CUR has a lower delta (is closer)
            assert self._data.seek(deltaCur, SEEK_CUR) == pointer

    def _writeInternal(self, *, data: Iterable[int], i: int = -1) -> None:
        """
        Writes ``data`` at a certain position in the buffer (at the index ``i``).

        Makes sure to insert the data instead of overwriting it,
        adding additional O(n) time when `i != -1`

        :param data: The data to write, as iterable of integers in the range of 0-255 inclusive of
        :param i: The index to write the data to.
         If -1, the data is written at the end of the file.
        """
        self._syncPointer(i)
        if i == -1:
            dataAfter: bytes = bytes(0)
        # We have to manually shift the data in the range [i:EOF] to [i + len(data):EOF + len(data)]
        # As by default, Python will overwrite the data,
        # and we want the same behavior as the ByteBuffer has - it inserts the data.
        else:
            dataAfter: bytes = self._data.read()  # Until EOF
            self._syncPointer(i)

        dataBytes: bytes = bytes(data)
        assert self._data.write(dataBytes) == len(dataBytes)
        if len(dataAfter) > 0:
            assert self._data.write(dataAfter) == len(dataAfter)

    def writeByte(self, byte: int, i: int = -1) -> Self:
        self._writeInternal(data=[byte], i=i)
        return self

    def write(self, data: Iterable[int], i: int = -1) -> Self:
        self._writeInternal(data=data, i=i)
        return self

    def export(self) -> bytes:
        return self._readInnerWithoutPointer(pointer=0, amount=self.fullLength())

    def reset(self, data: Optional[Iterable[int]] = None) -> Self:
        self.resetPointer()
        self._syncPointer()  # self._pointer should be 0
        self._data.truncate(0)  # Clear all the file's contents
        if data is not None:
            self.write(data)
        return self

    def resetBeforePointer(self) -> Self:
        # Read the data to leave intact
        dataLeft: bytes = self._readInnerWithoutPointer(pointer=self._pointer,
                                                        amount=self.leftLength())
        # Write the data to the beginning of the BinaryIO
        self._syncPointer(0)
        assert self._data.write(dataLeft) == len(dataLeft)
        # Remove the leftover data
        self._syncPointer(0)
        self._data.truncate(len(dataLeft))

        self.resetPointer()
        return self

    def resetPointer(self) -> Self:
        self._pointer = 0
        self._syncPointer()
        return self

    def assertCanRead(self) -> None:
        from kutil.io.native_io_wrapper import UnsupportedOperation
        self.assertCanSeek()
        if not self._data.readable():
            raise UnsupportedOperation(
                "Cannot write to a non-readable file wrapped in a FileByteBuffer")

    def assertCanWrite(self) -> None:
        from kutil.io.native_io_wrapper import UnsupportedOperation
        self.assertCanSeek()
        if not self._data.writable():
            raise UnsupportedOperation(
                "Cannot write to a non-writable file wrapped in a FileByteBuffer")

    def assertCanSeek(self) -> None:
        """
        Checks if the buffer can be seeked.

        :exception UnsupportedOperation: If the buffer cannot be seeked
        """
        from kutil.io.native_io_wrapper import UnsupportedOperation
        if self._data.closed:
            raise UnsupportedOperation(
                "Cannot write to or read from a closed file wrapped in a FileByteBuffer")
        elif not self._data.seekable():
            raise UnsupportedOperation(
                "Cannot write to or read from a non-seekable file wrapped in a FileByteBuffer")

    def copy(self) -> Self:
        copyBuff = FileByteBuffer(None)  # Will create an in-memory buffer

        # Copy the data 10MB at a time
        self._syncPointer(0)
        copyBuff._syncPointer(0)
        while True:
            chunk = self._data.read(1024 * 1024 * 10)
            if len(chunk) == 0:
                break
            assert copyBuff._data.write(chunk) == len(chunk)

        copyBuff._pointer = self._pointer
        return copyBuff

    def __repr__(self) -> str:
        return (f"FileByteBuffer(length={self.fullLength()}, bytes_left={self.leftLength()}, "
                f"pointer={self._pointer}, file={repr(self._data)}), "
                f"cached_DataBuffer={self._dataBuffer is not None})")

    def __iter__(self) -> Iterator[int]:
        for byte in self.export():  # A lazy solution to re-use code
            yield byte


__all__ = ["FileByteBuffer"]
