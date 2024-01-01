#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil.protocol.HTTP import HTTPResponse, HTTPRequest, HTTPMethod
from kutil import HTTPConnection


class TestHTTPConnection(TestCase):
    conn: HTTPConnection

    def setUp(self):
        self.conn = HTTPConnection(("example.com", 80), self.__printResponse)

    def tearDown(self):
        self.conn.close()

    def __printResponse(self, resp: HTTPResponse):
        self.assertEqual(resp.statusCode, 200)
        # print(f"Got response {resp.statusCode} ({resp.statusPhrase})")
        # print("Headers:")
        # for name, value in resp.headers.items():
        #     print(f"    {name}: {value}")
        # print("Body:")
        # print(resp.body)

    def test_http_connection(self):
        req: HTTPRequest = HTTPRequest(HTTPMethod.GET, "http://www.example.com/")
        self.conn.sendData(req)
