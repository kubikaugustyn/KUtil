#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import os
import sys
from enum import IntEnum, unique

from kutil.protocol.TLS.extensions import Extension, readExtension

from kutil.protocol.TLS.CipherSuite import CipherSuite

from kutil.buffer.DataBuffer import DataBuffer

from kutil import ByteBuffer
from kutil.buffer.Serializable import Serializable

from kutil.protocol.TLS.ConnectionState import TLSVersion


# https://datatracker.ietf.org/doc/html/rfc8446#appendix-B.3
@unique
class MessageType(IntEnum):
    HelloRequest = 0
    ClientHello = 1
    ServerHello = 2
    NewSessionTicket = 4
    EncryptedExtensions = 8  # (TLS 1.3 only)
    Certificate = 11
    ServerKeyExchange = 12
    CertificateRequest = 13
    ServerHelloDone = 14
    CertificateVerify = 15
    ClientKeyExchange = 16
    Finished = 20


class Message(Serializable):
    messageType: MessageType
    payload: bytes

    def __init__(self, messageType: MessageType | None = None, payload: bytes | None = None):
        self.messageType = messageType
        self.payload = payload

    @staticmethod
    def readType(dBuff: DataBuffer, rollback: bool = False) -> MessageType:
        msgType: MessageType = MessageType(dBuff.readUInt8())
        if rollback:
            dBuff.buff.back(1)
        return msgType

    def read(self, buff: ByteBuffer):
        dBuff = DataBuffer(buff)
        self.messageType = MessageType(self.readType(dBuff, rollback=False))
        length = dBuff.readUIntN(3)
        self.payload = buff.read(length)

    def write(self, buff: ByteBuffer):
        dBuff = DataBuffer(buff)
        dBuff.writeUInt8(self.messageType.value)
        length = len(self.payload)
        dBuff.writeUIntN(length, 3)
        buff.write(self.payload)

    def __repr__(self):
        if self.__class__ is not Message:
            return super().__repr__()
        return f"<kutil.protocol.TLS.messages.Message of type {self.messageType.name} object at {hex(id(self))}>"


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.1.2
class ClientHelloMessage(Message):
    protocolVersion: TLSVersion
    random: bytes
    sessionID: bytes
    cipherSuites: list[CipherSuite]
    compressionMethods: bytes
    extensions: list[Extension]

    def __init__(self, protocolVersion: TLSVersion, random: bytes | None = None,
                 sessionID: bytes | None = None, cipherSuites: list[CipherSuite] | None = None,
                 compressionMethods: bytes | None = None,
                 extensions: list[Extension] | None = None):
        self.protocolVersion = protocolVersion
        self.random = random if random is not None else os.urandom(32)
        self.sessionID = sessionID if sessionID is not None else b''
        self.cipherSuites = cipherSuites if cipherSuites is not None else []
        self.compressionMethods = compressionMethods if \
            compressionMethods is not None else b''
        self.extensions = extensions if extensions is not None else []

        super().__init__(MessageType.ClientHello, b'')

    def write(self, buff: ByteBuffer):
        b = ByteBuffer()
        dBuff = DataBuffer(b)
        b.writeByte(self.protocolVersion.value[0]).writeByte(self.protocolVersion.value[1])
        assert len(self.random) == 32
        b.write(self.random)
        assert 0 <= len(self.sessionID) <= 32
        dBuff.writeUInt8(len(self.sessionID))
        b.write(self.sessionID)
        assert 1 <= len(self.cipherSuites) <= pow(2, 15) - 1
        dBuff.writeUInt16(len(self.cipherSuites) * 2)
        for suite in self.cipherSuites:
            dBuff.writeUInt16(suite.value)
        assert 1 <= len(self.compressionMethods) <= 255
        dBuff.writeUInt8(len(self.compressionMethods))
        b.write(self.compressionMethods)

        extensionBuff = ByteBuffer()
        for extension in self.extensions:
            extension.write(extensionBuff)
        assert 8 <= len(extensionBuff.export()) <= pow(2, 16) - 1
        dBuff.writeUInt16(len(extensionBuff.export()))
        b.write(extensionBuff.export())

        self.payload = b.export()
        super().write(buff)


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.1.3
class ServerHelloMessage(Message):
    protocolVersion: TLSVersion
    random: bytes
    sessionIDEcho: bytes
    cipherSuite: CipherSuite
    compressionMethod: int
    extensions: list[Extension]

    def __init__(self, protocolVersion: TLSVersion | None = None, random: bytes | None = None,
                 sessionIDEcho: bytes | None = None, cipherSuite: CipherSuite | None = None,
                 compressionMethod: int | None = None, extensions: list[Extension] | None = None):
        self.protocolVersion = protocolVersion
        self.random = random if random is not None else os.urandom(32)
        self.sessionIDEcho = sessionIDEcho if sessionIDEcho is not None else b''
        self.cipherSuite = cipherSuite if cipherSuite is not None else None
        self.compressionMethod = compressionMethod if compressionMethod is not None else None
        self.extensions = extensions if extensions is not None else []

        super().__init__(MessageType.ServerHello, b'')

    def read(self, buff: ByteBuffer):
        super().read(buff)
        b = ByteBuffer(self.payload)
        dBuff = DataBuffer(b)

        self.protocolVersion = TLSVersion((b.readByte(), b.readByte()))
        self.random = b.read(32)
        sessionIDEchoLength = dBuff.readUInt8()
        assert 0 <= sessionIDEchoLength <= 32
        self.sessionIDEcho = b.read(sessionIDEchoLength)
        self.cipherSuite = CipherSuite(dBuff.readUInt16())
        self.compressionMethod = b.readByte()
        assert self.compressionMethod == 0

        self.extensions = []
        if not b.has(1):
            # Apparently when there is no length field for the extensions it means 0?
            # TOD0 Figure it out!
            return

        extensionLength = dBuff.readUInt16()
        assert 6 <= extensionLength <= pow(2, 16) - 1
        extensionBuff = ByteBuffer(b.read(extensionLength))
        while extensionBuff.has(1):
            extension = readExtension(extensionBuff)
            self.extensions.append(extension)


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.4.2
class CertificateMessage(Message):
    def __init__(self):
        super().__init__(MessageType.Certificate, b'')

    def read(self, buff: ByteBuffer):
        super().read(buff)
        b = ByteBuffer(self.payload)
        dBuff = DataBuffer(b)

        pass  # TODO Parse the certificate


def parseMessage(buff: DataBuffer, version: TLSVersion) -> Message:
    msgType: MessageType = Message.readType(buff, rollback=True)

    if msgType == MessageType.ClientHello:
        msg = ClientHelloMessage(version)
    elif msgType == MessageType.ServerHello:
        msg = ServerHelloMessage(version)
    elif msgType == MessageType.Certificate:
        msg = CertificateMessage()
    else:
        msg: Message = Message()
    msg.read(buff.buff)
    return msg
