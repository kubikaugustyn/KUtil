#  -*- coding: utf-8 -*-
__author__ = "kubik.augustyn@post.cz"

from typing import Any, Optional

from kutil.buffer.ByteBuffer import ByteBuffer, OutOfBoundsReadError, OutOfBoundsUndoError
from kutil.protocol.AbstractProtocol import AbstractProtocol, StopUnpacking, NeedMoreDataError
from kutil.protocol.ProtocolConnection import ProtocolEstablishedConnection, OnEstablishedListener
from kutil.protocol.HTTPConnection import OnHTTPDataListener, HTTPProtocol
from kutil.protocol.TCPConnection import TCPProtocol
from kutil.protocol.TLS.certificate_verifier import verifyPeerCertificates
from kutil.protocol.TLS.AlertCause import AlertCause
from kutil.protocol.TLS.RawTLSRecord import TLSRecordType, RawTLSRecord, \
    RawTLSRecordNeedMoreDataError
from kutil.protocol.TLS.ConnectionState import ConnectionState, ConnectionStateType, TLSVersion
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
            record = records.HandshakeRecord(state)
        elif contentType == TLSRecordType.ChangeCipherSpec:
            record = records.ChangeCipherSpecRecord(state)
        elif contentType == TLSRecordType.Heartbeat:
            record = records.RawTLSRecord(TLSRecordType.Heartbeat,
                                          state)  # records.HeartbeatRecord(state)
        else:
            raise NotImplementedError(f"Unknown record type {contentType.name}")

        # On AlertCause error send that error and terminate the connection with it
        try:
            record.read(buff)
        except AlertCause as e:
            self.connection.sendAlert(e, False)
            self.connection.close(e)
        except RawTLSRecordNeedMoreDataError as e:
            # ONLY require more data when the raw TLS record parse requires it
            # Not if I accidentally do an out-of-bounds read
            raise NeedMoreDataError from e
        except (OutOfBoundsUndoError, OutOfBoundsReadError) as e:
            cause = AlertCause(50)
            self.connection.sendAlert(cause, False)
            self.connection.close(cause)

        # print("RX data:", record, "as", buff.export())

        return record

    def unpackSubProtocol(self, buff: ByteBuffer) -> ByteBuffer:
        record = self.unpackData(buff)
        if not isinstance(record, records.ApplicationRecord):
            # print("Unpack sub protocol failed - TLS non-application data")
            raise StopUnpacking
        return ByteBuffer(record.payload)

    def packData(self, data: RawTLSRecord, buff: ByteBuffer):
        data.write(buff)
        # print("TX data:", data, "as", buff.export())

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

        self.state.setServerDomainName(address[0])
        self._sendHello()

    def onDataInner(self, data: Any, stoppedUnpacking: bool = False,
                    layer: Optional[AbstractProtocol] = None) -> bool | Any:
        if not stoppedUnpacking:
            return True
        assert isinstance(layer, TLSProtocol)
        assert isinstance(data, RawTLSRecord)

        if isinstance(data, records.AlertRecord):
            # TODO Deal with the non-fatal errors too
            if data.isFatal:
                print("Other peer sent an error while in state:", self.state.state)
                self.close(AlertCause(data.code))
                return False
        try:
            # https://upload.wikimedia.org/wikipedia/commons/d/d3/Full_TLS_1.2_Handshake.svg
            if self.state.state in {ConnectionStateType.CLIENT_HELLO_SENT,
                                    ConnectionStateType.SERVER_HELLO_RECEIVED}:
                assert isinstance(data, records.HandshakeRecord)

                for msg in data.messages:
                    if msg.messageType == MessageType.ServerHello:
                        assert self.state.state == ConnectionStateType.CLIENT_HELLO_SENT
                        self.state.state = ConnectionStateType.SERVER_HELLO_RECEIVED
                        assert isinstance(msg, messages.ServerHelloMessage)
                        self._handleServerHello(msg)
                    elif msg.messageType == MessageType.ServerHelloDone:
                        assert self.state.state == ConnectionStateType.SERVER_HELLO_RECEIVED
                        self.state.state = ConnectionStateType.SERVER_HELLO_DONE
                        self._handleServerHelloDone()
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
            self.sendAlert(e, False)
        except (OutOfBoundsReadError, OutOfBoundsUndoError) as e:
            self.sendAlert(AlertCause(80), False)
        except Exception as e:
            self.sendAlert(AlertCause(80), False, forceNoClose=True)
            self.close(e)

        return False

    def _sendHello(self) -> None:
        assert self.state.state == ConnectionStateType.INIT
        hello = records.HandshakeRecord(self.state)

        extensions = [
            # TODO Come up with actually useful extensions
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
                                          extensions=extensions,
                                          sessionID=self.state.sessionID)
        hello.messages.append(msg)
        self.sendData(hello, 1)

        self.state.state = ConnectionStateType.CLIENT_HELLO_SENT

    # https://datatracker.ietf.org/doc/html/rfc8446#section-4.1.3
    def _handleServerHello(self, hello: messages.ServerHelloMessage) -> None:
        # Handle the random field downgrading
        if (self.state.version is TLSVersion.TLS_1_3 and
                hello.protocolVersion is not TLSVersion.TLS_1_3):
            if hello.protocolVersion is TLSVersion.TLS_1_2:
                if not hello.random.endswith(b'DOWNGRD\x01'):
                    raise AlertCause(47)
            elif hello.protocolVersion <= TLSVersion.TLS_1_1:
                if not hello.random.endswith(b'DOWNGRD\x00'):
                    raise AlertCause(47)
        elif (self.state.version is TLSVersion.TLS_1_2 and
              hello.protocolVersion <= TLSVersion.TLS_1_1):
            if hello.random.endswith(b'DOWNGRD\x01'):
                raise AlertCause(47)
        assert hello.protocolVersion <= TLSVersion.TLS_1_3, \
            f"Unsupported TLS version {hello.protocolVersion.name}"
        # Handle cipher suite mismatch
        if hello.cipherSuite not in self.state.supportedCipherSuites:
            raise AlertCause(47)
        # Handle the session ID echo mismatch
        # TODO Find out why the session IDs mismatch
        # if self.state.sessionID != hello.sessionIDEcho:
        #     print(self.state.sessionID)
        #     print(hello.sessionIDEcho)
        #     raise AlertCause(47)

        self.state.version = hello.protocolVersion  # Perform the downgrade/upgrade
        self.state.pendingCipher = hello.cipherSuite  # Select the cipher

        # TODO Handle ServerHello extensions

    def _handleServerHelloDone(self) -> None:
        for msg in self._serverHelloMessages:
            if isinstance(msg, messages.CertificateMessage):
                self.state.addCertificates(msg.certificates)
        if len(self.state.certificates) == 0:
            # Certificate is required!
            # TODO Only require the certificate when the encryption requires it
            if self.state.version is TLSVersion.TLS_1_3:
                raise AlertCause(116)
            elif self.state.version is TLSVersion.SSL_3_0:
                raise AlertCause(41)
            else:
                raise AlertCause(40)

        error, cause = verifyPeerCertificates(self.state)
        if error != -1:
            raise AlertCause(error) from cause

        self._sendKey()

    def _sendKey(self) -> None:
        assert self.state.state == ConnectionStateType.SERVER_HELLO_DONE

        key = records.HandshakeRecord(self.state, [self._prepareClientKeyExchangeMessage()])
        changeCipher = records.ChangeCipherSpecRecord(self.state)
        # TODO Send finished
        # finished = records.HandshakeRecord(self.state,
        #                                    [messages.FinishedMessage(self.state.sizeMAC)])

        self.sendData(key, 1)
        self.state.state = ConnectionStateType.KEY_SENT

        self.sendData(changeCipher, 1)
        self.state.state = ConnectionStateType.CHANGE_CIPHER_SENT
        self.state.switchToPendingCipher(unsafe_allow_no_cipher=False)

        # self.sendData(finished, 1)
        # self.state.state = ConnectionStateType.FINISHED_SENT

        # https://github.com/tlsfuzzer/tlslite-ng/blob/master/tlslite/constants.py
        # https://github.com/tlsfuzzer/tlslite-ng/blob/master/tlslite/messages.py
        # https://github.com/tlsfuzzer/tlslite-ng/blob/master/tlslite/utils/codec.py

    def _prepareClientKeyExchangeMessage(self) -> messages.ClientKeyExchangeMessage:
        msg = messages.ClientKeyExchangeMessage(self.state.pendingCipher, self.state.version)
        # TODO Valid key exchange message
        msg.ecdh_Yc = b''

        return msg

    def sendAlert(self, cause: AlertCause, warning: bool, forceNoClose: bool = False) -> None:
        alert = records.AlertRecord(self.state, cause.code, 1 if warning else 2)
        self.sendData(alert, 1)
        if not warning and not forceNoClose:
            self.close(cause)
