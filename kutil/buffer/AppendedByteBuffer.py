#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

import copy
from typing import Iterable, Self, Optional, Iterator, Never

from kutil.buffer.ByteBuffer import ByteBuffer, bCRLF


class IllegalManipulationError(BaseException):
    pass


type TInnerBufferRecord = tuple[ByteBuffer, int]  # Buffer, length
type TInnerBuffers = list[TInnerBufferRecord]


class AppendedByteBuffer(ByteBuffer[TInnerBuffers]):
    _data: TInnerBuffers

    def __init__(self, buffers: Iterable[ByteBuffer] | None = None):
        """
        Creates an AppendedByteBuffer from multiple byte buffers.

        You must NOT resize the underlying buffers of an AppendedByteBuffer.

        You must NOT depend on the underlying buffer's pointers after passing them to an AppendedByteBuffer.

        You cannot write arbitrarily to this buffer, as it only serves as a way to append buffers for reading, so you can only write to the end (e.g., append data or buffers).

        :param buffers: The byte buffers to append
        """
        if buffers is None:
            buffers = []

        records: TInnerBuffers = []
        for buffer in buffers:
            assert isinstance(buffer, ByteBuffer)
            records.append((buffer, buffer.fullLength()))
        super(AppendedByteBuffer, self).__init__(records)

    def readByte(self) -> int:
        self.assertNotDestroyed()
        self.assertHas(1)

        buffer: ByteBuffer | None = None
        start: int = 0
        for buffer in self.__iterate_buffers():
            if 0 <= self._pointer - start < buffer.fullLength():
                break
            start += buffer.fullLength()

        assert buffer is not None
        buffer.resetPointer()
        assert self._pointer - start >= 0, "Sanity check failed... :-/"
        if self._pointer - start > 0:
            buffer.skip(self._pointer - start)
        self._pointer += 1
        return buffer.readByte()

    def read(self, amount: int) -> bytearray:
        self.assertNotDestroyed()
        if amount == 0:
            return bytearray()
        self.assertHas(amount)
        startPtr: int = self._pointer
        self._pointer += amount

        parts: bytearray = bytearray()
        totalNeeded: int = amount
        start: int = 0
        for buffer in self.__iterate_buffers():
            if startPtr <= start + buffer.fullLength():
                relPtr: int = max(startPtr - start, 0)
                currentAmount: int = min(buffer.fullLength() - relPtr, totalNeeded)

                buffer.resetPointer()
                if relPtr > 0:
                    buffer.skip(relPtr)
                parts.extend(buffer.read(currentAmount))
                totalNeeded -= currentAmount
            if totalNeeded == 0:
                break

            start += buffer.fullLength()

        assert len(parts) == amount, "Sanity check failed... :-/"
        return parts

    def readLastByte(self) -> int:
        self.assertNotDestroyed()
        last, _ = self.__last_buffer()
        assert last is not None
        return last.readLastByte()

    def index(self, seq: bytes) -> int:
        self.assertNotDestroyed()
        from kutil.io.native_io_wrapper import UnsupportedOperation
        raise UnsupportedOperation(
            "You cannot look for a sequence in an AppendedByteBuffer from the pointer. This is "
            "like a NotImplementedError, if you really need this functionality, "
            "notify me to implement this.")

    def fullLength(self) -> int:
        self.assertNotDestroyed()
        return sum([buffer.fullLength() for buffer in self.__iterate_buffers()])

    def readRest(self) -> bytearray:
        self.assertNotDestroyed()
        from kutil.io.native_io_wrapper import UnsupportedOperation
        raise UnsupportedOperation(
            "You cannot read the rest of an AppendedByteBuffer from the pointer. This is like "
            "a NotImplementedError, if you need this functionality, use read(leftLength()) "
            "instead (not tested) and notify me to implement this.")

    def writeByte(self, byte: int, i: int = -1) -> Self:
        self.assertNotDestroyed()
        if i != -1:
            from kutil.io.native_io_wrapper import UnsupportedOperation
            raise UnsupportedOperation(
                "You cannot write to an AppendedByteBuffer at a specific index.")

        self.write(bytes([byte]))
        return self

    def write(self, data: Iterable[int] | ByteBuffer, i: int = -1) -> Self:
        self.assertNotDestroyed()
        from kutil.io.native_io_wrapper import UnsupportedOperation
        if i != -1:
            raise UnsupportedOperation(
                "You cannot write to an AppendedByteBuffer at a specific index.")

        if isinstance(data, ByteBuffer):
            self._data.append((data, data.fullLength()))
        else:
            from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer
            assert isinstance(data, Iterable)
            last, i = self.__last_buffer()
            writable: bool = last is not None and isinstance(last, MemoryByteBuffer)
            try:
                if writable:
                    assert isinstance(last, ByteBuffer)
                    last.assertCanWrite()
            except UnsupportedOperation:
                writable = False

            if last is None or not writable:
                data_bytes = bytearray(data)
                self._data.append((MemoryByteBuffer(data_bytes), len(data_bytes)))
            else:
                assert isinstance(last, MemoryByteBuffer), ("Final check failed. This is a good "
                                                            "sign, as if this wasn't caught, "
                                                            "it would be bad.")
                last.write(data)
                self._data[i] = (last, last.fullLength())

        return self

    def export(self, disable_warning: bool = False) -> bytes:
        self.assertNotDestroyed()
        if not disable_warning and self.fullLength() >= self.APPENDED_BUFFER_THRESHOLD:
            import warnings
            warnings.warn("You should not export a big AppendedByteBuffer, as it is "
                          "supposed to be used to be able to stream-read buffers. This completely "
                          "defeats the purpose of an AppendedByteBuffer.", UserWarning)

        def generate():
            for buffer in self.__iterate_buffers():
                yield from buffer.export()

        return bytes(generate())

    def reset(self, data: Optional[Iterable[int]] = None) -> Self:
        self.assertNotDestroyed()
        from kutil.io.native_io_wrapper import UnsupportedOperation
        raise UnsupportedOperation("You cannot reset an AppendedByteBuffer.")

    def resetBeforePointer(self) -> Self:
        self.assertNotDestroyed()
        from kutil.io.native_io_wrapper import UnsupportedOperation
        raise UnsupportedOperation("You cannot reset a part of an AppendedByteBuffer.")

    def resetPointer(self) -> Self:
        self.assertNotDestroyed()
        self._pointer = 0
        return self

    def assertCanRead(self) -> None:
        self.assertNotDestroyed()
        for buffer in self.__iterate_buffers():
            buffer.assertCanRead()

    def assertCanWrite(self) -> Never | None:
        self.assertNotDestroyed()
        pass  # You can... but it will be "messy"

    def assertCanBeConvertedToAppended(self) -> Never | None:
        self.assertNotDestroyed()
        pass  # This is fine, but it may get optimized

    def copy(self) -> Self:
        self.assertNotDestroyed()
        buffers: list[ByteBuffer] = list(self.__iterate_buffers())
        if len(buffers) != 0:
            buffers[-1] = buffers[-1].copy()

        copyBuff = AppendedByteBuffer(buffers)
        copyBuff._pointer = self._pointer
        return copyBuff

    def _destroyInner(self) -> None:
        for buffer, _ in self._data:
            buffer.destroy()
        self._data.clear()

    def __repr__(self) -> str:
        self.assertNotDestroyed()
        return (f"AppendedByteBuffer(length={self.fullLength()}, bytes_left={self.leftLength()}, "
                f"pointer={self._pointer}, buffers={self.buffers}, "
                f"cached_DataBuffer={self._dataBuffer is not None})")

    def __iter__(self) -> Iterator[int]:
        self.assertNotDestroyed()
        for buffer in self.__iterate_buffers():
            yield from buffer

    # Type-specific methods
    def __iterate_buffers(self) -> Iterator[ByteBuffer]:
        self.assertNotDestroyed()
        for buffer, length in self._data:
            if buffer.fullLength() != length:
                raise IllegalManipulationError("You must not resize the underlying buffers "
                                               "of an AppendedByteBuffer")
            yield buffer

    def __last_buffer(self) -> tuple[ByteBuffer | None, int]:
        self.assertNotDestroyed()
        iterator = self.__iterate_buffers()
        buffer: ByteBuffer | None = None
        i: int = -1

        try:
            while True:
                buffer = next(iterator)
                i += 1
        except StopIteration:
            return buffer, i

    @property
    def buffers(self) -> list[ByteBuffer]:
        self.assertNotDestroyed()
        return list(self.__iterate_buffers())


__all__ = ["AppendedByteBuffer"]
