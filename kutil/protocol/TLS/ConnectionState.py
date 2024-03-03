#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from cryptography.hazmat.primitives.asymmetric import dh
from enum import Enum, unique, IntEnum
from typing import Self

from kutil.protocol.TLS.tls_cryptography import generateDHEKeys

from kutil.protocol.TLS.extensions import NamedGroup, KeyShareEntry, DHE_GROUPS

from kutil.protocol.TLS.CipherSuite import CipherSuite


@unique
class TLSVersion(Enum):
    SSL_3_0 = (3, 0)
    TLS_1_0 = (3, 1)
    TLS_1_1 = (3, 2)
    TLS_1_2 = (3, 3)
    TLS_1_3 = (3, 4)

    def __lt__(self, other: Self):
        return self.value[0] < other.value[0] or self.value[1] < other.value[1]

    def __gt__(self, other: Self):
        return self.value[0] > other.value[0] or self.value[1] > other.value[1]

    def __eq__(self, other: Self):
        return self.value[0] == other.value[0] or self.value[1] == other.value[1]

    def __ge__(self, other: Self):
        return self > other or self == other

    def __le__(self, other: Self):
        return self < other or self == other


# Type of the MAC + its size
@unique
class MACType(IntEnum):
    HMAC_SHA256 = 32
    HMAC_SHA1 = 20
    HMAC_MD5 = 16


@unique
class ConnectionStateType(Enum):
    # TODO Figure out the real states
    INIT = "INIT"
    CLIENT_HELLO_SENT = "CLIENT_HELLO_SENT"
    SERVER_HELLO_RECEIVED = "SERVER_HELLO_RECEIVED"
    SERVER_HELLO_DONE = "SERVER_HELLO_DONE"
    KEY_SENT = "KEY_SENT"
    CHANGE_CIPHER_SENT = "CHANGE_CIPHER_SENT"
    FINISHED_SENT = "FINISHED_SENT"
    CHANGE_CIPHER_RECEIVED = "CHANGE_CIPHER_RECEIVED"
    APPLICATION_DATA = "APPLICATION_DATA"


class ConnectionState:
    state: ConnectionStateType
    mac: MACType | None
    _version: TLSVersion | None
    supportedCipherSuites: list[CipherSuite] = [
        CipherSuite.TLS_AES_128_GCM_SHA256,
        CipherSuite.TLS_AES_256_GCM_SHA384,
        CipherSuite.TLS_CHACHA20_POLY1305_SHA256,
        CipherSuite.TLS_AES_128_CCM_SHA256,
        CipherSuite.TLS_AES_128_CCM_8_SHA256
    ]
    supportedGroups: list[NamedGroup] = [
        # TODO Order and implement them all properly
        NamedGroup.ffdhe8192,
        NamedGroup.ffdhe4096,
        NamedGroup.ffdhe2048
    ]
    clientSharedKeys: list[KeyShareEntry]
    _privateKeys: dict[NamedGroup, dh.DHPrivateKey]

    def __init__(self):
        self.state = ConnectionStateType.INIT
        self.mac = None
        self._version = None
        self._privateKeys = {}
        self.clientSharedKeys = self.generateClientSharedKeys()

    def generateClientSharedKeys(self) -> list[KeyShareEntry]:
        print("Gen keys")
        keys = []
        self._privateKeys = {}

        for group in self.supportedGroups:
            if group in DHE_GROUPS:
                print("S")
                public_key, private_key = generateDHEKeys(group)
                print("E")
                self._privateKeys[group] = private_key
                keys.append(KeyShareEntry(group, public_key))
            else:
                raise NotImplementedError(f"Unknown group {group}")
        print("Gotcha")
        return keys

    @property
    def allowMAC(self) -> bool:
        if self.state != ConnectionStateType.APPLICATION_DATA:
            return False
        return self.mac is not None

    @property
    def sizeMAC(self) -> int:
        assert self.allowMAC
        return self.mac.value

    @property
    def usesBlockCipher(self) -> bool:
        return False  # TODO Integrate with the cipher currently stored

    @property
    def allowPadding(self) -> bool:
        return self.state == ConnectionStateType.APPLICATION_DATA and self.usesBlockCipher

    @property
    def version(self) -> TLSVersion:
        return self._version or TLSVersion.TLS_1_3

    @version.setter
    def version(self, newVersion: TLSVersion) -> None:
        from kutil.protocol.TLS.AlertCause import AlertCause

        if self._version is not None:
            if self._version != newVersion:
                raise AlertCause(47)
            return
        self._version = newVersion if newVersion < self.version else self.version
