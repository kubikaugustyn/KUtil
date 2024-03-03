#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import os
import sys
from enum import IntEnum, unique

from kutil.protocol.TLS.extensions import Extension

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
        self.messageType = MessageType(self.readType(dBuff))
        length = dBuff.readUIntN(3)
        self.payload = buff.read(length)

    def write(self, buff: ByteBuffer):
        dBuff = DataBuffer(buff)
        dBuff.writeUInt8(self.messageType.value)
        length = len(self.payload)
        dBuff.writeUIntN(length, 3)
        buff.write(self.payload)


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
