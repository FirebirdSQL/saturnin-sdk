#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/service/echo/service.py
# DESCRIPTION:    Sample ECHO service (classic version)
# CREATED:        6.3.2019
#
# The contents of this file are subject to the MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Copyright (c) 2019 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin SDK examples - Sample ECHO service (classic version)

ECHO service sends data frames back to the sender.

Supported requests:

    :ECHO:            Simple echo, immediately sends unaltered data frames.
    :ECHO_ROMAN:      Simple echo, sends data frames filtered through ROMAN service.
    :ECHO_MORE:       Sends DATA message for each request data frame using MORE flag.
    :ECHO_STATE:      Sends DATA message for each request data frame using STATE/FINISHED.
    :ECHO_SYNC:       Sends DATA message for each request data frame using ACK handshake
                      managed by service.
    :ECHO_DATA_MORE:  Sends back up to 3 DATA messages using MORE flag.
    :ECHO_DATA_SYNC:  Sends back up to 3 DATA messages using ACK handshake managed by client.
"""

from typing import List
from uuid import UUID, uuid1
from struct import pack, unpack # pylint: disable=E0611
from saturnin.service.echo.api import EchoRequest, EchoError, Protocol, PROTOCOL_UID, \
     SERVICE_UID
from saturnin.service.roman import api as roman_api
from saturnin.service.roman.client import RomanClient
from saturnin.sdk.base import BaseChannel, BaseService, ServiceError, InvalidMessageError, \
     DealerChannel
from saturnin.sdk.classic import SimpleServiceImpl
from saturnin.sdk.fbsp import Session, ServiceMessagelHandler, \
     MsgType, Flag, State, ErrorCode, HelloMessage, CancelMessage, DataMessage, \
     ReplyMessage, RequestMessage

# Classes

class EchoMessageHandler(ServiceMessagelHandler):
    """Message handler for ECHO service."""
    def __init__(self, chn: BaseChannel, service):
        super().__init__(chn, service)
        # We use ECHO protocol instead raw FBSP
        self.protocol = Protocol()
        # Our message handlers
        self.handlers.update({(MsgType.REQUEST, EchoRequest.ECHO): self.h_echo,
                              (MsgType.REQUEST, EchoRequest.ECHO_ROMAN): self.h_echo_roman,
                              (MsgType.REQUEST, EchoRequest.ECHO_MORE): self.h_echo_more,
                              (MsgType.REQUEST, EchoRequest.ECHO_STATE): self.h_echo_state,
                              (MsgType.REQUEST, EchoRequest.ECHO_SYNC): self.h_echo_sync,
                              (MsgType.REQUEST, EchoRequest.ECHO_DATA_MORE):
                              self.h_echo_data_more,
                              (MsgType.REQUEST, EchoRequest.ECHO_DATA_SYNC):
                              self.h_echo_data_sync,
                             })
        # Optional ROMAN client
        self.roman_cli: RomanClient = None
    def on_invalid_message(self, session: Session, exc: InvalidMessageError):
        "Invalid Message event."
        raise ServiceError("Invalid message") from exc
    def on_invalid_greeting(self, exc: InvalidMessageError):
        "Invalid Greeting event."
        raise ServiceError("Invalid Greeting") from exc
    def on_dispatch_error(self, session: Session, exc: Exception):
        "Exception unhandled by `dispatch()`."
        raise ServiceError("Unhandled exception") from exc
    def h_hello(self, session: Session, msg: HelloMessage):
        "HELLO message handler. Sends WELCOME message back to the client."
        super().h_hello(session, msg)
        welcome = self.protocol.create_welcome_reply(msg)
        welcome.peer.CopyFrom(self.impl.desc)
        self.send(welcome, session)
    def h_cancel(self, session: Session, msg: CancelMessage):
        """Handle CANCEL message.

TODO: Properly handle CANCEL request. Right now we ignore it and do nothing.
"""
    def on_ack_reply(self, session: Session, msg: ReplyMessage):
        """REPLY message handler."""
        # If the message is ACK-REPLY to ECHO_SYNC request, we will start sending DATA to
        # the client.
        if msg.request_code == EchoRequest.ECHO_SYNC:
            req_msg = session.get_request(msg.token)
            msg_data = self.protocol.create_data_for(req_msg)
            msg_data.data.append(req_msg.data.pop(0))
            msg_data.type_data = session.get_handle(req_msg)
            if req_msg.data:
                msg_data.set_flag(Flag.ACK_REQ)
            else:
                session.request_done(req_msg)
            self.send(msg_data, session)
    def h_data(self, session: Session, msg: DataMessage):
        """DATA message handler.

There are three cases when this handler is called:

    1.  ACK_REPLY for ECHO_SYNC
    2.  Data package for ECHO_DATA_MORE
    3.  Data package for ECHO_DATA_SYNC

All messages must have a valid handle in `type_data`.
"""
        #pylint: disable=R0912,R0915,R1702,C0301
        if session.is_handle_valid(msg.type_data):
            req_msg = session.get_request(handle=msg.type_data)
            if req_msg.request_code == EchoRequest.ECHO_SYNC:
                if msg.has_ack_reply():
                    msg_data = self.protocol.create_data_for(req_msg)
                    msg_data.type_data = msg.type_data
                    msg_data.data.append(req_msg.data.pop(0))
                    if req_msg.data:
                        msg_data.set_flag(Flag.ACK_REQ)
                    else:
                        session.request_done(req_msg)
                    self.send(msg_data, session)
                else: # regular DATA without ACK_REPLY is a client error
                    err = self.protocol.create_error_for(req_msg, ErrorCode.BAD_REQUEST)
                    errd = err.add_error()
                    errd.code = EchoError.PROTOCOL_VIOLATION
                    errd.description = "Expected DATA with ACK_REPLY"
                    self.send(err, session)
            elif req_msg.request_code == EchoRequest.ECHO_DATA_MORE:
                if len(req_msg.data) == 3:
                    # too many data messages
                    err = self.protocol.create_error_for(req_msg, ErrorCode.BAD_REQUEST)
                    errd = err.add_error()
                    errd.code = EchoError.PROTOCOL_VIOLATION
                    errd.description = "Too many DATA messages"
                    self.send(err, session)
                    session.request_done(req_msg)
                req_msg.data.append(msg)
                if not msg.has_more():
                    # That was last one, send them back all at once
                    msg_data = self.protocol.create_data_for(req_msg)
                    while req_msg.data:
                        pkg = req_msg.data.pop(0)
                        msg_data.data.extend(pkg.data)
                        if req_msg.data:
                            msg_data.set_flag(Flag.MORE)
                        else:
                            msg_data.clear_flag(Flag.MORE)
                        self.send(msg_data, session)
                        msg_data.data.clear()
                    session.request_done(req_msg)
            elif req_msg.request_code == EchoRequest.ECHO_DATA_SYNC:
                req_msg.data.append(msg)
                if msg.has_ack_req():
                    if len(req_msg.data) == req_msg.expect:
                        # Error, the last one should not have ACK_REQ
                        err = self.protocol.create_error_for(req_msg, ErrorCode.BAD_REQUEST)
                        errd = err.add_error()
                        errd.code = EchoError.PROTOCOL_VIOLATION
                        errd.description = "Last DATA message must not have ACK_REQ flag"
                        self.send(err, session)
                        session.request_done(req_msg)
                    else:
                        self.send(self.protocol.create_ack_reply(msg), session)
                else:
                    # this should be the last one
                    if len(req_msg.data) == req_msg.expect:
                        # That was last one, send them back all at once
                        msg_data = self.protocol.create_data_for(req_msg)
                        while req_msg.data:
                            pkg = req_msg.data.pop(0)
                            msg_data.data.extend(pkg.data)
                            if req_msg.data:
                                msg_data.set_flag(Flag.MORE)
                            else:
                                msg_data.clear_flag(Flag.MORE)
                            self.send(msg_data, session)
                            msg_data.data.clear()
                        session.request_done(req_msg)
                    else:
                        # Did we miss a DATA message?
                        err = self.protocol.create_error_for(req_msg, ErrorCode.BAD_REQUEST)
                        errd = err.add_error()
                        errd.code = EchoError.PROTOCOL_VIOLATION
                        errd.description = f"Announced {req_msg.expect} messages, but only {len(req_msg.data)} received"
                        self.send(err, session)
                        session.request_done(req_msg)
        else:
            err = self.protocol.create_error_for(session.greeting, ErrorCode.BAD_REQUEST)
            errd = err.add_error()
            errd.code = EchoError.PROTOCOL_VIOLATION
            errd.description = "Invalid DATA.type_data content"
            self.send(err, session)
    def h_echo(self, session: Session, msg: RequestMessage):
        "ECHO request handler."
        session.note_request(msg)
        reply = self.protocol.create_reply_for(msg)
        reply.data.extend(list(msg.data)) # copy data
        self.send(reply, session)
        session.request_done(msg)
    def h_echo_roman(self, session: Session, msg: RequestMessage):
        "ECHO_ROMAN request handler."
        session.note_request(msg)
        reply = self.protocol.create_reply_for(msg)
        #
        if self.roman_cli:
            # copy data from ROMAN's reply
            try:
                reply.data.extend(list(self.roman_cli.roman(*msg.data, timeout=1000)))
            except TimeoutError as exc:
                reply = self.protocol.create_error_for(msg, ErrorCode.REQUEST_TIMEOUT)
                err = reply.add_error()
                err.description = str(exc)
            self.send(reply, session)
        else:
            # ROMAN service not available
            err_msg = self.protocol.create_error_for(msg, ErrorCode.SERVICE_UNAVAILABLE)
            err = err_msg.add_error()
            err.description = "ROMAN service not available"
            self.send(err_msg, session)
        session.request_done(msg)
    def h_echo_more(self, session: Session, msg: RequestMessage):
        "ECHO_MORE request handler."
        session.note_request(msg)
        reply = self.protocol.create_reply_for(msg)
        self.send(reply, session)
        data_msg = self.protocol.create_data_for(msg)
        while msg.data:
            data_msg.data.append(msg.data.pop(0))
            if msg.data:
                data_msg.set_flag(Flag.MORE)
            else:
                data_msg.clear_flag(Flag.MORE)
            self.send(data_msg, session)
            data_msg.data.clear()
        session.request_done(msg.token)
    def h_echo_state(self, session: Session, msg: RequestMessage):
        "ECHO_STATE request handler."
        session.note_request(msg)
        reply = self.protocol.create_reply_for(msg)
        self.send(reply, session)
        data_msg = self.protocol.create_data_for(msg)
        while msg.data:
            data_msg.data.append(msg.data.pop(0))
            self.send(data_msg, session)
            data_msg.data.clear()
        state = self.protocol.create_state_for(msg, State.FINISHED)
        self.send(state, session)
        session.request_done(msg.token)
    def h_echo_sync(self, session: Session, msg: RequestMessage):
        "Handle ECHO_SYNC message."
        session.note_request(msg)
        reply = self.protocol.create_reply_for(msg)
        reply.set_flag(Flag.ACK_REQ)
        self.send(reply, session)
    def h_echo_data_more(self, session: Session, msg: RequestMessage):
        "Handle ECHO_DATA_MORE message."
        session.note_request(msg)
        msg.data.clear() # Clear data, we will accumulate sent DATA messages there
        reply = self.protocol.create_reply_for(msg)
        hnd = session.get_handle(msg)
        reply.data.append(pack('H', hnd)) # handle for type_data in DATA messages
        self.send(reply, session)
    def h_echo_data_sync(self, session: Session, msg: RequestMessage):
        "Handle ECHO_DATA_SYNC message."
        session.note_request(msg)
        # Data frame must contain number of DATA messages that would follow
        i, = unpack('H', msg.data[0])
        if i > 3:
            # too many data messages
            err = self.protocol.create_error_for(msg, ErrorCode.BAD_REQUEST)
            errd = err.add_error()
            errd.code = EchoError.PROTOCOL_VIOLATION
            errd.description = "Too many DATA messages"
            self.send(err, session)
            session.request_done(msg)
        else:
            msg.expect = i
            msg.data.clear() # Clear data, we will accumulate sent DATA messages there
            reply = self.protocol.create_reply_for(msg)
            hnd = session.get_handle(msg)
            reply.data.append(pack('H', hnd)) # handle for type_data in DATA messages
            self.send(reply, session)

class EchoServiceImpl(SimpleServiceImpl):
    """Implementation of ECHO service."""
    # It's not an official service, so we can use any UUID constants
    SERVICE_UID: UUID = SERVICE_UID
    SERVICE_NAME: str = "Sample ECHO service"
    SERVICE_VERSION: str = "0.2"
    PROTOCOL_UID: UUID = PROTOCOL_UID
    OPTIONAL: List[UUID] = [roman_api.SERVICE_UID]
    def initialize(self, svc: BaseService):
        super().initialize(svc)
        # Message handler for ECHO service
        self.msg_handler = EchoMessageHandler(self.svc_chn, self)
        #
        self.desc.uid = uuid1().bytes
        self.desc.host = "localhost"
        self.desc.identity.protocol.uid = self.msg_handler.protocol.uid.bytes
        self.desc.identity.protocol.version = str(self.msg_handler.protocol.revision)
        self.desc.identity.classification = "service-example/echo"
        # Channel to ROMAN service
        with_roman = roman_api.SERVICE_UID in self.svc_remotes
        if with_roman:
            self.roman_chn = DealerChannel(uuid1().bytes, False)
            svc.mngr.add(self.roman_chn)
            self.roman_chn.socket.connect_timeout = 1
            roman_cli = RomanClient(self.roman_chn, UUID(bytes=self.instance_id),
                                    self.desc.host, self.SERVICE_UID,
                                    self.SERVICE_NAME, self.SERVICE_VERSION)
            try:
                roman_cli.open(self.svc_remotes[roman_api.SERVICE_UID])
                self.msg_handler.roman_cli = roman_cli
            except:
                # we can live without ROMAN service, just clean up the ROMAN channel
                svc.mngr.remove(self.roman_chn)
                self.roman_chn.close()
