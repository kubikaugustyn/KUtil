#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Final
from colorama import Fore, Style

from kutil.protocol.TLS.ConnectionState import TLSVersion

# Can be warning, can be fatal
type AlertFatality = tuple[bool, bool]
WARNING: Final[AlertFatality] = (True, False)
WARNING_FATAL: Final[AlertFatality] = (True, True)
FATAL: Final[AlertFatality] = (False, True)
# Description, fatality,min version
type AlertError = tuple[str, AlertFatality, TLSVersion]

ALL = sorted(list(TLSVersion))[0]
TLS = TLSVersion.TLS_1_0
TLS3 = TLSVersion.TLS_1_3
SSL3 = TLSVersion.SSL_3_0

# https://en.wikipedia.org/wiki/Transport_Layer_Security#Alert_protocol
# https://datatracker.ietf.org/doc/html/rfc8446#section-6.2
# https://datatracker.ietf.org/doc/html/rfc8446#appendix-B.2
alertErrors: Final[dict[int, AlertError]] = {
    # TODO Add all errors
    0: ("Close notify", WARNING_FATAL, ALL),
    10: ("Unexpected message", FATAL, ALL),
    20: ("Bad record MAC", FATAL, ALL),
    21: ("Decryption failed", FATAL, TLS),
    22: ("Record overflow", FATAL, TLS),
    30: ("Decompression failure", FATAL, ALL),
    40: ("Handshake failure", FATAL, ALL),
    41: ("No certificate", WARNING_FATAL, SSL3),
    42: ("Bad certificate", WARNING_FATAL, ALL),
    43: ("Unsupported certificate", WARNING_FATAL, ALL),
    44: ("Certificate revoked", WARNING_FATAL, ALL),
    45: ("Certificate expired", WARNING_FATAL, ALL),
    46: ("Certificate unknown", WARNING_FATAL, ALL),
    47: ("Illegal parameter", FATAL, ALL),
    50: ("Decode error", FATAL, TLS),
    70: ("Protocol version", FATAL, TLS),
    80: ("Internal error", FATAL, TLS),
    120: ("No application protocol", FATAL, TLS3),
    255: ("No application protocol", FATAL, TLS3)
}


class AlertCause(Exception):
    code: int

    def __init__(self, code: int):
        if code not in alertErrors:
            # raise ValueError("Invalid error code")
            print(f"{Fore.RED}{self.__class__.__module__}: "
                  f"Unknown error code: {code}{Style.RESET_ALL}")

        self.code = code
        if code in alertErrors:
            error = alertErrors[code][0]
        else:
            error = "(Unknown error)"
        super().__init__(error)


__all__ = ["AlertCause", "alertErrors", "WARNING", "WARNING_FATAL", "FATAL", "AlertFatality"]
