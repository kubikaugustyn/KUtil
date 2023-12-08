#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.protocol.HTTP import HTTPResponse, HTTPRequest, HTTPMethod

from kutil import HTTPConnection

conn: HTTPConnection


def printResponse(resp: HTTPResponse):
    assert resp.statusCode == 200
    # print(f"Got response {resp.statusCode} ({resp.statusPhrase})")
    # print("Headers:")
    # for name, value in resp.headers.items():
    #     print(f"    {name}: {value}")
    # print("Body:")
    # print(resp.body)
    conn.close()


# if __name__ == '__main__':
conn = HTTPConnection(("example.com", 80), printResponse)
req: HTTPRequest = HTTPRequest(HTTPMethod.GET, "http://www.example.com/")
conn.sendData(req)
