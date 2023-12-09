#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from kutil.protocol.HTTP import HTTPRequest, HTTPResponse, HTTPHeaders, HTTPThing
from kutil.protocol.WS import WSData
from kutil import HTTPServer, HTTPServerConnection, ProtocolConnection

with open("websocket_server.html", "rb") as f:
    ws_test_page: bytes = f.read()


def acceptWebSocket(conn: HTTPServerConnection, data: HTTPRequest) -> bool:
    return data.requestURI == "/ws"


def onData(conn: HTTPServerConnection, data: HTTPRequest | WSData):
    # print(data)
    if conn.didUpgradeToWS:
        assert isinstance(data, WSData)
        msg: WSData = data
        # print("Got WS message:", msg.text)
        assert msg.text == "good"
        conn.close()
        return
    assert isinstance(data, HTTPRequest)
    # req: HTTPRequest = data
    # print(f"{req.method.name} - {req.headers.get('Host', '')}{req.requestURI}")
    # print("Got data, closing...")
    # resp: HTTPResponse = HTTPResponse(200, "OK", HTTPHeaders(),
    #                                   HTTPThing.enc(f"<h1>Hello world at {req.requestURI}</h1>"))
    resp: HTTPResponse = HTTPResponse(200, "OK", HTTPHeaders(), ws_test_page)
    if data.requestURI == "/ws":
        resp = HTTPResponse(405, "Method not Allowed", HTTPHeaders(), b'This is for websocket.')
    conn.sendData(resp)
    conn.close()
    # print("Close connection.")


def onWebsocketEstablishment(conn: HTTPServerConnection):
    assert conn.didUpgradeToWS
    conn.sendData(WSData("test"))
    conn.sendData(WSData("you"))
    conn.sendData(WSData("sussy"))
    conn.sendData(WSData("baka"))


def onConnection(conn: ProtocolConnection):
    # print(conn)
    if not isinstance(conn, HTTPServerConnection):
        raise ValueError
    sus: HTTPServerConnection = conn
    sus.onWebsocketEstablishment = onWebsocketEstablishment
    # print(f"On connection...")
    return lambda data: onData(sus, data)

# server: HTTPServer = HTTPServer(("localhost", 666), onConnection)
# server.acceptWebsocket(acceptWebSocket)
# server.listen()
# Go to http://localhost:666/ and see the results
# Works!!!
