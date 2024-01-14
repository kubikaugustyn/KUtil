#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique
from kutil import ByteBuffer
from kutil.buffer.Serializable import Serializable

@unique
class WSOpcode(Enum):
    CONTINUATION_FRAME = 0x0
    TEXT_FRAME = 0x1
    BINARY_FRAME = 0x2
    CONNECTION_CLOSE = 0x8
    PING = 0x9
    PONG = 0xA


class WSData:
    isBinary: bool
    __raw: bytes

    def __init__(self, data: bytes | bytearray | str | None = None):
        if data is None:
            data = b''
        self.isBinary = isinstance(data, bytes) or isinstance(data, bytearray)
        if self.isBinary:
            self.raw = bytes(data)
        else:
            self.text = data

    @property
    def superSecretRawAccess(self) -> bytes:
        """Lol. Just don't use this if you don't know what are you doing."""
        return self.__raw

    @property
    def raw(self) -> bytes:
        assert self.isBinary
        return self.__raw

    @raw.setter
    def raw(self, newBytes: bytes):
        assert self.isBinary
        self.__raw = newBytes

    @property
    def text(self) -> str:
        assert not self.isBinary
        return self.__raw.decode("utf-8")

    @text.setter
    def text(self, newText: str):
        assert not self.isBinary
        self.__raw = newText.encode("utf-8")

    @property
    def lenBytes(self) -> int:
        if len(self.__raw) <= 125:
            return 1
        if len(self.__raw) <= 0xFFFF:
            return 2
        assert len(self.__raw) <= 0xFFFFFFFFFFFFFFFF
        return 8

    def __len__(self) -> int:
        return len(self.__raw)

    def mask(self, maskingKey: bytes):
        assert len(maskingKey) == 4
        masked: bytearray = bytearray(self.__raw)
        for i, byte in enumerate(self.__raw):
            masked[i] = byte ^ maskingKey[i % 4]
        self.__raw = bytes(masked)


class WSMessage(Serializable):
    isFin: bool
    # rsv: int - not used, we don't use any extension
    opcode: WSOpcode
    maskingKey: bytes | None
    payload: WSData

    def __init__(self):
        super().__init__()
        self.isFin = True
        # self.rsv = 0
        self.opcode = WSOpcode.TEXT_FRAME
        self.maskingKey = None
        self.payload = WSData()

    def read(self, buff: ByteBuffer):
        # https://en.wikipedia.org/wiki/WebSocket#Base_Framing_Protocol
        byte: int = buff.readByte()
        self.isFin = bool(byte & 0b10000000)
        self.opcode = WSOpcode(byte & 0x0F)
        byte: int = buff.readByte()
        isMasked = bool(byte & 0b10000000)
        payloadLength: int = byte & 0b01111111
        if payloadLength == 126:
            raise ValueError("Unknown endianness - big or little?")
            # payloadLength = int.from_bytes(buff.read(2), "big", signed=False)
        elif payloadLength == 127:
            raise ValueError("Unknown endianness - big or little?")
            # payloadLength = int.from_bytes(buff.read(8), "big", signed=False)
        self.maskingKey = buff.read(4) if isMasked else None
        self.payload = WSData(bytes(buff.read(payloadLength)))
        self.payload.isBinary = self.opcode != WSOpcode.TEXT_FRAME
        if isMasked:
            self.payload.mask(self.maskingKey)

    def write(self, buff: ByteBuffer):
        byte: int = 0
        if self.isFin:
            byte |= 0b10000000
        byte |= self.opcode.value
        buff.writeByte(byte)
        byte: int = 0
        if self.isMasked:
            byte |= 0b10000000
        payloadBytes = self.payload.lenBytes
        if payloadBytes == 1:
            byte |= len(self.payload)
        elif payloadBytes == 2:
            byte |= 126
        elif payloadBytes == 8:
            byte |= 127
        buff.writeByte(byte)
        if payloadBytes > 1:
            raise ValueError("Unknown endianness - big or little?")
            # buff.write(len(self.payload).to_bytes(payloadBytes, "big", signed=False))
        if self.isMasked:
            assert len(self.maskingKey) == 4
            buff.write(self.maskingKey)
        buff.write(self.payload.superSecretRawAccess)

    @property
    def isMasked(self) -> bool:
        return self.maskingKey is not None
