#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from enum import Enum, unique, auto
from typing import Callable, Any, Self, Optional

from kutil.typing_help import neverCall, returnFalse

from kutil.protocol.AbstractProtocol import AbstractProtocol, NeedMoreDataError
from kutil.buffer.ByteBuffer import ByteBuffer, OutOfBoundsReadError
from kutil.protocol.ProtocolConnection import ProtocolConnection
from kutil.protocol.ProtocolServer import ProtocolServer
from kutil.protocol.TCPConnection import TCPProtocol
from kutil.protocol.HTTP.HTTPRequest import HTTPRequest
from kutil.protocol.HTTP.HTTPResponse import HTTPResponse
from kutil.protocol.HTTP.HTTPHeaders import HTTPHeaders
from kutil.protocol.WS.WSMessage import WSMessage
from kutil.protocol.WSConnection import WSProtocol, WSConnection
from kutil.protocol.SSE.SSEMessage import SSEMessage
from kutil.protocol.SSEConnection import SSEProtocol, SSEConnection

type AcceptWSChecker = Callable[[HTTPServerConnection, HTTPRequest], bool]
type AcceptSSEChecker = Callable[[HTTPServerConnection, HTTPRequest], bool]


@unique
class HTTPConnectionState(Enum):
    """
    A class indicating the current connection state - was it upgraded? Is it still raw HTTP?
    """
    HTTP = auto()
    WS = auto()
    SSE = auto()


class HTTPServerProtocol(AbstractProtocol):
    name = "HTTPServerProtocol"

    def unpackData(self, buff: ByteBuffer) -> HTTPRequest:
        req = HTTPRequest()
        try:
            req.read(buff)
        except OutOfBoundsReadError:
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


class ServerSentEventsNotAllowed(Exception):
    pass


class HTTPServerConnection(ProtocolConnection):
    # Note that editing the __init__ method might break the whole thing
    onData: Callable[[Self, HTTPRequest | WSMessage], None]
    _acceptWSChecker: AcceptWSChecker
    _acceptSSEChecker: AcceptSSEChecker
    _state: HTTPConnectionState
    # Change these two if you want, called with self and the source request as the arguments
    onWebsocketEstablishment: Optional[Callable[[Self, HTTPRequest], None]]
    onSSEEstablishment: Optional[Callable[[Self, HTTPRequest], None]]
    wsConn: Optional[WSConnection]
    sseConn: Optional[SSEConnection]

    def init(self):
        self._state = HTTPConnectionState.HTTP
        self._acceptWSChecker = returnFalse
        self._acceptSSEChecker = returnFalse
        self.onWebsocketEstablishment = None
        self.onSSEEstablishment = None
        self.wsConn = None
        self.sseConn = None

    def _denyWebsocketConnection(self, notAllowedOrInvalid: bool):
        if notAllowedOrInvalid:
            resp: HTTPResponse = HTTPResponse(403, "Invalid protocol selected", HTTPHeaders(), b'')
        else:
            resp: HTTPResponse = HTTPResponse(426, "Upgrade Required", HTTPHeaders(),
                                              b'Invalid key header or version != 13 selected')
        self.sendData(resp)
        self.close(WebSocketNotAllowed())

    def _denySSEConnection(self):
        resp: HTTPResponse = HTTPResponse(406, "Not Acceptable", HTTPHeaders(), b'')
        self.sendData(resp)
        self.close(ServerSentEventsNotAllowed())

    def onDataInner(self, data: HTTPRequest | WSMessage | SSEMessage,
                    stoppedUnpacking: bool = False,
                    layer: Optional[AbstractProtocol] = None) -> bool:
        if self.didNotUpgrade:
            assert isinstance(data, HTTPRequest)
        elif self.didUpgradeToWS:
            assert isinstance(data, WSMessage)
        elif self.didUpgradeToSSE:
            assert isinstance(data, SSEMessage)
        else:
            raise ValueError

        if self.didNotUpgrade and not self.didUpgradeToWS:
            if (data.headers.get("Upgrade") == "websocket" and
                    data.headers.get("Connection").capitalize() == "Upgrade"):
                if not self._acceptWSChecker(self, data):
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
                self.wsConn = WSConnection(("", 0), [], neverCall, self.sock)
                self._state = HTTPConnectionState.WS
                if self.onWebsocketEstablishment:
                    self.onWebsocketEstablishment(self, data)
                return False  # Don't call the onData with the WS request
        if self.didNotUpgrade and not self.didUpgradeToSSE:
            if (data.headers.get("Accept") == "text/event-stream" and
                    data.headers.get("Connection").lower() == "keep-alive"):
                if not self._acceptSSEChecker(self, data):
                    # Cancel the connection if we aren't allowed to establish an SSE connection
                    self._denySSEConnection()
                    return False
                headers: HTTPHeaders = HTTPHeaders()
                headers["Content-Type"] = "text/event-stream"
                headers["X-Omit-Content-Length"] = "1"
                headers["Connection"] = "keep-alive"
                resp: HTTPResponse = HTTPResponse(200, "OK", headers, b'')
                self.sendData(resp)
                self.removeProtocol(self.layers[-1])  # Remove the HTTP protocol
                self.addProtocol(SSEProtocol(self))
                self.sseConn = SSEConnection(("", 0), [], neverCall, self.sock)
                self._state = HTTPConnectionState.SSE
                if self.onSSEEstablishment:
                    self.onSSEEstablishment(self, data)
                return False  # Don't call the onData with the SSE request
        return True

    def acceptWebsocket(self, acceptWSChecker: AcceptWSChecker):
        self._acceptWSChecker = acceptWSChecker

    def acceptServerSentEvents(self, acceptSSEChecker: AcceptSSEChecker):
        self._acceptSSEChecker = acceptSSEChecker

    @property
    def didUpgradeToWS(self) -> bool:
        return self._state is HTTPConnectionState.WS

    @property
    def didUpgradeToSSE(self) -> bool:
        return self._state is HTTPConnectionState.SSE

    @property
    def didNotUpgrade(self) -> bool:
        return self._state is HTTPConnectionState.HTTP

    @property
    def ownConnection(self):
        if self.didUpgradeToWS:
            return self.wsConn
        elif self.didUpgradeToSSE:
            return self.sseConn
        else:
            assert self.didNotUpgrade
            return self


type onConnectionListener = Callable[
    [HTTPServerConnection],  # Argument - the new connection
    Callable[  # Return - onData listener
        [HTTPServerConnection, HTTPRequest | WSMessage | SSEMessage],
        None
    ]
]


class HTTPServer(ProtocolServer):
    connectionType: type[ProtocolConnection] = HTTPServerConnection
    acceptWSChecker: AcceptWSChecker
    acceptSSEChecker: AcceptSSEChecker

    def __init__(self, address: tuple[str, int],
                 onConnection: onConnectionListener):
        super().__init__(address, lambda conn: [TCPProtocol(conn), HTTPServerProtocol(conn)],
                         onConnection)
        self.acceptWSChecker = returnFalse
        self.acceptSSEChecker = returnFalse

    def acceptWebsocket(self, acceptWSChecker: AcceptWSChecker):
        self.acceptWSChecker = acceptWSChecker

    def acceptServerSentEvents(self, acceptSSEChecker: AcceptSSEChecker):
        self.acceptSSEChecker = acceptSSEChecker

    def onConnectionInner(self, conn: HTTPServerConnection) -> bool:
        conn.acceptWebsocket(self.acceptWSChecker)
        conn.acceptServerSentEvents(self.acceptSSEChecker)
        return True


__all__ = ["HTTPServer", "HTTPServerConnection", "HTTPServerProtocol"]
