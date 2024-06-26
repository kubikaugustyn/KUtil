#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import Thread
from time import time

from kutil.protocol.HTTP import HTTPRequest, HTTPResponse, HTTPHeaders, HTTPThing
from kutil.protocol.WS import WSData
from kutil.protocol.SSE import SSEMessage
from kutil import HTTPServer, HTTPServerConnection, ProtocolConnection, readFile, ThreadWaiter

index_page = b"""<h1>HTTP server test</h1>
<a href="/test-ws">Test websocket (WS)</a><br>
<a href="/test-sse">Test server sent events (SSE)</a>"""
ws_test_page = readFile("websocket_server.html", "bytes")
sse_test_page = readFile("sse_server.html", "bytes")

sse_conns: list[HTTPServerConnection] = []
sse_thread_waiter: ThreadWaiter = ThreadWaiter()


def sseThread():
    print("SSE thread started")
    while True:
        sse_thread_waiter.wait(maxTime=.01)
        if len(sse_conns) == 0:
            continue

        # Send the time update message, letting the user know the current server time
        # Runs every ~10ms
        ev = SSEMessage(data=HTTPThing.enc(str(time())), eventName="update-time")
        for conn in sse_conns:
            if conn.closed:
                # print("SSE closed.")
                sse_conns.remove(conn)
                continue
            conn.sendData(ev)


def acceptWebSocket(conn: HTTPServerConnection, data: HTTPRequest) -> bool:
    return data.requestURI == "/ws"


def acceptSSE(conn: HTTPServerConnection, data: HTTPRequest) -> bool:
    return data.requestURI == "/sse"


def onData(conn: HTTPServerConnection, data: HTTPRequest | WSData | SSEMessage):
    # print(data)
    if conn.didUpgradeToWS:
        assert isinstance(data, WSData)
        msg: WSData = data
        # print("Got WS message:", msg.text)
        assert msg.text == "good"
        conn.close()
        return
    assert isinstance(data, HTTPRequest)
    req: HTTPRequest = data
    # print(f"{req.method.name} - {req.headers.get('Host', '')}{req.requestURI}")
    # print("Got data, closing...")
    # resp: HTTPResponse = HTTPResponse(200, "OK", HTTPHeaders(),
    #                                   HTTPThing.enc(f"<h1>Hello world at {req.requestURI}</h1>"))
    resp: HTTPResponse = HTTPResponse(200, "OK", HTTPHeaders(), index_page)
    if req.requestURI == "/ws":
        resp = HTTPResponse(405, "Method not Allowed", HTTPHeaders(), b'This is for websocket.')
    elif req.requestURI == "/sse":
        resp = HTTPResponse(405, "Method not Allowed", HTTPHeaders(), b'This is for SSE.')
    elif req.requestURI == "/test-ws":
        resp.body = ws_test_page
    elif req.requestURI == "/test-sse":
        resp.body = sse_test_page
    conn.sendData(resp)
    conn.close()
    # print("Close connection.")


def onWebsocketEstablishment(conn: HTTPServerConnection):
    assert conn.didUpgradeToWS
    conn.sendData(WSData("test"))
    conn.sendData(WSData("you"))
    conn.sendData(WSData("sussy"))
    conn.sendData(WSData("baka"))


def onSSEEstablishment(conn: HTTPServerConnection):
    assert conn.didUpgradeToSSE
    # print("SSE open")
    sse_conns.append(conn)
    sse_thread_waiter.reset()


def onConnection(conn: ProtocolConnection):
    # print(conn)
    if not isinstance(conn, HTTPServerConnection):
        raise ValueError
    sus: HTTPServerConnection = conn
    sus.onWebsocketEstablishment = onWebsocketEstablishment
    sus.onSSEEstablishment = onSSEEstablishment
    # print(f"On connection...")
    return onData


if __name__ == '__main__':
    Thread(target=sseThread).start()

    addr = ("localhost", 666)
    server: HTTPServer = HTTPServer(addr, onConnection)
    server.acceptWebsocket(acceptWebSocket)
    server.acceptServerSentEvents(acceptSSE)
    print(f"Server open on http://{addr[0]}:{addr[1]}")
    server.listen()
    # Go to http://localhost:666/ and see the results
