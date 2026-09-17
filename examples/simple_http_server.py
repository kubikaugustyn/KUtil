#  -*- coding: utf-8 -*-
__author__ = "Jakub Augustýn <kubik.augustyn@post.cz>"

from threading import Event, Thread
from typing import Any

from kutil.io.file import readFile, bCRLF
from kutil.threads import ThreadWaiter
from kutil.protocol.HTTP.simple_server.SimpleHTTPServer import httpResponse, SimpleHTTPServer, \
    SimpleHTTPServerRouteManager, SimpleHTTPRequestContext, SimpleHTTPWebSocketContext, SimpleHTTPSSEContext, TResponse, \
    TResponseBody, THeaders, SimpleHTTPServerCORSSettings, convertResponse, HTTPMethod, HTTPRequest, HTTPResponse, \
    WSData, SSEMessage

router: SimpleHTTPServerRouteManager = SimpleHTTPServerRouteManager(
    cors=SimpleHTTPServerCORSSettings(
        enabled=True,
        foreign_hosts=["*"],
        allowed_methods=[HTTPMethod.DELETE],
        allowed_request_headers=["Content-Type", "X-Secret-Header-Request"],
        allowed_response_headers=["X-Secret-Header"],
    )
)


@router.route("/")
def get_home(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    # return "Hello, world! See /test.html"
    return httpResponse(308, "Hello, world! See /test.html", headers={"Location": "/test.html"})


@router.route("/test.html")
def get_test(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    body: str = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no">
    <title>KUtil Simple HTTP server</title>
</head>
<body>
    <h2>Hello, world!</h2>
    <ul>
        <li><a href="/api/products/1">Product 1</a></li>
        <li><a href="/api/products/2/">Product 2</a></li>
        <li><a href="/api/products/3/description">Product 3's description</a></li>
        <li><a href="/api/products/3/brew">Brew coffee with product 3</a></li>
    </ul>
    <a href="/ws">WebSocket test</a><br>
    <a href="/sse">SSE test</a><br>
    <a href="/big-file">Big file</a><br>
    CORS testing (DevTools Console & Network): <pre>await fetch("http://localhost:9000/cors", {method: "DELETE", headers: {"X-Secret-Header-Request": "idk", "Content-Type": "application/json"}, body: JSON.stringify({"ignored": "body"})})</pre>
</body>
</html>"""
    return httpResponse(200, body, contentType="text/html")


def _get_product_id(req: HTTPRequest, ctx: SimpleHTTPRequestContext, *,
                    allow_unknown: bool = False) -> int | HTTPResponse:
    try:
        id_: int = int(ctx.params[0])
    except (ValueError, IndexError):
        return httpResponse(400, {"error": "Invalid product ID"})
    if id_ not in (1, 2, 3) and not allow_unknown:
        return httpResponse(404, {"error": "Product not found"})
    return id_


@router.route("/api/products/*")
def get_product(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    id_ = _get_product_id(req, ctx)
    if isinstance(id_, HTTPResponse): return id_

    return {"id": id_}


@router.route("/api/products/*", HTTPMethod.POST)
def new_product(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    id_ = _get_product_id(req, ctx, allow_unknown=True)
    if isinstance(id_, HTTPResponse): return id_

    description: str = str(req.json["description"]).strip()
    if not description: return httpResponse(400, {"error": "Invalid description"})

    print(f"Definitely created a new Product(id={id_}, description={repr(description)})")
    return {"id": id_, "description": description}


@router.route("/api/products/*/description")
def get_product(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    id_ = _get_product_id(req, ctx)
    if isinstance(id_, HTTPResponse): return id_

    return {
        "id": id_,
        "description": {
            1: "A teapot",
            2: "A brewing machine",
            3: "A different brewing machine",
        }[id_]
    }


@router.route("/api/products/*/brew")
def get_product(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    id_ = _get_product_id(req, ctx)
    if isinstance(id_, HTTPResponse): return id_

    if id_ == 1:
        return httpResponse(418, {"error": "Unable to brew coffee, I'm a tea pot!"})
    elif id_ == 2:
        return httpResponse(503, {"error": "Temporarily out of coffee"})
    elif id_ == 3:
        # message/coffeepot causes automatic downloads - https://www.rfc-editor.org/info/rfc2324/#section-4
        return httpResponse(200, b"start", contentType="text/plain")
    else:
        raise ValueError("Unknown product ID")


@router.route("/ws")
def websocket(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    return httpResponse(200, readFile("./websocket_server.html", "buffer"), contentType="text/html")


@router.websocket("/ws")
def websocket(req: HTTPRequest, ctx: SimpleHTTPWebSocketContext) -> bool:
    def listener(_, event: str, data: Any) -> None:
        if event == "websocket-established":
            ctx.sendData("test")
            ctx.sendData("you")
            ctx.sendData("sussy")
            ctx.sendData("baka")
        elif event == "websocket-data":
            assert isinstance(data, WSData)
            assert data.text == "good"
            ctx.close()

    ctx.addListener(listener)
    return True


@router.route("/sse")
def sse(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    return httpResponse(200, readFile("./sse_server.html", "buffer"), contentType="text/html")


sse_conns: list[SimpleHTTPSSEContext] = []
sse_thread_waiter: ThreadWaiter = ThreadWaiter()
sse_stop: Event = Event()


def sse_thread_impl() -> None:
    from time import time

    print("SSE thread started")
    while not sse_stop.is_set():
        sse_thread_waiter.wait(maxTime=.01)
        if len(sse_conns) == 0:
            continue

        # Send the time update message, letting the user know the current server time
        # Runs every ~10ms
        ev = SSEMessage(data=HTTPResponse.enc(str(time())), eventName="update-time")
        for conn in sse_conns:
            if conn.closed: continue
            conn.conn.sendData(ev)
    print("SSE thread stopped.")


@router.sse("/sse")
def sse(req: HTTPRequest, ctx: SimpleHTTPSSEContext) -> bool:
    def listener(_, event: str, data: Any) -> None:
        if event == "sse-established":
            sse_conns.append(ctx)
            sse_thread_waiter.reset()
        elif event == "pre-close":
            sse_conns.remove(ctx)

    ctx.addListener(listener)
    return True


@router.route("/big-file")
def big_file(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    from kutil.buffer.ByteBuffer import ByteBuffer
    from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer
    from kutil.buffer.AppendedByteBuffer import AppendedByteBuffer

    # Roughly 42 MB * 100 = 4.2 GB
    line: bytes = b'This is a single line of a very big file' + bCRLF
    lorem: ByteBuffer = MemoryByteBuffer(line * 1024 * 1024)
    big: ByteBuffer = AppendedByteBuffer([lorem] * 100)
    return httpResponse(200, big, contentType="text/plain",
                        headers={"Content-Disposition": 'attachment; filename="big-file.txt"'})


@router.route("/cors", HTTPMethod.DELETE, cors=True)
def big_file(req: HTTPRequest, ctx: SimpleHTTPRequestContext) -> TResponse:
    try:
        request: str = req.headers["X-Secret-Header-Request"]
    except KeyError:
        return 400, "Missing X-Secret-Header-Request header"

    return httpResponse(200, "Deleted nothing :-)", headers={
        "X-Secret-Header": f"some-secret-value; {request}",
    })


def main() -> None:
    sse_thread = Thread(target=sse_thread_impl)
    sse_thread.start()

    port: int = 9000
    server: SimpleHTTPServer = SimpleHTTPServer(("0.0.0.0", port), router)
    # , [f"127.0.0.1:{port}", f"localhost:{port}"])
    print(f"Server started at http://127.0.0.1:{port}")
    server.listen()
    sse_stop.set()
    sse_thread.join()
    print("Server stopped.")


if __name__ == '__main__':
    main()
