#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil import TCPConnection

conn: TCPConnection


def printer(data: bytes):
    assert len(data)
    # print(data.decode("utf-8"))
    conn.close()


# if __name__ == '__main__':
conn = TCPConnection(("example.com", 80), printer)
conn.sendData(b'GET http://example.com/ HTTP/1.1\r\n\r\n')
