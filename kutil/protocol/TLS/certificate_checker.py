#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.protocol.TLS.messages import CertificateMessage


def checkCertificate(cert: CertificateMessage) -> int:
    """
    Checks if the provided certificate is valid
    :param cert: certificate to check
    :return: error code or -1 if no error occurred
    """
    return -1
