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
