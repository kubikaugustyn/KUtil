#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Optional

from kutil.protocol.TLS import messages

from kutil.protocol.TLS.ConnectionState import ConnectionState, ConnectionStateType

from kutil import DataBuffer, ByteBuffer, MemoryByteBuffer
from kutil.protocol.TLS.RawTLSRecord import RawTLSRecord, TLSRecordType
from kutil.protocol.TLS.AlertCause import AlertFatality, FATAL, WARNING_FATAL, WARNING, alertErrors
from kutil.protocol.TLS.messages import Message, MessageType


# https://en.wikipedia.org/wiki/Transport_Layer_Security#Handshake_protocol
class HandshakeRecord(RawTLSRecord):
    messages: list[Message]

    def __init__(self, connectionState: ConnectionState,
                 messages: Optional[list[Message]] = None) -> None:
        self.messages = messages if messages is not None else []
        super().__init__(TLSRecordType.Handshake, connectionState)

    def write(self, buff: ByteBuffer):
        payloadBuff: DataBuffer = DataBuffer()

        for msg in self.messages:
            msg.write(payloadBuff.buff)

        self.payload = payloadBuff.buff.export()
        super().write(buff)

    def read(self, buff: ByteBuffer):
        super().read(buff)
        self.messages = []
        payloadBuff: DataBuffer = DataBuffer(ByteBuffer(self.payload))

        while payloadBuff.buff.has(4):
            msg = messages.parseMessage(payloadBuff, self.connectionState)
            self.messages.append(msg)


# https://en.wikipedia.org/wiki/Transport_Layer_Security#Alert_protocol
class AlertRecord(RawTLSRecord):
    _level: int
    _code: int

    def __init__(self, connectionState: ConnectionState, code: int = -1, level: int = -1) -> None:
        self.code = code
        self.level = level
        super().__init__(TLSRecordType.Alert, connectionState)

    def write(self, buff: ByteBuffer):
        payloadBuff: ByteBuffer = MemoryByteBuffer()

        if self.level == -1 or self.code == -1:
            raise ValueError("Invalid level or code")
        payloadBuff.writeByte(self.level)
        payloadBuff.writeByte(self.code)

        self.payload = payloadBuff.export()
        super().write(buff)

    def read(self, buff: ByteBuffer):
        super().read(buff)

        assert len(self.payload) == 2

        # Set the code first to pass level validation
        self.code = self.payload[1]
        self.level = self.payload[0]

    @property
    def code(self) -> int:
        return self._code

    @code.setter
    def code(self, newCode: int) -> None:
        if newCode != -1 and newCode not in alertErrors:
            raise ValueError(f"Invalid error code {newCode}")
        self._code = newCode
        self.level = -1

    @property
    def isFatal(self) -> int:
        return self.level == 2

    @property
    def isWarning(self) -> int:
        return self.level == 1

    @property
    def level(self) -> int:
        return self._level

    @level.setter
    def level(self, newLevel: int) -> None:
        if newLevel == -1:
            self._level = -1
            return

        fatality: AlertFatality = alertErrors[self.code][1]
        if newLevel == 1:
            # Warning
            if fatality not in (WARNING, WARNING_FATAL):
                raise ValueError(f"Invalid warning fatality for '{alertErrors[self.code][0]}'")
        elif newLevel == 2:
            # Fatal
            if fatality not in (FATAL, WARNING_FATAL):
                raise ValueError(f"Invalid fatal fatality for '{alertErrors[self.code][0]}'")
        else:
            raise ValueError(f"Invalid level {newLevel}")
        self._level = newLevel


# https://en.wikipedia.org/wiki/Transport_Layer_Security#ChangeCipherSpec_protocol
class ChangeCipherSpecRecord(RawTLSRecord):
    _protocolType: int

    def __init__(self, connectionState: ConnectionState, protocolType: int = 1) -> None:
        self.protocolType = protocolType
        super().__init__(TLSRecordType.ChangeCipherSpec, connectionState)

    def write(self, buff: ByteBuffer):
        payloadBuff: ByteBuffer = MemoryByteBuffer()

        payloadBuff.writeByte(self.protocolType)

        self.payload = payloadBuff.export()
        super().write(buff)

    def read(self, buff: ByteBuffer):
        super().read(buff)

        assert len(self.payload) == 1

        self.protocolType = self.payload[0]

    @property
    def protocolType(self) -> int:
        return self._protocolType

    @protocolType.setter
    def protocolType(self, newProtocolType: int) -> None:
        if newProtocolType != 1:
            raise ValueError(f"Invalid protocol type: {newProtocolType}")
        self._protocolType = newProtocolType


# https://en.wikipedia.org/wiki/Transport_Layer_Security#Application_protocol
class ApplicationRecord(RawTLSRecord):
    def __init__(self, connectionState: ConnectionState, payload: Optional[bytes] = None) -> None:
        assert connectionState.state == ConnectionStateType.APPLICATION_DATA
        super().__init__(TLSRecordType.Application, connectionState, payload)
