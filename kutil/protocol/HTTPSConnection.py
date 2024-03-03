#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Any

from kutil.protocol.TLS.AlertCause import AlertCause

from kutil.protocol.TLS.RawTLSRecord import TLSRecordType, RawTLSRecord

from kutil.protocol.TLS.ConnectionState import ConnectionState, ConnectionStateType, TLSVersion

from kutil.buffer.ByteBuffer import ByteBuffer
from kutil.protocol.AbstractProtocol import AbstractProtocol, StopUnpacking
from kutil.protocol.ProtocolConnection import ProtocolEstablishedConnection, OnEstablishedListener
from kutil.protocol.TCPConnection import TCPProtocol
from kutil.protocol.HTTPConnection import OnHTTPDataListener, HTTPProtocol
from kutil.protocol.TLS import records, messages
from kutil.protocol.TLS.records import Message, MessageType
from kutil.protocol.TLS.extensions import Extension, ExtensionType, SupportedGroupsExtension, \
    NamedGroup, KeyShareExtension


class TLSProtocol(AbstractProtocol):
    name = "TLSProtocol"

    def unpackData(self, buff: ByteBuffer) -> RawTLSRecord:
        assert isinstance(self.connection, HTTPSConnection)
        contentType: TLSRecordType = RawTLSRecord.readContentType(buff, True)
        state = self.connection.state

        if contentType == TLSRecordType.Application:
            record = records.ApplicationRecord(state)
        elif contentType == TLSRecordType.Alert:
            record = records.AlertRecord(state)
        elif contentType == TLSRecordType.Handshake:
            record = records.AlertRecord(state)
        elif contentType == TLSRecordType.ChangeCipherSpec:
            record = records.AlertRecord(state)
        elif contentType == TLSRecordType.Heartbeat:
            record = records.AlertRecord(state)
        else:
            raise NotImplementedError(f"Unknown record type {contentType.name}")
        # On AlertCause error send that error and terminate the connection with it
        try:
            record.read(buff)
        except AlertCause as e:
            self.connection.sendAlert(e, False)
            self.connection.close(e)
        return record

    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        record = self.unpackData(buff)
        if not isinstance(record, records.ApplicationRecord):
            raise StopUnpacking
        return ByteBuffer(record.payload)

    def packData(self, data: RawTLSRecord, buff: ByteBuffer):
        data.write(buff)

    def packSubProtocol(self, buff: ByteBuffer):
        assert isinstance(self.connection, HTTPSConnection)
        record = records.ApplicationRecord(self.connection.state, buff.export())
        buff.reset()
        record.write(buff)


class HTTPSConnection(ProtocolEstablishedConnection):
    state: ConnectionState
    _serverHelloMessages: list[Message]

    def __init__(self, address: tuple[str, int], onData: OnHTTPDataListener,
                 onEstablished: OnEstablishedListener):
        self.state = ConnectionState()
        self._serverHelloMessages = []
        super().__init__(address, [TCPProtocol(self), TLSProtocol(self), HTTPProtocol(self)],
                         onData, onEstablished)

        self._sendHello()

    def onDataInner(self, data: Any, stoppedUnpacking: bool = False,
                    layer: AbstractProtocol | None = None) -> bool | Any:
        if not stoppedUnpacking:
            return True
        assert isinstance(layer, TLSProtocol)
        assert isinstance(data, RawTLSRecord)

        if isinstance(data, records.AlertRecord):
            # TODO Deal with the non-fatal errors too
            if data.isFatal:
                print(self.state.state)
                self.close(AlertCause(data.code))
                return False
        try:
            # https://upload.wikimedia.org/wikipedia/commons/d/d3/Full_TLS_1.2_Handshake.svg
            if self.state.state == ConnectionStateType.CLIENT_HELLO_SENT:
                assert isinstance(data, records.HandshakeRecord)
                for msg in data.messages:
                    if msg.messageType == MessageType.ServerHello:
                        assert self.state.state == ConnectionStateType.CLIENT_HELLO_SENT
                        self.state.state = ConnectionStateType.SERVER_HELLO_RECEIVED
                    elif msg.messageType == MessageType.ServerHelloDone:
                        assert self.state.state == ConnectionStateType.SERVER_HELLO_RECEIVED
                        self.state.state = ConnectionStateType.SERVER_HELLO_DONE
                        self._sendKey()
                        break
                    else:
                        if self.state.state != ConnectionStateType.SERVER_HELLO_RECEIVED:
                            continue
                        self._serverHelloMessages.append(msg)
            elif self.state.state == ConnectionStateType.FINISHED_SENT:
                assert isinstance(data, records.ChangeCipherSpecRecord)
                self.state.state = ConnectionStateType.CHANGE_CIPHER_RECEIVED
            elif self.state.state == ConnectionStateType.CHANGE_CIPHER_RECEIVED:
                assert isinstance(data, records.HandshakeRecord)
                assert len(data.messages) == 1
                msg = data.messages[0]
                assert msg.messageType == MessageType.Finished
                self.state.state = ConnectionStateType.APPLICATION_DATA
            else:
                raise NotImplementedError(f"Unknown connection state {self.state.state.name}")
        except AlertCause as e:
            self.sendData(records.AlertRecord(self.state, e.code, 2))
            self.close(e)
        except Exception as e:
            self.sendData(records.AlertRecord(self.state, 80, 2))
            try:
                # Not clean code :-/
                raise AlertCause(80) from e
            except AlertCause as ex:
                self.close(ex)

        return False

    def _sendHello(self) -> None:
        print("Send hello")
        assert self.state.state == ConnectionStateType.INIT
        hello = records.HandshakeRecord(self.state)

        extensions = [
            # https://datatracker.ietf.org/doc/html/rfc6520#autoid-4
            Extension(ExtensionType.HEARTBEAT, b'\x01'),
            # https://datatracker.ietf.org/doc/html/rfc8446#section-4.2.2
            Extension(ExtensionType.COOKIE, b'\xff'),
            SupportedGroupsExtension(self.state.supportedGroups),
            KeyShareExtension(self.state.clientSharedKeys)
        ]
        # https://datatracker.ietf.org/doc/html/rfc8446#section-4.1.2
        msg = messages.ClientHelloMessage(TLSVersion.TLS_1_2,
                                          cipherSuites=self.state.supportedCipherSuites,
                                          compressionMethods=b'\x00',
                                          extensions=extensions)
        hello.messages.append(msg)
        self.sendData(hello, 1)
        print("Sent hello")

        self.state.state = ConnectionStateType.CLIENT_HELLO_SENT

    def _sendKey(self) -> None:
        assert self.state.state == ConnectionStateType.SERVER_HELLO_DONE

        # TODO Valid key
        key = records.HandshakeRecord(self.state, [Message(MessageType.ClientKeyExchange, b'')])
        changeCipher = records.ChangeCipherSpecRecord(self.state)
        finished = records.HandshakeRecord(self.state, [Message(MessageType.Finished, b'')])

        self.sendData(key, 1)
        self.state.state = ConnectionStateType.KEY_SENT
        self.sendData(changeCipher, 1)
        self.state.state = ConnectionStateType.CHANGE_CIPHER_SENT
        self.sendData(finished, 1)
        self.state.state = ConnectionStateType.FINISHED_SENT

    def sendAlert(self, cause: AlertCause, warning: bool) -> None:
        alert = records.AlertRecord(self.state, cause.code, 1 if warning else 2)
