#  -*- coding: utf-8 -*-
"""
This is the crucial point of the connection. If you find any bugs that could lead to auth bypass,
create an issue on GitHub here: https://github.com/kubikaugustyn/KUtil/issues/new
"""
__author__ = "kubik.augustyn@post.cz"

from typing import Optional

from cryptography.x509 import DNSName, load_pem_x509_certificates
from cryptography.x509.verification import PolicyBuilder, Store, VerificationError
import certifi
from datetime import datetime

from kutil.protocol.TLS.ConnectionState import ConnectionState

_STORE: Optional[Store] = None


def getStore() -> Store:
    global _STORE
    if _STORE is not None:
        return _STORE
    with open(certifi.where(), "rb") as pemCerts:
        _STORE = Store(load_pem_x509_certificates(pemCerts.read()))
    return _STORE


# https://datatracker.ietf.org/doc/html/rfc5280
# https://cryptography.io/en/latest/x509/verification/
# This is the crucial point of the connection - is the certificate valid?
def verifyPeerCertificates(state: ConnectionState) -> tuple[int, Optional[Exception]]:
    """
    Verifies the provided certificate's validity.
    :param state: Connection state containing certificates to check
    :return: [error code + cause] or [-1 and None] if no error occurred
    """
    state.verifiedCertificateChain = None

    try:
        builder = PolicyBuilder().store(getStore())
        builder = builder.time(datetime.now())
        verifier = builder.build_server_verifier(DNSName(state.serverDomainName))
        chain = verifier.verify(state.rootCertificate, state.certificates)
    except VerificationError as e:
        return 42, e
    except Exception as e:
        # If any other exception occurs...
        return 80, e

    state.verifiedCertificateChain = chain

    return -1, None


__all__ = ["verifyPeerCertificates"]
