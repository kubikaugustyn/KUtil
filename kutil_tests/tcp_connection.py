#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from unittest import TestCase

from kutil import TCPConnection


class TestTCPConnection(TestCase):
    conn: TCPConnection

    def setUp(self):
        self.conn = TCPConnection(("example.com", 80), self.__printer)

    def tearDown(self):
        self.conn.close()

    def __printer(self, data: bytes):
        self.assertGreater(len(data), 0)
        # print(data.decode("utf-8"))

    def test_connection(self):
        self.conn.sendData(b'GET http://example.com/ HTTP/1.1\r\n\r\n')
