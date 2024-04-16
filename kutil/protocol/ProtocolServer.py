#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from socket import socket, AF_INET, SOCK_STREAM
from typing import Callable, Any

from kutil.typing_help import neverCall

from kutil.protocol.AbstractProtocol import AbstractProtocol
from kutil.protocol.ProtocolConnection import ProtocolConnection

type OnConnectionListener = Callable[
    [ProtocolConnection], Callable[[ProtocolConnection, Any], None]]
type LayersGetter = Callable[[ProtocolConnection], list[AbstractProtocol]]


class ProtocolServer:
    connectionType: type[ProtocolConnection] = ProtocolConnection

    sock: socket
    layersGetter: LayersGetter
    onConnection: OnConnectionListener
    closed: bool
    connections: list[ProtocolConnection]

    def __init__(self, address: tuple[str, int], layersGetter: LayersGetter,
                 onConnection: OnConnectionListener):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.layersGetter = layersGetter
        self.onConnection = onConnection
        self.closed = True
        self.connections = []

        self.sock.bind(address)

    def listen(self, maxAmount: int | None = None):
        if maxAmount is None:
            self.sock.listen()
        else:
            self.sock.listen(maxAmount)
        self.closed = False
        i = 0
        while (i < maxAmount) if maxAmount is not None else True:
            # print("Accept...")
            conn, addr = self.sock.accept()
            i += 1
            # I hope that the lambda will know the changed onData value
            connection: ProtocolConnection = self.connectionType(addr, [], neverCall, conn)
            for protocol in self.layersGetter(connection):
                connection.addProtocol(protocol)
            if not self.onConnectionInner(connection):
                continue
            connection.onData = self.onConnection(connection)
            connection.onCloseListeners.append(self.__onConnectionClose)
            self.connections.append(connection)
            connection.startRecv()

    def __onConnectionClose(self, connection: ProtocolConnection, cause: Exception | None) -> None:
        if connection not in self.connections:
            return
        self.connections.remove(connection)

    def onConnectionInner(self, conn: ProtocolConnection) -> bool:
        return True  # Rewritten by subclasses, returns whether the connection should be kept

    def close(self):
        if self.closed:
            return
        self.sock.close()
        self.closed = True
