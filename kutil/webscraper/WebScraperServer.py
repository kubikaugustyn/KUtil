#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod

from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from kutil.protocol.HTTP.HTTPResponse import HTTPResponse
from kutil.protocol.HTTP.HTTPRequest import HTTPRequest
from kutil.protocol.ProtocolConnection import ProtocolConnection

from kutil.protocol.HTTPServer import HTTPServer, HTTPServerConnection


class WebScraperServer:
    server: HTTPServer
    port: int
    host: str

    def __init__(self, port: int = 666, host: str = "localhost"):
        self.server = HTTPServer((host, port), self.onConnection)
        self.port = port
        self.host = host

    def listen(self):
        self.server.listen()

    def onConnection(self, conn: ProtocolConnection):
        # print(conn)
        if not isinstance(conn, HTTPServerConnection):
            raise ValueError
        castedConn: HTTPServerConnection = conn
        # print(f"On connection...")
        return lambda data: self.onData(castedConn, data)

    def onData(self, conn: HTTPServerConnection, req: HTTPRequest):
        try:
            resp = self.onDataInner(conn, req)
        except Exception as e:
            content = str(e)
            if not content:
                content = str(type(e).__name__)
            resp = HTTPResponse(500, "Internal server error", HTTPHeaders(), HTTPResponse.enc(content))
            resp.headers["Content-Type"] = "text/plain"
        # Don't close the socket if the client wants to request more data
        close = req.headers.get("Connection", "close") != "keep-alive"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        WebScraperServer.sendResponse(resp, conn, close)

    @abstractmethod
    def onDataInner(self, conn: HTTPServerConnection, req: HTTPRequest) -> HTTPResponse:
        return HTTPResponse(405, "Method not Allowed", HTTPHeaders(), b'This is for websocket.')

    @staticmethod
    def sendResponse(resp: HTTPResponse, conn: HTTPServerConnection, close: bool = True):
        conn.sendData(resp)
        if close:
            conn.close()

    @staticmethod
    def badRequest() -> HTTPResponse:
        headers: HTTPHeaders = HTTPHeaders()
        headers["Content-Type"] = "text/html"
        return HTTPResponse(400, "Bad request", headers, b'<h1>A bad request.</h1>')
