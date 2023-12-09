#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import Thread
from typing import Callable, Any
from socket import socket, AF_INET, SOCK_STREAM
from kutil.protocol.AbstractProtocol import AbstractProtocol, NeedMoreDataError
from kutil.buffer.ByteBuffer import ByteBuffer

type OnDataListener = Callable[[Any], None]


class ProtocolConnection:
    """An event-based connection, doesn't block any thread (creates one thread for its needs)"""
    layers: list[AbstractProtocol]
    onData: OnDataListener
    receiverThread: Thread
    closed: bool
    sock: socket

    def __init__(self, address: tuple[str, int], layers: list[AbstractProtocol], onData: OnDataListener,
                 sock: socket | None = None):
        self.layers = layers
        self.onData = onData
        self.receiverThread = Thread(target=self.receive)
        self.closed = False
        if sock is None:  # If we are a client connection
            self.connect(address)
            self.startRecv()
        else:  # If we are a server's client connection handler
            self.sock = sock
            # Note that you need to manually call startRecv()
        self.init()

    def init(self):
        pass  # Subclasses will overwrite this

    def onDataInner(self, data: Any) -> bool | Any:
        return True  # Subclasses will overwrite this, return whether you want to call the onData handler

    def startRecv(self):
        self.receiverThread.start()

    def connect(self, address: tuple[str, int]):
        self.sock = socket(AF_INET, SOCK_STREAM)
        self.sock.connect(address)

    def addProtocol(self, protocol: AbstractProtocol):
        assert protocol not in self.layers, "Protocol already added"
        assert isinstance(protocol, AbstractProtocol)
        self.layers.append(protocol)

    def removeProtocol(self, protocol: AbstractProtocol):
        """Removes a protocol and it's contained protocols"""
        self.layers = self.layers[:self.layers.index(protocol)]

    def close(self):
        self.closed = True
        # try:
        self.sock.close()
        # except OSError:
        #     pass

    def receive(self):
        buff: ByteBuffer = ByteBuffer()
        try:
            while not self.closed:
                data = self.sock.recv(1024 * 1024)
                if not len(data):
                    self.close()
                    return
                buff.write(data)
                buff.resetPointer()
                if self.tryReceivedData(buff):
                    buff.reset()
        except OSError:
            self.close()
        except ConnectionAbortedError | ConnectionError | ConnectionResetError:
            self.close()

    def tryReceivedData(self, buff: ByteBuffer) -> bool:
        try:
            for layer in self.layers[:-1]:
                buff = layer.unpackSubProtocol(buff)
            data: Any = self.layers[-1].unpackData(buff)
            dataInner: bool | Any = self.ownConnection.onDataInner(data)
            isBool: bool = isinstance(dataInner, bool)
            if not isBool or dataInner is True:
                if not isBool:
                    # print(data, "-->", dataInner)
                    data = dataInner
                # print("On data:", data, "with inner:", dataInner)
                self.onData(data)
            return True
        except NeedMoreDataError:
            print("Need more data!")
            print(buff.data)
            return False

    def sendData(self, data: Any) -> bool:
        buff: ByteBuffer = ByteBuffer()
        for i in range(len(self.layers)):
            if i == 0:
                self.layers[-1].packData(data, buff)
            else:
                self.layers[len(self.layers) - 1 - i].packSubProtocol(buff)
        try:
            self.sock.sendall(buff.export())
        except OSError:
            self.close()
            return False
        return True

    @property
    def ownConnection(self):
        """Returns self (usually). Used to split the work across different connection protocol
         classes when the protocols change (e.g. HTTP --> WebSocket)"""
        return self  # Maybe the connection changed (protocol switch)
