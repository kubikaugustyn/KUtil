#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Callable, Any, Self

from kutil.typing_help import neverCall

from kutil.protocol.AbstractProtocol import AbstractProtocol, NeedMoreDataError
from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.ProtocolConnection import ProtocolConnection
from kutil.protocol.ProtocolServer import ProtocolServer
from kutil.protocol.TCPConnection import TCPProtocol
from kutil.protocol.WS.WSMessage import WSMessage
from kutil.protocol.HTTP.HTTPRequest import HTTPRequest
from kutil.protocol.HTTP.HTTPResponse import HTTPResponse
from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from kutil.protocol.WSConnection import WSProtocol, WSConnection

type AcceptWSChecker = Callable[[HTTPServerConnection, HTTPRequest], bool]


class HTTPServerProtocol(AbstractProtocol):
    name = "HTTPServerProtocol"

    def unpackData(self, buff: ByteBuffer) -> HTTPRequest:
        req = HTTPRequest()
        try:
            req.read(buff)
        except Exception:
            raise NeedMoreDataError
        return req

    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        raise RuntimeError  # Not possible
        # return buff  # Nothing lol

    def packData(self, data: HTTPResponse, buff: ByteBuffer):
        # Make sure to mark the response
        data.headers["Server"] = "KUtil"

        data.write(buff)

    def packSubProtocol(self, buff: ByteBuffer):
        raise RuntimeError  # Not possible
        # pass  # Nothing lol


class WebSocketNotAllowed(Exception):
    pass


class HTTPServerConnection(ProtocolConnection):
    # Note that editing the __init__ method might break the whole thing
    onData: Callable[[Self, HTTPRequest | WSMessage], None]
    didUpgradeToWS: bool
    acceptWSChecker: AcceptWSChecker
    onWebsocketEstablishment: Callable[[Any], None] | None
    wsConn: WSConnection | None

    def init(self):
        self.didUpgradeToWS = False
        self.acceptWSChecker = lambda x, y: False
        self.onWebsocketEstablishment = None  # Change if wanted, called with self as the argument
        self.wsConn = None

    def _denyWebsocketConnection(self, notAllowedOrInvalid: bool):
        if notAllowedOrInvalid:
            resp: HTTPResponse = HTTPResponse(400, "Invalid protocol selected", HTTPHeaders(), b'')
        else:
            resp: HTTPResponse = HTTPResponse(400, "Bad request", HTTPHeaders(),
                                              b'Invalid key header or version != 13 selected')
        self.sendData(resp)
        self.close(WebSocketNotAllowed())

    def onDataInner(self, data: HTTPRequest | WSMessage, stoppedUnpacking: bool = False,
                    layer: AbstractProtocol | None = None) -> bool:
        assert isinstance(data, HTTPRequest) if not self.didUpgradeToWS else isinstance(data,
                                                                                        WSMessage)
        if not self.didUpgradeToWS:
            if data.headers.get("Upgrade") == "websocket" and data.headers.get(
                    "Connection") == "Upgrade":
                if not self.acceptWSChecker(self, data):
                    # Cancel the connection if we aren't allowed to establish a WS connection
                    self._denyWebsocketConnection(True)
                    return False
                if data.headers.get("Sec-WebSocket-Version") != "13" or data.headers.get(
                        "Sec-WebSocket-Key") is None:
                    # Make sure we both support v13 and we have a key
                    self._denyWebsocketConnection(False)
                    return False
                # print(data.headers.get("Sec-WebSocket-Key"))
                # print(WSProtocol.createAcceptHeader(data.headers.get("Sec-WebSocket-Key")))
                headers: HTTPHeaders = HTTPHeaders()
                headers["Upgrade"] = "websocket"
                headers["Connection"] = "Upgrade"
                # headers["Sec-WebSocket-Protocol"] = "chat" - breaks stuff, although on Wikipedia
                headers["Sec-WebSocket-Accept"] = WSProtocol.createAcceptHeader(
                    data.headers.get("Sec-WebSocket-Key"))
                resp: HTTPResponse = HTTPResponse(101, "Switching Protocols", headers, b'')
                self.sendData(resp)
                self.removeProtocol(self.layers[-1])  # Remove the HTTP protocol
                self.addProtocol(WSProtocol(self))
                self.didUpgradeToWS = True
                if self.onWebsocketEstablishment:
                    self.onWebsocketEstablishment(self)
                self.wsConn = WSConnection(("", 0), [], neverCall, self.sock)
                return False  # Don't call the onData with the WS request
        return True

    def acceptWebsocket(self, acceptWSChecker: AcceptWSChecker):
        self.acceptWSChecker = acceptWSChecker

    @property
    def ownConnection(self):
        if self.didUpgradeToWS:
            return self.wsConn
        return self


class HTTPServer(ProtocolServer):
    connectionType: type[ProtocolConnection] = HTTPServerConnection
    acceptWSChecker: AcceptWSChecker

    def __init__(self, address: tuple[str, int],
                 onConnection: Callable[[ProtocolConnection], Callable[[Self, HTTPRequest], None]]):
        super().__init__(address, lambda conn: [TCPProtocol(conn), HTTPServerProtocol(conn)],
                         onConnection)
        self.acceptWSChecker = lambda x, y: False

    def acceptWebsocket(self, acceptWSChecker: AcceptWSChecker):
        self.acceptWSChecker = acceptWSChecker

    def onConnectionInner(self, conn: HTTPServerConnection) -> bool:
        conn.acceptWebsocket(self.acceptWSChecker)
        return True
