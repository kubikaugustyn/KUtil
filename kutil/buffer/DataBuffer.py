#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import binascii
import zlib
from typing import Self

from kutil.buffer.ByteBuffer import ByteBuffer


class DataBuffer:
    buff: ByteBuffer

    def __init__(self, buff: ByteBuffer | None = None):
        self.buff = buff if buff is not None else ByteBuffer()

    # Writing
    def writeUInt8(self, num: int) -> Self:
        self.buff.writeByte(num)
        return self

    def writeUInt16(self, num: int) -> Self:
        self.buff.write(num.to_bytes(2, "big", signed=False))
        return self

    def writeUInt32(self, num: int) -> Self:
        self.buff.write(num.to_bytes(4, "big", signed=False))
        return self

    def writeUInt64(self, num: int) -> Self:
        self.buff.write(num.to_bytes(8, "big", signed=False))
        return self

    def writeUIntN(self, num: int, byteSize: int) -> Self:
        self.buff.write(num.to_bytes(byteSize, "big", signed=False))
        return self

    def writeInt8(self, num: int) -> Self:
        # I don't want to mess with the negative stuff
        self.buff.write(num.to_bytes(1, "big", signed=True))
        return self

    def writeInt16(self, num: int) -> Self:
        self.buff.write(num.to_bytes(2, "big", signed=True))
        return self

    def writeInt32(self, num: int) -> Self:
        self.buff.write(num.to_bytes(4, "big", signed=True))
        return self

    def writeInt64(self, num: int) -> Self:
        self.buff.write(num.to_bytes(8, "big", signed=True))
        return self

    def writeIntN(self, num: int, byteSize: int) -> Self:
        self.buff.write(num.to_bytes(byteSize, "big", signed=True))
        return self

    def writeUInt(self, num: int, byteSize: int) -> Self:
        if byteSize == 1:
            self.writeUInt8(num)
        elif byteSize == 2:
            self.writeUInt16(num)
        elif byteSize == 4:
            self.writeUInt32(num)
        elif byteSize == 8:
            self.writeUInt64(num)
        else:
            raise ValueError(f"Invalid byteSize {byteSize}")
        return self

    def writeInt(self, num: int, byteSize: int) -> Self:
        if byteSize == 1:
            self.writeInt8(num)
        elif byteSize == 2:
            self.writeInt16(num)
        elif byteSize == 4:
            self.writeInt32(num)
        elif byteSize == 8:
            self.writeInt64(num)
        else:
            raise ValueError(f"Invalid byteSize {byteSize}")
        return self

    def writeString(self, string: str, lengthByteSize: int = 4) -> Self:
        self.writeUInt(len(string), lengthByteSize)
        self.buff.write(string.encode("utf-8"))
        return self

    def writeBool(self, boolean: bool) -> Self:
        self.buff.writeByte(0x01 if boolean else 0x00)
        return self

    def writeCRC32(self, data: bytes) -> Self:
        crc32: int = zlib.crc32(data)
        self.writeUInt32(crc32)
        return self

    # Reading
    def readUInt8(self) -> int:
        return self.buff.readByte()

    def readUInt16(self) -> int:
        return int.from_bytes(self.buff.read(2), "big", signed=False)

    def readUInt32(self) -> int:
        return int.from_bytes(self.buff.read(4), "big", signed=False)

    def readUInt64(self) -> int:
        return int.from_bytes(self.buff.read(8), "big", signed=False)

    def readUIntN(self, byteSize: int) -> int:
        return int.from_bytes(self.buff.read(byteSize), "big", signed=False)

    def readInt8(self) -> int:
        # I don't want to mess with the negative stuff
        return int.from_bytes(self.buff.read(1), "big", signed=True)

    def readInt16(self) -> int:
        return int.from_bytes(self.buff.read(2), "big", signed=True)

    def readInt32(self) -> int:
        return int.from_bytes(self.buff.read(4), "big", signed=True)

    def readInt64(self) -> int:
        return int.from_bytes(self.buff.read(8), "big", signed=True)

    def readIntN(self, byteSize: int) -> int:
        return int.from_bytes(self.buff.read(byteSize), "big", signed=True)

    def readUInt(self, byteSize: int) -> int:
        if byteSize == 1:
            return self.readUInt8()
        elif byteSize == 2:
            return self.readUInt16()
        elif byteSize == 4:
            return self.readUInt32()
        elif byteSize == 8:
            return self.readUInt64()
        raise ValueError(f"Invalid byteSize {byteSize}")

    def readInt(self, byteSize: int) -> int:
        if byteSize == 1:
            return self.readInt8()
        elif byteSize == 2:
            return self.readInt16()
        elif byteSize == 4:
            return self.readInt32()
        elif byteSize == 8:
            return self.readInt64()
        raise ValueError(f"Invalid byteSize {byteSize}")

    def readString(self, lengthByteSize: int = 4) -> str:
        strLen = self.readUInt(lengthByteSize)
        return self.buff.read(strLen).decode("utf-8")

    def readBool(self) -> bool:
        return self.buff.readByte() == 0x01

    def readAndCompareCRC32(self, dataToCompare: bytes) -> bool:
        checkCrc32: int = zlib.crc32(dataToCompare)
        crc32 = self.readUInt32()
        return checkCrc32 == crc32
