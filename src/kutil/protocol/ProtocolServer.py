#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from socket import socket, AF_INET, SOCK_STREAM
from typing import Callable, Any
from kutil.protocol.AbstractProtocol import AbstractProtocol
from kutil.protocol.ProtocolConnection import ProtocolConnection

type OnConnectionListener = Callable[[ProtocolConnection], Callable[[Any], None]]
type LayersGetter = Callable[[ProtocolConnection], list[AbstractProtocol]]


class ProtocolServer:
    connectionType: type[ProtocolConnection] = ProtocolConnection

    sock: socket
    layersGetter: LayersGetter
    onConnection: OnConnectionListener

    def __init__(self, address: tuple[str, int], layersGetter: LayersGetter, onConnection: OnConnectionListener):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.layersGetter = layersGetter
        self.onConnection = onConnection

        self.sock.bind(address)

    def listen(self, maxAmount: int | None = None):
        if maxAmount is None:
            self.sock.listen()
        else:
            self.sock.listen(maxAmount)
        i = 0
        while (i < maxAmount) if maxAmount is not None else True:
            # print("Accept...")
            conn, addr = self.sock.accept()
            i += 1
            # I hope that the lambda will know the changed onData value
            connection: ProtocolConnection = self.connectionType(addr, [], None, conn)
            for protocol in self.layersGetter(connection):
                connection.addProtocol(protocol)
            if not self.onConnectionInner(connection):
                continue
            connection.onData = self.onConnection(connection)
            connection.startRecv()

    def onConnectionInner(self, conn: ProtocolConnection) -> bool:
        return True  # Rewritten by subclasses, returns whether the connection should be kept

    def close(self):
        self.sock.close()
