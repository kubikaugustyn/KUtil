#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Final

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
    47: ("Illegal parameter", FATAL, ALL),
    50: ("Decode error", FATAL, TLS),
    70: ("Protocol version", FATAL, TLS),
    120: ("No application protocol", FATAL, TLS3),
    255: ("No application protocol", FATAL, TLS3)
}


class AlertCause(Exception):
    code: int

    def __init__(self, code: int):
        if code not in alertErrors:
            raise ValueError("Invalid error code")

        self.code = code
        super().__init__(alertErrors[code][0])


__all__ = ["AlertCause", "alertErrors", "WARNING", "WARNING_FATAL", "FATAL", "AlertFatality"]
