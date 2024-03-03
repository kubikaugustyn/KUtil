#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.protocol.HTTP import HTTPRequest, HTTPResponse, HTTPMethod, HTTPHeaders
from kutil.protocol import HTTPConnection, ProtocolConnection


def onData(conn: ProtocolConnection, resp: HTTPResponse):
    print(resp)
    print()
    print(resp.text)
    print()
    for key, val in resp.headers.items():
        print(f"{key}: {val}")

    conn.close()


def main():
    conn = HTTPConnection(("google.com", 80), onData)

    headers = HTTPHeaders()
    headers["Accept"] = "text/html"
    req = HTTPRequest(HTTPMethod.GET, "http://google.com/", headers)

    conn.sendData(req)


if __name__ == '__main__':
    main()
