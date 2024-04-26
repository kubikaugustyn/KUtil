#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import IntEnum, unique, Enum
from typing import Final, Self, Optional

from kutil.protocol.AbstractProtocol import NeedMoreDataError

from kutil.protocol.TLS.ConnectionState import ConnectionState, ConnectionStateType, TLSVersion

from kutil.protocol.TLS.AlertCause import AlertCause

from kutil.buffer.DataBuffer import DataBuffer
from kutil.buffer.ByteBuffer import ByteBuffer, OutOfBoundsUndoError, OutOfBoundsReadError

from kutil.buffer.Serializable import Serializable


# https://en.wikipedia.org/wiki/Transport_Layer_Security#TLS_record
@unique
class TLSRecordType(IntEnum):
    ChangeCipherSpec = 0x14
    Alert = 0x15
    Handshake = 0x16
    Application = 0x17
    Heartbeat = 0x18


class RawTLSRecordNeedMoreDataError(NeedMoreDataError):
    pass


class RawTLSRecord(Serializable):
    connectionState: ConnectionState
    contentType: TLSRecordType
    payload: Optional[bytes]
    mac: Optional[bytes]
    padding: Optional[bytes]

    def __init__(self, contentType: TLSRecordType, connectionState: ConnectionState,
                 payload: Optional[bytes] = None, mac: Optional[bytes] = None,
                 padding: Optional[bytes] = None) -> None:
        self.connectionState = connectionState
        self.contentType = contentType
        self.payload = payload
        self.mac = mac
        self.padding = padding

    def write(self, buff: ByteBuffer):
        assert self.payload is not None

        # Content type + version
        buff.writeByte(self.contentType.value)
        buff.writeByte(self.connectionState.version.value[0]).writeByte(
            self.connectionState.version.value[1])

        # Length
        length = len(self.payload)
        if self.mac is not None:
            length += len(self.mac)
        if self.padding is not None:
            length += len(self.padding)
        assert 0 <= length < (1 << 14)
        DataBuffer(buff).writeUInt16(length)

        # Payload etc.
        buff.write(self.payload)
        if self.mac is not None:
            buff.write(self.mac)
        if self.padding is not None:
            buff.write(self.padding)

    @staticmethod
    def readContentType(buff: ByteBuffer, resetAfterwards: bool = False) -> TLSRecordType:
        rec = TLSRecordType(buff.readByte())
        if resetAfterwards:
            buff.back(1)
        return rec

    def read(self, buff: ByteBuffer):
        try:
            # Content type + version
            contentType = self.readContentType(buff, False)
            assert contentType == self.contentType, \
                f"ContentType mismatch - {contentType.name} != {self.contentType.name}"
            try:
                cmpVersion = TLSVersion((buff.readByte(), buff.readByte()))
                if self.connectionState.version != cmpVersion:
                    raise ValueError
            except (TypeError, ValueError) as e:
                # Invalid version (doesn't exist or not set)
                raise AlertCause(70) from e

            # Length
            length = DataBuffer(buff).readUInt16()
            assert 0 <= length < (1 << 14)

            # Payload etc.
            # Explained in:
            # https://en.wikipedia.org/wiki/Transport_Layer_Security#Application_protocol
            dataBuff: ByteBuffer = ByteBuffer(buff.read(length))

            if self.connectionState.allowMAC:
                macSize = self.connectionState.sizeMAC
            else:
                macSize = 0
                self.mac = None

            if self.connectionState.allowPadding:
                paddingSize = dataBuff.readLastByte()
            else:
                paddingSize = 0
                self.padding = None

            self.payload = dataBuff.read(length - macSize - paddingSize)
            if macSize > 0:
                self.mac = dataBuff.read(macSize)
            if paddingSize > 0:
                self.padding = dataBuff.read(paddingSize)
        except (OutOfBoundsUndoError, OutOfBoundsReadError) as e:
            raise RawTLSRecordNeedMoreDataError from e
