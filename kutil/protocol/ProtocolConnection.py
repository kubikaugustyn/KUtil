#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from threading import Thread
from typing import Callable, Any, Optional
from socket import socket, AF_INET, SOCK_STREAM
from kutil.protocol.AbstractProtocol import AbstractProtocol, NeedMoreDataError, StopUnpacking
from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.buffer.MemoryByteBuffer import MemoryByteBuffer

type OnDataListener = Callable[[ProtocolConnection, Any], None]
type OnEstablishedListener = Callable[[ProtocolEstablishedConnection], None]
type OnCloseListener = Callable[[ProtocolConnection, Optional[Exception]], None]


class ConnectionClosed(Exception):
    pass


class ProtocolConnection:
    """An event-based connection, doesn't block any thread (creates one thread for its needs)"""
    layers: list[AbstractProtocol]
    onData: OnDataListener
    onCloseListeners: list[OnCloseListener]
    receiverThread: Thread
    closed: bool
    sock: socket

    def __init__(self, address: tuple[str, int], layers: list[AbstractProtocol],
                 onData: OnDataListener, sock: Optional[socket] = None,
                 onClose: Optional[list[OnCloseListener]] = None):
        self.layers = layers
        self.onData = onData
        self.onCloseListeners = onClose if onClose is not None else []
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

    def onDataInner(self, data: Any, stoppedUnpacking: bool = False,
                    layer: Optional[AbstractProtocol] = None) -> bool | Any:
        return True  # Subclasses will overwrite this, return whether you want to call the onData handler

    def startRecv(self):
        self.receiverThread.start()

    def connect(self, address: tuple[str, int]):
        self.sock = socket(AF_INET, SOCK_STREAM)
        try:
            self.sock.connect(address)
        except TimeoutError as e:
            self.close(e)

    def addProtocol(self, protocol: AbstractProtocol):
        assert protocol not in self.layers, "Protocol already added"
        assert isinstance(protocol, AbstractProtocol)
        self.layers.append(protocol)

    def removeProtocol(self, protocol: AbstractProtocol):
        """Removes a protocol and it's contained protocols"""
        self.layers = self.layers[:self.layers.index(protocol)]

    def close(self, cause: Optional[Exception] = None):
        self.closed = True
        # try:
        self.sock.close()
        # except OSError:
        #     pass

        for listener in self.onCloseListeners:
            listener(self, cause)

    def receive(self):
        buff: ByteBuffer = MemoryByteBuffer()
        try:
            while not self.closed:
                data = self.sock.recv(1024 * 1024)
                if not len(data):
                    self.close(ConnectionClosed())
                    return
                buff.write(data)
                buff.resetPointer()
                while buff.has(1) and not self.closed:
                    # Read all the packets that are packed tightly one after another
                    # print(f"Pointer: {buff.pointer}, length: {len(buff.export())}")
                    # print("Data:", buff.export())
                    if self.tryReceivedData(buff):
                        # print(f"Pointer after read: {buff.pointer}")
                        buff.resetBeforePointer()
                        # print(f"Length: {len(buff.export())}")
                    else:
                        # print("Not successful")
                        break
        except OSError as e:
            self.close(e)
        except (ConnectionAbortedError, ConnectionError, ConnectionResetError) as e:
            self.close(e)

    def tryReceivedData(self, buff: ByteBuffer) -> bool:
        """
        Tries to parse and handle the received data,
        returning whether it succeeded (True) or needs more data (False)
        :param buff: The source buffer
        :return: succeeded (True) or needs more data (False)
        """
        if self.closed:
            # If the connection is closed, don't even try
            return True

        layerI: int = -1
        lastBuff: ByteBuffer = buff.copy()
        try:
            for layerI in range(len(self.layers) - 1):
                buff = self.layers[layerI].unpackSubProtocol(buff)
                lastBuff = buff.copy()
                if self.closed:
                    # If the sub-protocol unpacker closed the connection, cancel the onData handler
                    return True
            data: Any = self.layers[-1].unpackData(buff)
            if self.closed:
                # If the data unpacker closed the connection, cancel the onData handler
                return True
            dataInner: bool | Any = self.ownConnection.onDataInner(data, False)
            isBool: bool = isinstance(dataInner, bool)
            if not isBool or dataInner is True:
                if not isBool:
                    # print(data, "-->", dataInner)
                    data = dataInner
                # print("On data:", data, "with inner:", dataInner)
                self.onData(self, data)
            return True
        except NeedMoreDataError:
            # print("Need more data!")
            # print(buff.export())
            return False
        except StopUnpacking:
            # Basically, this error means that at the current layer we should stop unpacking the
            # protocol layers and pass the data directly to the connection to be processed and never
            # passed to the last protocol, because it's a not-final-layer data packet.
            # print("Stop unpacking!")
            data: Any = self.layers[layerI].unpackData(lastBuff)
            dataInner: bool | Any = self.onDataInner(data, True, self.layers[layerI])
            assert isinstance(dataInner, bool) and dataInner is False
            return True

    def sendData(self, data: Any, beginAtLayer: int = -1) -> bool:
        if beginAtLayer == -1:
            beginAtLayer = len(self.layers) - 1
        buff: ByteBuffer = MemoryByteBuffer()
        for i in range(beginAtLayer, 0, -1):
            if i == beginAtLayer:
                self.layers[beginAtLayer].packData(data, buff)
            else:
                self.layers[i].packSubProtocol(buff)
        try:
            self.sock.sendall(buff.export())
        except OSError as e:
            self.close(e)
            return False
        return True

    @property
    def ownConnection(self):
        """Returns self (usually). Used to split the work across different connection protocol
         classes when the protocols change (e.g., HTTP --> WebSocket)"""
        return self  # Maybe the connection changed (protocol switch)


class ProtocolEstablishedConnection(ProtocolConnection):
    _established: bool
    onEstablished: OnEstablishedListener

    def __init__(self, address: tuple[str, int], layers: list[AbstractProtocol],
                 onData: OnDataListener, onEstablished: OnEstablishedListener,
                 sock: Optional[socket] = None, onClose: Optional[list[OnCloseListener]] = None):
        self._established = False
        self.onEstablished = onEstablished
        super().__init__(address, layers, onData, sock, onClose)

    def markEstablished(self):
        if self._established:
            raise ValueError("Cannot re-establish an already established connection")
        self._established = True
        self.onEstablished(self)
