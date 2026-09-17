#  -*- coding: utf-8 -*-
"""An implementation of a high-level HTTP server over the low-level KUtil APIs"""
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

from asyncio import exceptions
from threading import Lock
from typing import Callable, Optional, cast, Literal, Never, overload, Any, Self
from json import dumps
from urllib.parse import ParseResult, urlparse, urljoin, parse_qs
from dataclasses import dataclass, field

from kutil.buffer.ByteBuffer import ByteBufferLike, ByteBuffer
from kutil.protocol.ProtocolConnection import ProtocolConnection
from kutil.protocol.HTTP import HTTPRequest, HTTPResponse, HTTPHeaders, HTTPMethod
from kutil.protocol.WS.WSMessage import WSMessage, WSData
from kutil.protocol.SSE.SSEMessage import SSEMessage
from kutil.protocol.HTTPServer import HTTPServer, HTTPServerConnection

from kutil.protocol.HTTP.simple_server.HTTPStatusCodes import getStatusPhrase
from kutil.protocol.HTTP.simple_server.HTTPRequestTiming import HTTPRequestTiming

# TODO Start using proper logging and maybe create a message handler "framework" to allow listening to messages

type THeaders = dict | HTTPHeaders
type TResponseBody = ByteBufferLike | dict | str
type TResponse = (
        HTTPResponse |  # Full HTTP response
        tuple[int, TResponseBody] |  # Status code, body
        tuple[int, THeaders, TResponseBody] |  # Status code, headers, body
        TResponseBody  # Body
)


def _encode_body(contentType: Optional[str], body: TResponseBody) -> tuple[str, ByteBufferLike]:
    encoded: ByteBufferLike
    type_: str
    if isinstance(body, dict):
        encoded = HTTPResponse.enc(dumps(body))
        type_ = "application/json"
    elif isinstance(body, str):
        encoded = HTTPResponse.enc(body)
        type_ = "text/plain" if contentType is None else contentType
    elif isinstance(body, ByteBufferLike):
        encoded = body
        type_ = "application/octet-stream" if contentType is None else contentType
    else:
        raise ValueError("Invalid body type")

    if contentType is not None and type_ != contentType:
        raise ValueError(f"Invalid content type, encoded as {type_}, but received {contentType}")

    if encoded is None or not isinstance(encoded, ByteBufferLike): raise RuntimeError("Failed to encode body")
    if type_ is None or not isinstance(type_, str): raise RuntimeError("Failed to set content type")
    return type_, encoded


def httpResponse(statusCode: int, body: TResponseBody, *,
                 contentType: Optional[str] = None, headers: Optional[THeaders] = None) -> HTTPResponse:
    # Get headers
    headers_: HTTPHeaders = HTTPHeaders()
    if headers is not None:
        assert isinstance(headers, (dict, HTTPHeaders)), "Headers must either be a dict or HTTPHeaders"
        headers_ = HTTPHeaders()
        headers_.update(headers)

    # Get the status
    assert 100 <= statusCode < 600, "Status code out of range"
    statusPhrase: str = headers_.get("__STATUS_PHRASE__", getStatusPhrase(statusCode, "Unknown Status Code"))

    # Convert the body
    contentType_, body_ = _encode_body(contentType, body)
    headers_["Content-Type"] = contentType_

    return HTTPResponse(statusCode, statusPhrase, headers_, body_)


def convertResponse(resp: TResponse) -> HTTPResponse:
    if isinstance(resp, HTTPResponse):
        return resp
    elif isinstance(resp, tuple):
        statusCode = resp[0]
        if not isinstance(statusCode, int): raise ValueError("Response tuple[0] must be an integer status code")
        if len(resp) == 2:
            body = cast(TResponseBody, resp[1])
            return httpResponse(statusCode, body)
        else:
            if len(resp) != 3: raise ValueError("Response tuple must contain 2 or 3 elements")
            headers = cast(THeaders, resp[1])
            body = cast(TResponseBody, resp[2])
            return httpResponse(statusCode, body, headers=headers)
    else:
        body = cast(TResponseBody, resp)
        return httpResponse(200, body)


@dataclass(frozen=True)
class SimpleHTTPServerCORSSettings:
    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/OPTIONS#preflighted_requests_in_cors
    enabled: bool = False  # Whether to enable CORS
    foreign_hosts: list[str] = field(default_factory=list)
    allowed_methods: list[HTTPMethod] = field(default_factory=list)
    allowed_request_headers: list[str] = field(default_factory=list)
    allowed_response_headers: list[str] = field(default_factory=list)
    max_age: int = 86_400  # For how long should the above permissions apply in seconds, defaults to 1 day

    # This configuration only applies to non-overridden OPTIONS requests by default.
    # You will wither need to specify cors=True to every endpoint you want the non-preflight requests to succeed on,
    # or transform your response with router.processCORS(...).


@dataclass(frozen=True)
class SimpleHTTPRequestContext:
    params: list[str]  # route wildcard values
    query: dict[str, list[str]]
    url: ParseResult


class _SimpleHTTPGeneralContext:
    _conn: HTTPServerConnection
    _req: SimpleHTTPRequestContext
    _listeners: list[Callable[[Self, str, Any], None]]

    def __init__(self, conn: HTTPServerConnection, req: SimpleHTTPRequestContext) -> None:
        self._conn = conn
        self._req = req
        self._listeners = []

    def addListener(self, listener: Callable[[Self, str, Any], None]) -> None:
        self._listeners.append(listener)

    def onEvent(self, conn: HTTPServerConnection, event: str, data: Any) -> None:
        if conn is not self._conn: return
        for listener in self._listeners:
            listener(self, event, data)

    def close(self, cause: Optional[Exception] = None) -> None:
        self._conn.close(cause)

    @property
    def closed(self) -> bool:
        return self._conn.closed

    @property
    def conn(self) -> HTTPServerConnection:
        return self._conn

    @property
    def request(self) -> SimpleHTTPRequestContext:
        return self._req


class SimpleHTTPWebSocketContext(_SimpleHTTPGeneralContext):
    def sendData(self, data: ByteBufferLike | str) -> None:
        self._conn.sendData(WSData(data))


class SimpleHTTPSSEContext(_SimpleHTTPGeneralContext):
    def sendData(self, eventName: Optional[str], data: bytes, eventID: Optional[bytes] = None) -> None:
        self._conn.sendData(SSEMessage(eventName, data, eventID))


type TRequestMethod = HTTPMethod | Literal["WS", "SSE"]
type TSimpleHTTPRouteProcessor = Callable[[HTTPRequest, SimpleHTTPRequestContext], TResponse]  # def handle(req, ctx)...
type TSimpleWSRouteProcessor = Callable[[HTTPRequest, SimpleHTTPWebSocketContext], bool]  # def handle(req, ctx): accept
type TSimpleSSERouteProcessor = Callable[[HTTPRequest, SimpleHTTPSSEContext], bool]  # def handle(req, ctx): accept
type TSimpleRouteProcessor = TSimpleHTTPRouteProcessor | TSimpleWSRouteProcessor | TSimpleSSERouteProcessor
type TSimpleRouteEndpoint = list[Optional[TSimpleRouteProcessor]]  # Mapped to REQUEST_METHODS
type TRouteEntry = tuple[Optional[str], bool, TRoute | TSimpleRouteEndpoint]  # (segment, isRoute, route | endpoint)
type TRoute = list[TRouteEntry]


class EndpointNotFoundError(Exception): ...


class MethodNotAllowedError(Exception):
    methods: list[str]  # The methods that are allowed

    def __init__(self, message: str, methods: list[str]) -> None:
        super().__init__(message)
        self.methods = methods


class SimpleHTTPServerRouteManager:
    @staticmethod
    def _splitRoute(route: str) -> list[str]:
        route = urlparse(urljoin("/", route)).path
        return route.strip("/").split("/")

    @classmethod
    def _parseRouteWithWildcards(cls, route: str) -> list[Optional[str]]:
        return [
            segment if segment != "*" else None
            for segment in cls._splitRoute(route)
        ]

    @classmethod
    def _parseRoute(cls, route: str) -> list[str]:
        return cls._splitRoute(route)

    @staticmethod
    def _segmentsEq(a: Optional[str], b: Optional[str]) -> bool:
        """
        Checks whether the provided segments of a route match.

        :param a: The segment A
        :param b: The segment B
        """
        if a is None:
            return b is None
        else:
            return b is not None and a == b

    @staticmethod
    def _segmentsMatch(a: Optional[str], b: str) -> bool:
        """
        Checks whether the provided segments of a route match.

        If segment A is a wildcard (None), will they match.
        If segment A is NOT a wildcard, their values will be compared.

        :param a: The segment A
        :param b: The segment B
        """
        return True if a is None else a == b

    REQUEST_METHODS: list[TRequestMethod] = [*list(HTTPMethod), "WS", "SSE"]

    _root: TRoute
    _cors: SimpleHTTPServerCORSSettings

    def __init__(self, *, cors: Optional[SimpleHTTPServerCORSSettings] = None) -> None:
        self._root = []
        self._cors = cors or SimpleHTTPServerCORSSettings()

    def _addEndpoint(self, route: list[Optional[str]]) -> TSimpleRouteEndpoint:
        entries: TRoute | TSimpleRouteEndpoint = self._root
        for i, segment in enumerate(route):
            isRoute: bool = i < len(route) - 1
            for entry in entries:
                other, otherIsRoute, routeOrEndpoint = entry
                if not self._segmentsEq(segment, other): continue
                if isRoute != otherIsRoute: continue

                entries = routeOrEndpoint
                break
            else:
                if isRoute:
                    newEntries: TRoute = []
                else:
                    newEntries: TSimpleRouteEndpoint = [None] * len(self.REQUEST_METHODS)
                newEntry: TRouteEntry = (segment, isRoute, newEntries)
                entries.append(newEntry)
                entries = newEntries
        assert not any(map(lambda x: isinstance(x, tuple), entries))  # Just a sanity check heuristic
        return cast(TSimpleRouteEndpoint, entries)

    def _getEndpoint(self, route: list[str]) -> tuple[TSimpleRouteEndpoint, list[str]]:
        params: list[str] = []
        entries: TRoute | TSimpleRouteEndpoint = self._root
        for i, segment in enumerate(route):
            isRoute: bool = i < len(route) - 1
            for entry in entries:
                other, otherIsRoute, routeOrEndpoint = entry
                if not self._segmentsMatch(other, segment): continue
                if isRoute != otherIsRoute: continue

                entries = routeOrEndpoint
                if other is None:
                    params.append(segment)
                break
            else:
                raise EndpointNotFoundError("The requested endpoint was not found")
        assert not any(map(lambda x: isinstance(x, tuple), entries))  # Just a sanity check heuristic
        return cast(TSimpleRouteEndpoint, entries), params

    def _addEntry(self, route: list[Optional[str]], method: TRequestMethod, value: TSimpleRouteProcessor) -> None:
        endpoint: TSimpleRouteEndpoint = self._addEndpoint(route)
        index: int = self.REQUEST_METHODS.index(method)
        if endpoint[index] is not None: raise RuntimeError("This endpoint and method has already ben added")
        endpoint[index] = value

    def _processSimpleOptionsRequest(self, endpoint: TSimpleRouteEndpoint, req: HTTPRequest,
                                     ctx: SimpleHTTPRequestContext) -> TResponse:
        methods: list[str] = [HTTPMethod.OPTIONS.name]
        all_methods: list[str] = [HTTPMethod.OPTIONS.name]
        for method, processor in zip(self.REQUEST_METHODS, endpoint):
            if processor is None: continue
            if not isinstance(method, HTTPMethod):
                all_methods.append(method)
                continue
            if method is HTTPMethod.OPTIONS: continue
            methods.append(method.name)
            all_methods.append(method.name)

        resp: HTTPResponse = httpResponse(200, b'', headers={
            "Allow": ", ".join(methods),
            "X-KUtil-Allow": ", ".join(all_methods),
        })
        return self.processCORS(req, ctx, resp, _inner_methods=methods)

    def processCORS(self, req: HTTPRequest, ctx: SimpleHTTPRequestContext, resp: HTTPResponse, *,
                    _inner_methods: Optional[list[str]] = None) -> TResponse:
        methods: list[str] = _inner_methods if _inner_methods is not None else [req.method.name]
        required_method: Optional[str] = req.headers.get("Access-Control-Request-Method")
        if required_method is not None and (
                required_method not in methods or
                not self._cors.enabled or
                HTTPMethod(required_method.encode("utf-8")) not in self._cors.allowed_methods
        ):
            return httpResponse(403, "This endpoint does not support the requested method", headers=resp.headers)

        required_headers: list[str] = req.headers.get("Access-Control-Request-Headers", "").split(",")
        required_headers = list(filter(bool, map(lambda x: x.strip(), required_headers)))
        headers_allowed: bool = self._cors.enabled
        if headers_allowed:
            for header in required_headers:
                for other in self._cors.allowed_request_headers:
                    if header.lower() == other.lower(): break
                else:
                    headers_allowed = False
                    break
        if len(required_headers) > 0 and not headers_allowed:
            return httpResponse(403, "This server does not support the requested headers", headers=resp.headers)

        origin: Optional[str] = req.headers.get("Origin")
        server_host: str = f"{ctx.url.scheme}://{ctx.url.netloc}"
        if origin is not None and (
                origin != server_host and
                (not self._cors.enabled or (
                        origin not in self._cors.foreign_hosts and "*" not in self._cors.foreign_hosts
                ))
        ):
            return httpResponse(403, "This server does not support the requested origin", headers=resp.headers)

        if self._cors.enabled:
            if origin is not None:
                resp.headers["Access-Control-Allow-Origin"] = cast(str, origin)

            allowed_methods: set[str] = set(map(lambda x: x.name, self._cors.allowed_methods)).intersection(methods)
            if len(allowed_methods) > 0:
                resp.headers["Access-Control-Allow-Methods"] = ", ".join(allowed_methods)

            if len(required_headers) > 0:
                resp.headers["Access-Control-Allow-Headers"] = ", ".join(required_headers)

            if len(self._cors.allowed_response_headers) > 0:
                resp.headers["Access-Control-Expose-Headers"] = ", ".join(self._cors.allowed_response_headers)

            resp.headers["Access-Control-Max-Age"] = str(self._cors.max_age)
        return resp

    def _processSimpleHeadRequest(self, get_processor: TSimpleHTTPRouteProcessor, req: HTTPRequest,
                                  ctx: SimpleHTTPRequestContext) -> TResponse:
        raw_response: TResponse = get_processor(req, ctx)
        response: HTTPResponse = convertResponse(raw_response)

        # Remove the body
        if isinstance(response.body, ByteBuffer): response.body.destroy()
        response.body = b''

        return response

    @overload
    def register(self, method: HTTPMethod, route: str, processor: TSimpleHTTPRouteProcessor) -> None:
        ...

    @overload
    def register(self, method: Literal["WS"], route: str, processor: TSimpleWSRouteProcessor) -> None:
        ...

    @overload
    def register(self, method: Literal["SSE"], route: str, processor: TSimpleSSERouteProcessor) -> None:
        ...

    def register(self, method: TRequestMethod, route: str, processor: TSimpleRouteProcessor) -> None:
        segments: list[Optional[str]] = self._parseRouteWithWildcards(route)
        self._addEntry(segments, method, processor)

    def route(self, route: str, method: HTTPMethod = HTTPMethod.GET, *, cors: bool = False) -> \
            Callable[[TSimpleHTTPRouteProcessor], TSimpleHTTPRouteProcessor]:
        """
        A decorator to register a route.

        :param route: The route to register
        :param method: HTTP method, defaults to GET
        :param cors: Whether to call processCORS on the response before returning it
        """

        def wrapper(function: TSimpleHTTPRouteProcessor) -> TSimpleHTTPRouteProcessor:
            if cors:
                original_function: TSimpleHTTPRouteProcessor = function
                function = lambda req, ctx: self.processCORS(req, ctx, convertResponse(original_function(req, ctx)))

            self.register(method, route, function)
            return function

        return wrapper

    def websocket(self, route: str) -> Callable[[TSimpleWSRouteProcessor], TSimpleWSRouteProcessor]:
        """
        A decorator to register a WebSocket route.

        :param route: The route to register
        """

        def wrapper(function: TSimpleWSRouteProcessor) -> TSimpleWSRouteProcessor:
            self.register("WS", route, function)
            return function

        return wrapper

    def sse(self, route: str) -> Callable[[TSimpleSSERouteProcessor], TSimpleSSERouteProcessor]:
        """
        A decorator to register a Server-Sent Events route.

        :param route: The route to register
        """

        def wrapper(function: TSimpleSSERouteProcessor) -> TSimpleSSERouteProcessor:
            self.register("SSE", route, function)
            return function

        return wrapper

    @overload
    def resolve(self, method: HTTPMethod, route: str) -> tuple[TSimpleHTTPRouteProcessor, list[str]] | Never:
        ...

    @overload
    def resolve(self, method: Literal["WS"], route: str) -> tuple[TSimpleWSRouteProcessor, list[str]] | Never:
        ...

    @overload
    def resolve(self, method: Literal["SSE"], route: str) -> tuple[TSimpleSSERouteProcessor, list[str]] | Never:
        ...

    def resolve(self, method: TRequestMethod, route: str) -> tuple[TSimpleRouteProcessor, list[str]] | Never:
        segments: list[str] = self._parseRoute(route)
        endpoint, params = self._getEndpoint(segments)

        index: int = self.REQUEST_METHODS.index(method)
        processor: Optional[TSimpleRouteProcessor] = endpoint[index]

        # Try to fall back to the default OPTIONS and HEAD handlers
        if processor is None and method in (HTTPMethod.OPTIONS, HTTPMethod.HEAD):
            if method is HTTPMethod.OPTIONS:
                processor = lambda a, b: self._processSimpleOptionsRequest(endpoint, a, b)
            else:
                get_index: int = self.REQUEST_METHODS.index(HTTPMethod.GET)
                get_processor: Optional[TSimpleRouteProcessor] = endpoint[get_index]
                if get_processor is not None:
                    get_processor_http = cast(TSimpleHTTPRouteProcessor, get_processor)
                    processor = lambda a, b: self._processSimpleHeadRequest(get_processor_http, a, b)

        if processor is None:
            methods: list[str] = []
            for method, processor in zip(self.REQUEST_METHODS, endpoint):
                if processor is None: continue
                if isinstance(method, str):
                    methods.append(method)
                else:
                    methods.append(method.name)
            raise MethodNotAllowedError("This endpoint does not support the requested method", methods)
        return processor, params


type TSimpleConnectionListener = Callable[[HTTPServerConnection, str, Any], None]


class SimpleHTTPServerConnectionManager:
    _connection_mutex: Lock
    _connections: dict[int, HTTPServerConnection]
    _listener_mutex: Lock
    _listeners: dict[int, list[TSimpleConnectionListener]]

    def __init__(self) -> None:
        self._connection_mutex = Lock()
        self._connections = {}
        self._listener_mutex = Lock()
        self._listeners = {}

    def addListener(self, conn: HTTPServerConnection, listener: TSimpleConnectionListener) -> None:
        self.dispatch(conn, "pre-add-listener", listener)
        id_: int = id(conn)
        with self._listener_mutex:
            try:
                listeners = self._listeners[id_]
            except KeyError:
                self._listeners[id_] = listeners = []

            listeners.append(listener)
        self.dispatch(conn, "post-add-listener", listener)

    def removeListener(self, conn: HTTPServerConnection, listener: TSimpleConnectionListener) -> None:
        self.dispatch(conn, "pre-remove-listener", listener)
        id_: int = id(conn)
        with self._listener_mutex:
            try:
                listeners = self._listeners[id_]
            except KeyError:
                raise ValueError("Cannot remove a listener that wasn't added")

            listeners.remove(listener)
        self.dispatch(conn, "post-remove-listener", listener)

    def removeListeners(self, conn: HTTPServerConnection) -> None:
        id_: int = id(conn)
        with self._listener_mutex:
            try:
                listeners = self._listeners[id_].copy()
            except KeyError:
                return

        for listener in listeners:
            self.removeListener(conn, listener)

    def dispatch(self, conn: HTTPServerConnection, event: str, data: Any = None) -> None:
        id_: int = id(conn)
        with self._listener_mutex:
            try:
                listeners = self._listeners[id_].copy()
            except KeyError:
                return

        for listener in listeners:
            try:
                listener(conn, event, data)
            except Exception as e:
                print("Error in listener (should NEVER happen, check your code!!!):", e)

    def onConnection(self, conn: HTTPServerConnection) -> None:
        id_: int = id(conn)
        with self._connection_mutex:
            if id_ in self._connections:
                e: Exception = RuntimeError("There already exists an active connection with the same ID")
                conn.close(e)
                raise e
            self._connections[id_] = conn

    def getAllConnections(self) -> list[HTTPServerConnection]:
        with self._connection_mutex:
            return list(self._connections.values())

    def onClose(self, conn: ProtocolConnection, cause: Optional[Exception]) -> None:
        assert isinstance(conn, HTTPServerConnection)
        self.dispatch(conn, "pre-close", cause)
        id_: int = id(conn)
        with self._connection_mutex:
            del self._connections[id_]
        self.removeListeners(conn)
        self.dispatch(conn, "post-close", cause)

    def onHTTPRequest(self, conn: HTTPServerConnection, req: HTTPRequest) -> None:
        self.dispatch(conn, "http-request", req)

    def onHTTPException(self, conn: HTTPServerConnection, req: HTTPRequest, exception: Exception) -> None:
        self.dispatch(conn, "http-exception", (req, exception))

    def onHTTPResponse(self, conn: HTTPServerConnection, req: HTTPRequest, resp: HTTPResponse) -> None:
        self.dispatch(conn, "http-response", (req, resp))

    def onWebSocketEstablishment(self, conn: HTTPServerConnection, req: HTTPRequest) -> None:
        self.dispatch(conn, "websocket-established", req)

    def onWebSocketData(self, conn: HTTPServerConnection, message: WSData) -> None:
        self.dispatch(conn, "websocket-data", message)

    def onSSEEstablishment(self, conn: HTTPServerConnection, req: HTTPRequest) -> None:
        self.dispatch(conn, "sse-established", req)

    def onSSEData(self, conn: HTTPServerConnection, event: SSEMessage) -> None:
        self.dispatch(conn, "sse-data", event)


class SimpleHTTPServer:
    @staticmethod
    def _parseUrl(req: HTTPRequest) -> ParseResult:
        host: str = ("http://" + req.headers['Host']) if 'Host' in req.headers else ''
        url = urlparse(host + req.requestURI)
        return url

    @staticmethod
    def _getHost(url: ParseResult) -> str:
        return url.netloc
        # host: Optional[str] = url.hostname
        # return host if host is not None else ''

    _server: HTTPServer
    type THostnames = list[str] | Literal["*"] | Literal["no-cors"]
    _hostnames: THostnames
    _simple_routes: SimpleHTTPServerRouteManager
    _connections: SimpleHTTPServerConnectionManager

    def __init__(self, address: tuple[str, int], routes: SimpleHTTPServerRouteManager,
                 hostnames: THostnames = "no-cors") -> None:
        self._server = HTTPServer(address, self._onConnection)
        self._server.acceptWebsocket(self._onWSRequest)
        self._server.acceptServerSentEvents(self._onSSERequest)
        self._hostnames = hostnames
        self._simple_routes = routes
        self._connections = SimpleHTTPServerConnectionManager()

    def listen(self) -> None:
        try:
            self._server.listen()
        except KeyboardInterrupt:
            self._server.close()

            # Close all connections
            reason: Exception = RuntimeError("Server closing")
            for conn in self._connections.getAllConnections():
                try:
                    conn.close(reason)
                except Exception as e:
                    print("Error while closing a connection:", e)

    def _onConnection(self, conn: HTTPServerConnection) -> Callable[[HTTPServerConnection,
                                                                     HTTPRequest | WSData | SSEMessage], None]:
        if not isinstance(conn, HTTPServerConnection): raise ValueError("Invalid connection type")

        self._connections.onConnection(conn)
        conn.onCloseListeners.append(self._connections.onClose)
        conn.onWebsocketEstablishment = self._connections.onWebSocketEstablishment
        conn.onSSEEstablishment = self._connections.onSSEEstablishment

        return self._onData

    def _onData(self, conn: HTTPServerConnection, data: HTTPRequest | WSData | SSEMessage) -> None:
        if not isinstance(conn, HTTPServerConnection): raise ValueError("Invalid connection type")

        if conn.didNotUpgrade:
            if not isinstance(data, HTTPRequest): raise ValueError("Invalid data type")
            self._onHTTPData(conn, data)
        elif conn.didUpgradeToWS:
            if not isinstance(data, WSData): raise ValueError("Invalid data type")
            self._onWSData(conn, data)
        elif conn.didUpgradeToSSE:
            if not isinstance(data, SSEMessage): raise ValueError("Invalid data type")
            self._onSSEData(conn, data)
        else:
            raise RuntimeError("Invalid connection state")

    def _onHTTPData(self, conn: HTTPServerConnection, req: HTTPRequest) -> None:
        timing: HTTPRequestTiming = HTTPRequestTiming()
        timing.event("PreRequest", forceNoTime=True)
        self._connections.onHTTPRequest(conn, req)

        error: Optional[Exception] = None
        try:
            resp: HTTPResponse = self._processRequest(conn, req, timing)
        except Exception as e:
            self._connections.onHTTPException(conn, req, e)
            resp: HTTPResponse = httpResponse(500, str(e))
            error = e

        timing.event("GotResponse")
        resp.headers["Server-Timing"] = str(timing)
        if self._hostnames == "*":
            resp.headers["Access-Control-Allow-Origin"] = "*"
        elif self._hostnames != "no-cors":
            assert isinstance(self._hostnames, list)
            origin: str = self._getHost(self._parseUrl(req))
            if origin:
                resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Connection"] = "close"
        self._connections.onHTTPResponse(conn, req, resp)
        conn.sendData(resp)

        if resp.headers.get("Connection", "close") != "keep-alive" or error is not None:
            conn.close(error)

    def _onWSData(self, conn: HTTPServerConnection, message: WSData) -> None:
        self._connections.onWebSocketData(conn, message)

    def _onSSEData(self, conn: HTTPServerConnection, event: SSEMessage) -> None:
        self._connections.onSSEData(conn, event)

    def _checkCorrectHost(self, url: ParseResult) -> Optional[HTTPResponse]:
        if not isinstance(self._hostnames, list): return None
        host: str = self._getHost(url)
        if host not in self._hostnames:
            return httpResponse(421, "This server isn't configured for the requested hostname")
        return None

    def _processRequest(self, conn: HTTPServerConnection, req: HTTPRequest, timing: HTTPRequestTiming) -> HTTPResponse:
        url: ParseResult = self._parseUrl(req)
        query: dict[str, list[str]] = parse_qs(url.query)
        if (resp := self._checkCorrectHost(url)) is not None: return resp

        try:
            processor, params = self._simple_routes.resolve(req.method, url.path)
            ctx: SimpleHTTPRequestContext = SimpleHTTPRequestContext(params, query, url)
            return self._executeProcessor(conn, req, processor, ctx)
        except EndpointNotFoundError as e:
            self._connections.onHTTPException(conn, req, e)
            pass  # Pass through
        except MethodNotAllowedError as e:
            self._connections.onHTTPException(conn, req, e)
            methods: list[str] = e.methods
            return httpResponse(405, f"This endpoint does not accept the requested method. "
                                     f"Accepted method{'s' if len(methods) > 1 else ''}: {', '.join(methods)}",
                                headers={"Allow": ", ".join(methods)})

        return httpResponse(404, "The requested resource was not found on this server")

    def _executeProcessor(self, conn: HTTPServerConnection, req: HTTPRequest,
                          processor: TSimpleHTTPRouteProcessor, ctx: SimpleHTTPRequestContext) -> HTTPResponse:
        try:
            resp: TResponse = processor(req, ctx)
        except Exception as e:
            self._connections.onHTTPException(conn, req, e)
            return httpResponse(500, "Route processor failed: " + str(e))
        return convertResponse(resp)

    def _onWSRequest(self, conn: HTTPServerConnection, req: HTTPRequest) -> bool:
        url: ParseResult = self._parseUrl(req)
        query: dict[str, list[str]] = parse_qs(url.query)
        if self._checkCorrectHost(url) is not None: return False

        try:
            processor, params = self._simple_routes.resolve("WS", url.path)
            httpCtx: SimpleHTTPRequestContext = SimpleHTTPRequestContext(params, query, url)
            ctx: SimpleHTTPWebSocketContext = SimpleHTTPWebSocketContext(conn, httpCtx)
            self._connections.addListener(conn, ctx.onEvent)
            return processor(req, ctx)
        except EndpointNotFoundError:
            return False
        except MethodNotAllowedError:
            return False

    def _onSSERequest(self, conn: HTTPServerConnection, req: HTTPRequest) -> bool:
        url: ParseResult = self._parseUrl(req)
        query: dict[str, list[str]] = parse_qs(url.query)
        if self._checkCorrectHost(url) is not None: return False

        try:
            processor, params = self._simple_routes.resolve("SSE", url.path)
            httpCtx: SimpleHTTPRequestContext = SimpleHTTPRequestContext(params, query, url)
            ctx: SimpleHTTPSSEContext = SimpleHTTPSSEContext(conn, httpCtx)
            self._connections.addListener(conn, ctx.onEvent)
            return processor(req, ctx)
        except EndpointNotFoundError:
            return False
        except MethodNotAllowedError:
            return False


__all__ = [
    "httpResponse", "SimpleHTTPServer",  # Primary
    # Secondary
    "SimpleHTTPServerRouteManager", "SimpleHTTPRequestContext", "SimpleHTTPWebSocketContext", "SimpleHTTPSSEContext",
    "TResponse", "TResponseBody", "THeaders", "SimpleHTTPServerCORSSettings",
    "convertResponse",  # Utils
    "HTTPMethod", "HTTPRequest", "HTTPResponse", "WSData", "SSEMessage",  # Simpler imports
]
