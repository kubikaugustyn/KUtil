#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.protocol.HTTP import HTTPRequest, HTTPResponse, HTTPMethod, HTTPHeaders
from kutil.protocol import HTTPSConnection, ProtocolConnection


def onEstablished(conn: ProtocolConnection):
    print("Connection established, send request...")
    headers = HTTPHeaders()
    headers["Accept"] = "text/html"
    req = HTTPRequest(HTTPMethod.GET, "https://google.com/", headers)

    conn.sendData(req)


def onData(conn: ProtocolConnection, resp: HTTPResponse):
    print(resp)
    print()
    print(resp.text)
    print()
    for key, val in resp.headers.items():
        print(f"{key}: {val}")

    conn.close()


def onClose(_: ProtocolConnection, cause: Exception | None):
    if cause is None:
        return
    raise cause


def main():
    conn = HTTPSConnection(("google.com", 443), onData, onEstablished)
    conn.onCloseListeners.append(onClose)
    print("Connection started")
    conn.close(NotImplemented("HTTPS in KUtil is not implemented (yet)"))


if __name__ == '__main__':
    main()
