#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import IntEnum, unique
from typing import Final, Optional

from kutil.buffer.DataBuffer import DataBuffer
from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer

from kutil.buffer.Serializable import Serializable


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.2
@unique
class ExtensionType(IntEnum):
    SERVER_NAME = 0
    MAX_FRAGMENT_LENGTH = 1
    STATUS_REQUEST = 5
    SUPPORTED_GROUPS = 10
    SIGNATURE_ALGORITHMS = 13
    USE_SRTP = 14
    HEARTBEAT = 15
    APPLICATION_LAYER_PROTOCOL_NEGOTIATION = 16
    SIGNED_CERTIFICATE_TIMESTAMP = 18
    CLIENT_CERTIFICATE_TYPE = 19
    SERVER_CERTIFICATE_TYPE = 20
    PADDING = 21
    PRE_SHARED_KEY = 41
    EARLY_DATA = 42
    SUPPORTED_VERSIONS = 43
    COOKIE = 44
    PSK_KEY_EXCHANGE_MODES = 45
    CERTIFICATE_AUTHORITIES = 47
    OID_FILTERS = 48
    POST_HANDSHAKE_AUTH = 49
    SIGNATURE_ALGORITHMS_CERT = 50
    KEY_SHARE = 51


class Extension(Serializable):
    extensionType: ExtensionType
    payload: bytes

    def __init__(self, extensionType: Optional[ExtensionType], payload: Optional[bytes] = None):
        self.extensionType = extensionType
        self.payload = payload if payload is not None else b''

    def write(self, buff: ByteBuffer):
        dBuff = DataBuffer(buff)
        dBuff.writeUInt16(self.extensionType.value)
        dBuff.writeUInt16(len(self.payload))
        buff.write(self.payload)

    @staticmethod
    def readType(dBuff: DataBuffer, rollback: bool) -> ExtensionType:
        extensionType = ExtensionType(dBuff.readUInt16())
        if rollback:
            dBuff.buff.back(2)
        return extensionType

    def read(self, buff: ByteBuffer):
        dBuff = DataBuffer(buff)
        self.extensionType = self.readType(dBuff, False)
        length = dBuff.readUInt16()
        self.payload = buff.read(length)


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.2.7
@unique
class NamedGroup(IntEnum):
    # Elliptic Curve Groups(ECDHE)
    secp256r1 = 0x0017
    secp384r1 = 0x0018
    secp521r1 = 0x0019
    x25519 = 0x001D
    x448 = 0x001E

    # Finite Field Groups(DHE)
    ffdhe2048 = 0x0100
    ffdhe3072 = 0x0101
    ffdhe4096 = 0x0102
    ffdhe6144 = 0x0103
    ffdhe8192 = 0x0104


DHE_GROUPS: Final[set[NamedGroup]] = {NamedGroup.ffdhe2048, NamedGroup.ffdhe3072,
                                      NamedGroup.ffdhe4096, NamedGroup.ffdhe6144,
                                      NamedGroup.ffdhe8192}

ECDHE_GROUPS: Final[set[NamedGroup]] = {NamedGroup.secp256r1, NamedGroup.secp384r1,
                                        NamedGroup.secp521r1}


class SupportedGroupsExtension(Extension):
    namedGroups: list[NamedGroup]

    def __init__(self, namedGroups: Optional[list[NamedGroup]] = None):
        self.namedGroups = namedGroups if namedGroups is not None else []
        super().__init__(ExtensionType.SUPPORTED_GROUPS)

    def write(self, buff: ByteBuffer):
        b = DataBuffer()
        assert len(self.namedGroups) > 0
        b.writeUInt16(len(self.namedGroups) * 2)
        for group in self.namedGroups:
            b.writeUInt16(group.value)

        self.payload = b.buff.export()
        super().write(buff)


# https://datatracker.ietf.org/doc/html/rfc8446#section-4.2.8
class KeyShareEntry(Serializable):
    group: NamedGroup
    keyExchange: bytes

    def __init__(self, group: NamedGroup, keyExchange: bytes):
        self.group = group
        self.keyExchange = keyExchange

    def write(self, buff: ByteBuffer):
        dBuff = DataBuffer(buff)
        dBuff.writeUInt16(self.group.value)
        assert 1 <= len(self.keyExchange) <= pow(2, 16) - 1
        dBuff.writeUInt16(len(self.keyExchange))
        buff.write(self.keyExchange)

    def read(self, buff: ByteBuffer):
        dBuff = DataBuffer(buff)
        self.group = NamedGroup(dBuff.readUInt16())
        length = dBuff.readUInt16()
        assert length > 0
        self.keyExchange = buff.read(length)


class KeyShareExtension(Extension):
    clientShares: list[KeyShareEntry]

    def __init__(self, clientShares: Optional[list[KeyShareEntry]] = None):
        self.clientShares = clientShares if clientShares is not None else []
        super().__init__(ExtensionType.KEY_SHARE)

    def write(self, buff: ByteBuffer):
        # TODO Don't use 2 buffers
        payloadBuff = MemoryByteBuffer()

        sharesBuff = MemoryByteBuffer()
        for share in self.clientShares:
            share.write(sharesBuff)
        DataBuffer(payloadBuff).writeUInt16(len(sharesBuff.export()))
        payloadBuff.write(sharesBuff.export())

        self.payload = payloadBuff.export()
        super().write(buff)


def readExtension(buff: ByteBuffer) -> Extension:
    """
    Given a buffer, returns an extension that is parsed from it, optimally special extension object.
    :param buff: source buffer
    :return: parsed extension
    """
    extensionType = Extension.readType(DataBuffer(buff), True)

    if extensionType is ExtensionType.KEY_SHARE:
        extension = KeyShareExtension()
    elif extensionType is ExtensionType.SUPPORTED_GROUPS:
        extension = SupportedGroupsExtension()
    else:
        extension = Extension(extensionType)
    extension.read(buff)
    return extension


def readExtensions(buff: ByteBuffer, minByteSize: int) -> list[Extension]:
    extensions = []
    extensionLength = DataBuffer(buff).readUInt16()
    assert minByteSize <= extensionLength <= pow(2, 16) - 1
    extensionBuff = ByteBuffer(buff.read(extensionLength))
    while extensionBuff.has(1):
        extension = readExtension(extensionBuff)
        extensions.append(extension)
    return extensions


def writeExtensions(buff: ByteBuffer, minByteSize: int, extensions: list[Extension]) -> None:
    extensionBuff = MemoryByteBuffer()
    for extension in extensions:
        extension.write(extensionBuff)
    assert minByteSize <= len(extensionBuff.export()) <= pow(2, 16) - 1
    DataBuffer(buff).writeUInt16(len(extensionBuff.export()))
    buff.write(extensionBuff.export())
