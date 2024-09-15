#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from abc import abstractmethod, ABC

from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from kutil.protocol.HTTP.HTTPResponse import HTTPResponse
from kutil.protocol.HTTP.HTTPRequest import HTTPRequest
from kutil.protocol.ProtocolConnection import ProtocolConnection

from kutil.protocol.HTTPServer import HTTPServer, HTTPServerConnection


class WebScraperServer(ABC):
    server: HTTPServer | None
    port: int
    host: str

    def __init__(self, port: int = 666, host: str = "localhost"):
        self.server = None
        self.port = port
        self.host = host

    def listen(self):
        self.server = HTTPServer((self.host, self.port), self.onConnection)
        self.server.listen()

    def onConnection(self, conn: ProtocolConnection):
        # print(conn)
        if not isinstance(conn, HTTPServerConnection):
            raise ValueError
        # print(f"On connection...")
        return self.onData

    def onData(self, conn: HTTPServerConnection, req: HTTPRequest):
        try:
            resp = self.onDataInner(conn, req)
            assert isinstance(resp, HTTPResponse)
        except Exception as e:
            content = str(e)
            if not content:
                content = str(type(e).__name__)
            resp = HTTPResponse(500, "Internal server error", HTTPHeaders(),
                                HTTPResponse.enc(content))
            resp.headers["Content-Type"] = "text/plain"
        # Don't close the socket if the client wants to request more data
        close = req.headers.get("Connection", "close") != "keep-alive"
        resp.headers["Access-Control-Allow-Origin"] = "*"
        WebScraperServer.sendResponse(resp, conn, close)

    @abstractmethod
    def onDataInner(self, conn: HTTPServerConnection, req: HTTPRequest) -> HTTPResponse:
        headers = HTTPHeaders()
        headers["Content-Type"] = "text/html"
        return HTTPResponse(200, "OK", headers, b'WebScraperServer - rewrite the '
                                                b'onDataInner method to handle incoming requests')

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

    @staticmethod
    def badMethod() -> HTTPResponse:
        headers: HTTPHeaders = HTTPHeaders()
        headers["Content-Type"] = "text/html"
        return HTTPResponse(405, "Method not allowed", headers,
                            b'<h1>The requested method is not allowed.</h1>')

    @staticmethod
    def internalError() -> HTTPResponse:
        headers: HTTPHeaders = HTTPHeaders()
        headers["Content-Type"] = "text/html"
        return HTTPResponse(500, "Internal server error", headers,
                            b'<h1>An internal server error has occured.</h1>')
