#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import IntEnum, unique


def _int(a: int, b: int) -> int:
    return (a << 8) + b


# https://datatracker.ietf.org/doc/html/rfc8446#appendix-B.4
@unique
class CipherSuite(IntEnum):
    TLS_AES_128_GCM_SHA256 = _int(0x13, 0x01)
    TLS_AES_256_GCM_SHA384 = _int(0x13, 0x02)
    TLS_CHACHA20_POLY1305_SHA256 = _int(0x13, 0x03)
    TLS_AES_128_CCM_SHA256 = _int(0x13, 0x04)
    TLS_AES_128_CCM_8_SHA256 = _int(0x13, 0x05)

    # Stolen from the https://williamlieurance.com/tls-handshake-parser/ example handshake
    TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 = _int(0xc0, 0x2c)
    TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384 = _int(0xc0, 0x30)
    TLS_ECDHE_ECDSA_WITH_CHACHA20_POLY1305_SHA256 = _int(0xcc, 0xa9)
    # Selected by the https://google.com/ server v
    TLS_ECDHE_RSA_WITH_CHACHA20_POLY1305_SHA256 = _int(0xcc, 0xa8)
    TLS_ECDHE_ECDSA_WITH_AES_256_CCM = _int(0xc0, 0xad)
    TLS_ECDHE_ECDSA_WITH_AES_128_GCM_SHA256 = _int(0xc0, 0x2b)
    TLS_ECDHE_RSA_WITH_AES_128_GCM_SHA256 = _int(0xc0, 0x2f)
    TLS_ECDHE_ECDSA_WITH_AES_128_CCM = _int(0xc0, 0xac)
    TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA256 = _int(0xc0, 0x23)
    TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA256 = _int(0xc0, 0x27)
    TLS_ECDHE_ECDSA_WITH_AES_256_CBC_SHA = _int(0xc0, 0x0a)
    TLS_ECDHE_RSA_WITH_AES_256_CBC_SHA = _int(0xc0, 0x14)
    TLS_ECDHE_ECDSA_WITH_AES_128_CBC_SHA = _int(0xc0, 0x09)
    TLS_ECDHE_RSA_WITH_AES_128_CBC_SHA = _int(0xc0, 0x13)
    TLS_RSA_WITH_AES_256_GCM_SHA384 = _int(0x00, 0x9d)
    TLS_RSA_WITH_AES_256_CCM = _int(0xc0, 0x9d)
    TLS_RSA_WITH_AES_128_GCM_SHA256 = _int(0x00, 0x9c)
    TLS_RSA_WITH_AES_128_CCM = _int(0xc0, 0x9c)
    TLS_RSA_WITH_AES_256_CBC_SHA256 = _int(0x00, 0x3d)
    TLS_RSA_WITH_AES_128_CBC_SHA256 = _int(0x00, 0x3c)
    TLS_RSA_WITH_AES_256_CBC_SHA = _int(0x00, 0x35)
    TLS_RSA_WITH_AES_128_CBC_SHA = _int(0x00, 0x2f)
    TLS_DHE_RSA_WITH_AES_256_GCM_SHA384 = _int(0x00, 0x9f)
    TLS_DHE_RSA_WITH_CHACHA20_POLY1305_SHA256 = _int(0xcc, 0xaa)
    TLS_DHE_RSA_WITH_AES_256_CCM = _int(0xc0, 0x9f)
    TLS_DHE_RSA_WITH_AES_128_GCM_SHA256 = _int(0x00, 0x9e)
    TLS_DHE_RSA_WITH_AES_128_CCM = _int(0xc0, 0x9e)
    TLS_DHE_RSA_WITH_AES_256_CBC_SHA256 = _int(0x00, 0x6b)
    TLS_DHE_RSA_WITH_AES_128_CBC_SHA256 = _int(0x00, 0x67)
    TLS_DHE_RSA_WITH_AES_256_CBC_SHA = _int(0x00, 0x39)
    TLS_DHE_RSA_WITH_AES_128_CBC_SHA = _int(0x00, 0x33)
