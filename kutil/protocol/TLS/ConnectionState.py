#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

import os

import urllib3.util
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import dh
from enum import Enum, unique, IntEnum, auto
from typing import Self, Optional

from kutil.protocol.TLS.extensions import NamedGroup, KeyShareEntry
from kutil.protocol.TLS.CipherSuite import CipherSuite
from kutil.protocol.TLS.tls_cryptography import Certificate, generateKeypair


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


# Type of the exchanged key
@unique
class KeyExchangeAlgorithm(Enum):
    DHE_DSS = auto()
    DHE_RSA = auto()
    DH_ANON = auto()
    RSA = auto()
    DH_DSS = auto()
    DH_RSA = auto()


@unique
class ConnectionStateType(Enum):
    # TODO Figure out the real states
    INIT = auto()
    CLIENT_HELLO_SENT = auto()
    SERVER_HELLO_RECEIVED = auto()
    SERVER_HELLO_DONE = auto()
    KEY_SENT = auto()
    CHANGE_CIPHER_SENT = auto()
    FINISHED_SENT = auto()
    CHANGE_CIPHER_RECEIVED = auto()
    APPLICATION_DATA = auto()


class ConnectionState:
    state: ConnectionStateType
    mac: Optional[MACType]
    keyExchangeAlgorithm: Optional[KeyExchangeAlgorithm]
    rootCertificate: Optional[Certificate]
    certificates: list[Certificate]
    verifiedCertificateChain: Optional[list[Certificate]]
    _version: Optional[TLSVersion]
    supportedCipherSuites: list[CipherSuite] = list(CipherSuite)  # Well, lets lie to the server...
    supportedGroups: list[NamedGroup] = [
        # TODO Order and implement them all properly
        # Finite Field Groups(DHE)
        NamedGroup.ffdhe8192,
        NamedGroup.ffdhe6144,
        NamedGroup.ffdhe4096,
        NamedGroup.ffdhe3072,
        NamedGroup.ffdhe2048,
        # Elliptic Curve Groups(ECDHE)
        NamedGroup.secp256r1,
        NamedGroup.secp384r1,
        NamedGroup.secp521r1,
        NamedGroup.x25519,
        NamedGroup.x448
    ]
    clientSharedKeys: list[KeyShareEntry]
    _privateKeys: dict[NamedGroup, dh.DHPrivateKey]
    pendingCipher: Optional[CipherSuite]
    _selectedCipher: Optional[CipherSuite]
    sessionID: bytes
    serverDomainName: Optional[str]

    def __init__(self):
        self.state = ConnectionStateType.INIT
        self.mac = None
        self.keyExchangeAlgorithm = None
        self.rootCertificate = None
        self.certificates = []
        self.verifiedCertificateChain = None
        self._version = None
        self._privateKeys = {}
        self.pendingCipher = None
        self._selectedCipher = None
        self.sessionID = os.urandom(32)
        self.serverDomainName = None
        self.clientSharedKeys = self.generateClientSharedKeys()

    def generateClientSharedKeys(self) -> list[KeyShareEntry]:
        keys = []
        self._privateKeys = {}

        for group in self.supportedGroups:
            private_key, public_key = generateKeypair(group)

            self._privateKeys[group] = private_key

            if public_key is not None:
                # TODO Find the correct encoding and format
                public_bytes = public_key.public_bytes(serialization.Encoding.DER,
                                                       serialization.PublicFormat.SubjectPublicKeyInfo)
                keys.append(KeyShareEntry(group, public_bytes))
        return keys

    def switchToPendingCipher(self, unsafe_allow_no_cipher: bool = False):
        if not unsafe_allow_no_cipher and self.pendingCipher is None:
            raise ValueError("Cannot switch to the pending cipher because it's None")
        self._selectedCipher = self.pendingCipher

    def setServerDomainName(self, url: str) -> None:
        urlInfo = urllib3.util.parse_url(url)
        self.serverDomainName = urlInfo.host

    def addCertificates(self, certificates: list[Certificate]) -> None:
        for certificate in certificates:
            if self.rootCertificate is None:
                # TODO Set the root certificate correctly
                self.rootCertificate = certificate

            self.certificates.append(certificate)

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
