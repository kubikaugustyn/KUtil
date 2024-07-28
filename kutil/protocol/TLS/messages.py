#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import os
import sys
from enum import IntEnum, unique
from typing import Optional

from kutil.protocol.TLS.extensions import Extension, readExtension, readExtensions, writeExtensions, \
    NamedGroup

from kutil.protocol.TLS.CipherSuite import CipherSuite, CERTIFICATE_SUITES, SRP_ALL_SUITES, \
    DH_ALL_SUITES, ECDH_ALL_SUITES

from kutil.buffer.DataBuffer import DataBuffer

from kutil import ByteBuffer, MemoryByteBuffer
from kutil.buffer.Serializable import Serializable

from kutil.protocol.TLS.ConnectionState import TLSVersion, ConnectionState
from kutil.protocol.TLS.tls_cryptography import AnyPublicKey, parsePublicKey, Certificate, \
    parseX509Certificate


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

    def __init__(self, messageType: Optional[MessageType] = None, payload: Optional[bytes] = None):
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
        self.payload = bytes(buff.read(length))

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

    def __init__(self, protocolVersion: TLSVersion, random: Optional[bytes] = None,
                 sessionID: Optional[bytes] = None,
                 cipherSuites: Optional[list[CipherSuite]] = None,
                 compressionMethods: Optional[bytes] = None,
                 extensions: Optional[list[Extension]] = None):
        self.protocolVersion = protocolVersion
        self.random = random if random is not None else os.urandom(32)
        self.sessionID = sessionID if sessionID is not None else b''
        self.cipherSuites = cipherSuites if cipherSuites is not None else []
        self.compressionMethods = compressionMethods if \
            compressionMethods is not None else b''
        self.extensions = extensions if extensions is not None else []

        super().__init__(MessageType.ClientHello, b'')

    def write(self, buff: ByteBuffer):
        b = MemoryByteBuffer()
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
        writeExtensions(b, 8, self.extensions)

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

    def __init__(self, protocolVersion: Optional[TLSVersion] = None, random: Optional[bytes] = None,
                 sessionIDEcho: Optional[bytes] = None, cipherSuite: Optional[CipherSuite] = None,
                 compressionMethod: Optional[int] = None,
                 extensions: Optional[list[Extension]] = None):
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
        self.random = bytes(b.read(32))
        sessionIDEchoLength = dBuff.readUInt8()
        assert 0 <= sessionIDEchoLength <= 32
        self.sessionIDEcho = bytes(b.read(sessionIDEchoLength))
        self.cipherSuite = CipherSuite(dBuff.readUInt16())
        self.compressionMethod = b.readByte()
        assert self.compressionMethod == 0

        self.extensions = []
        if not b.has(1):
            # Apparently when there is no length field for the extensions it means 0?
            # TOD0 Figure it out!
            return

        self.extensions = readExtensions(b, 6)


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.4.2
@unique
class CertificateType(IntEnum):
    X509 = 0
    RawPublicKey = 2


class CertificateMessage(Message):
    certRequestCtx: bytes  # certificate_request_context
    certificates: list[Certificate | AnyPublicKey]

    def __init__(self, certRequestCtx: Optional[bytes] = None,
                 certificates: Optional[list[Certificate | AnyPublicKey]] = None):
        self.certRequestCtx = certRequestCtx or b''
        self.certificates = certificates or []
        super().__init__(MessageType.Certificate, b'')

    def read(self, buff: ByteBuffer):
        super().read(buff)
        b = ByteBuffer(self.payload)
        dBuff = DataBuffer(b)

        # I double-checked the RFC, but still:
        # https://datatracker.ietf.org/doc/html/rfc8446#section-4.4.2
        # 1) The certificate_request_context is not present
        # 2) The cert_data size is uint16, not uint24
        # (according to google.com server response)
        # TODO Find out why is that

        self.certRequestCtx = b''  # bytes(b.read(dBuff.readUInt8()))
        certificatesLength = dBuff.readUIntN(3)
        self.certificates = []

        certificatesBuff = ByteBuffer(b.read(certificatesLength))
        certificatesDBuff = DataBuffer(certificatesBuff)
        while certificatesBuff.has(1):
            certificateType = CertificateType(certificatesDBuff.readUInt8())
            rawLength = certificatesDBuff.readUInt16()  # certificatesDBuff.readUIntN(3)
            raw = bytes(certificatesBuff.read(rawLength))
            if certificateType is CertificateType.RawPublicKey:
                self.certificates.append(parsePublicKey(raw))
            elif certificateType is CertificateType.X509:
                self.certificates.append(parseX509Certificate(raw))
            else:
                raise NotImplementedError(f"Unknown certificate type {certificateType}")


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.4.4
class FinishedMessage(Message):
    macSize: int
    verifyData: bytes

    def __init__(self, macSize: int, verifyData: Optional[bytes] = None):
        self.macSize = macSize
        self.verifyData = verifyData if verifyData else b''
        super().__init__(MessageType.Finished, b'')

    def read(self, buff: ByteBuffer):
        super().read(buff)
        assert len(self.payload) == self.macSize
        self.verifyData = self.payload

    def write(self, buff: ByteBuffer):
        assert len(self.verifyData) == self.macSize
        self.payload = self.verifyData
        super().write(buff)


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.4.4
class ClientKeyExchangeMessage(Message):
    cipherSuite: CipherSuite
    version: TLSVersion

    srp_A: int
    dh_Yc: int
    ecdh_Yc: bytes
    encryptedPreMasterSecret: bytes

    def __init__(self, cipherSuite: CipherSuite, version: TLSVersion, srp_A: Optional[int] = None,
                 dh_Yc: Optional[int] = None, ecdh_Yc: Optional[bytes] = None,
                 encryptedPreMasterSecret: Optional[bytes] = None):
        self.cipherSuite = cipherSuite
        self.version = version

        self.srp_A = srp_A or 0
        self.dh_Yc = dh_Yc or 0
        self.ecdh_Yc = ecdh_Yc or b''
        self.encryptedPreMasterSecret = encryptedPreMasterSecret or b''

        super().__init__(MessageType.ClientKeyExchange, b'')

    def read(self, buff: ByteBuffer):
        super().read(buff)
        b = ByteBuffer(self.payload)
        dBuff = DataBuffer(b)

        # https://github.com/tlsfuzzer/tlslite-ng/blob/6db0826e5ba19ae35e898bd9e6d8410662b4528c/tlslite/messages.py#L1730-L1745
        if self.cipherSuite in SRP_ALL_SUITES:
            self.srp_A = dBuff.readUIntN(dBuff.readUInt16())
        elif self.cipherSuite in CERTIFICATE_SUITES:
            if self.version in {TLSVersion.TLS_1_1, TLSVersion.TLS_1_2, TLSVersion.TLS_1_3}:
                self.encryptedPreMasterSecret = bytes(b.read(dBuff.readUInt16()))
            elif self.version is TLSVersion.TLS_1_0:
                self.encryptedPreMasterSecret = bytes(b.readRest())
            else:
                raise NotImplementedError(f"Unknown version: {self.version.name}")
        elif self.cipherSuite in DH_ALL_SUITES:
            self.dh_Yc = dBuff.readUIntN(dBuff.readUInt16())
        elif self.cipherSuite in ECDH_ALL_SUITES:
            self.ecdh_Yc = bytes(buff.read(dBuff.readUInt8()))
        else:
            raise NotImplementedError(f"Unknown cipher suite: {self.cipherSuite.name}")

    def write(self, buff: ByteBuffer):
        b = MemoryByteBuffer()
        dBuff = DataBuffer(b)

        # https://github.com/tlsfuzzer/tlslite-ng/blob/6db0826e5ba19ae35e898bd9e6d8410662b4528c/tlslite/messages.py#L1756-L1770
        if self.cipherSuite in SRP_ALL_SUITES:
            raise NotImplementedError("How do I encode UIntN's length?")
        elif self.cipherSuite is CERTIFICATE_SUITES:
            if self.version in {TLSVersion.TLS_1_1, TLSVersion.TLS_1_2, TLSVersion.TLS_1_3}:
                dBuff.writeUInt16(len(self.encryptedPreMasterSecret))
                b.write(self.encryptedPreMasterSecret)
            elif self.version is TLSVersion.TLS_1_0:
                b.write(self.encryptedPreMasterSecret)
            else:
                raise NotImplementedError(f"Unknown version: {self.version.name}")
        elif self.cipherSuite in DH_ALL_SUITES:
            raise NotImplementedError("How do I encode UIntN's length?")
        elif self.cipherSuite in ECDH_ALL_SUITES:
            dBuff.writeUInt8(len(self.ecdh_Yc))
            b.write(self.ecdh_Yc)
        else:
            raise NotImplementedError(f"Unknown cipher suite: {self.cipherSuite.name}")

        self.payload = b.export()
        super().write(buff)


def parseMessage(buff: DataBuffer, state: ConnectionState) -> Message:
    msgType: MessageType = Message.readType(buff, rollback=True)

    if msgType == MessageType.ClientHello:
        msg = ClientHelloMessage(state.version)
    elif msgType == MessageType.ServerHello:
        msg = ServerHelloMessage(state.version)
    elif msgType == MessageType.Certificate:
        msg = CertificateMessage()
    elif msgType == MessageType.Finished:
        msg = FinishedMessage(state.sizeMAC)
    else:
        msg: Message = Message()
    msg.read(buff.buff)
    return msg
