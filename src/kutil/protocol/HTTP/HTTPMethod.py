#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique


@unique
class HTTPMethod(Enum):
    OPTIONS = b"OPTIONS"
    GET = b"GET"
    HEAD = b"HEAD"
    POST = b"POST"
    PUT = b"PUT"
    DELETE = b"DELETE"
    TRACE = b"TRACE"
    CONNECT = b"CONNECT"
