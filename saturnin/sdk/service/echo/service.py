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

import logging
from typing import Any
from struct import pack, unpack
from saturnin.core.types import SaturninError, ServiceDescriptor
from saturnin.sdk.service.roman.client import RomanClient
from saturnin.core.base import DealerChannel
from saturnin.core.service import SimpleServiceImpl, BaseService
from saturnin.core.protocol.fbsp import Session, bb2h, ServiceMessagelHandler, \
     MsgType, MsgFlag, State, ErrorCode, HelloMessage, CancelMessage, DataMessage, \
     ReplyMessage, RequestMessage, note_exception, fbsp_proto
from .api import EchoRequest, EchoConfig

# Logger

log = logging.getLogger(__name__)

# Classes

class EchoMessageHandler(ServiceMessagelHandler):
    """Message handler for ECHO service."""
    RQ_ECHO: int = bb2h(1, EchoRequest.ECHO)
    RQ_ECHO_ROMAN: int = bb2h(1, EchoRequest.ECHO_ROMAN)
    RQ_ECHO_MORE: int = bb2h(1, EchoRequest.ECHO_MORE)
    RQ_ECHO_STATE: int = bb2h(1, EchoRequest.ECHO_STATE)
    RQ_ECHO_SYNC: int = bb2h(1, EchoRequest.ECHO_SYNC)
    RQ_ECHO_DATA_MORE: int = bb2h(1, EchoRequest.ECHO_DATA_MORE)
    RQ_ECHO_DATA_SYNC: int = bb2h(1, EchoRequest.ECHO_DATA_SYNC)
    def __init__(self, welcome_df: fbsp_proto.FBSPWelcomeDataframe):
        super().__init__()
        self.welcome_df = welcome_df
        # Our message handlers
        self.handlers.update({(MsgType.REQUEST, self.RQ_ECHO): self.handle_echo,
                              (MsgType.REQUEST, self.RQ_ECHO_ROMAN): self.handle_echo_roman,
                              (MsgType.REQUEST, self.RQ_ECHO_MORE): self.handle_echo_more,
                              (MsgType.REQUEST, self.RQ_ECHO_STATE): self.handle_echo_state,
                              (MsgType.REQUEST, self.RQ_ECHO_SYNC): self.handle_echo_sync,
                              (MsgType.REQUEST, self.RQ_ECHO_DATA_MORE): self.handle_echo_data_more,
                              (MsgType.REQUEST, self.RQ_ECHO_DATA_SYNC): self.handle_echo_data_sync,
                             })
        # Optional ROMAN client
        self.roman_cli: RomanClient = None
        self.roman_address = None
    def handle_hello(self, session: Session, msg: HelloMessage):
        """HELLO message handler. Sends WELCOME message back to the client."""
        if __debug__:
            log.debug("%s.handle_hello(%s)", self.__class__.__name__, session.routing_id)
        super().handle_hello(session, msg)
        welcome = self.protocol.create_welcome_reply(msg)
        welcome.peer.CopyFrom(self.welcome_df)
        self.send(welcome, session)
    def handle_cancel(self, session: Session, msg: CancelMessage):
        """Handle CANCEL message.

TODO: Implement support for canceletion of at least one multi-message API: ECHO_MORE,
ECHO_STATE, ECHO_SYNC, ECHO_DATA_MORE or ECHO_DATA_SYNC.
"""
        if __debug__:
            log.debug("%s.handle_cancel(%s)", self.__class__.__name__, session.routing_id)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        self.send_error(session, session.greeting, ErrorCode.NOT_IMPLEMENTED,
                        "ECHO service does not support request cancelation")
    def handle_ack_reply(self, session: Session, msg: ReplyMessage):
        """REPLY message handler."""
        # If the message is ACK-REPLY to ECHO_SYNC request, we will start sending DATA to
        # the client.
        if __debug__:
            log.debug("%s.handle_ack_reply(%s)", self.__class__.__name__, session.routing_id)
        if msg.request_code == self.RQ_ECHO_SYNC:
            req_msg = session.get_request(msg.token)
            msg_data = self.protocol.create_data_for(req_msg)
            msg_data.data.append(req_msg.data.pop(0))
            msg_data.type_data = session.get_handle(req_msg)
            if req_msg.data:
                msg_data.set_flag(MsgFlag.ACK_REQ)
            else:
                session.request_done(req_msg)
            self.send(msg_data, session)
    def handle_data(self, session: Session, msg: DataMessage):
        """DATA message handler.

There are three cases when this handler is called:

    1.  ACK_REPLY for ECHO_SYNC
    2.  Data package for ECHO_DATA_MORE
    3.  Data package for ECHO_DATA_SYNC

All messages must have a valid handle in `type_data`.
"""
        if __debug__:
            log.debug("%s.handle_data(%s)", self.__class__.__name__, session.routing_id)
        if session.is_handle_valid(msg.type_data):
            req_msg = session.get_request(handle=msg.type_data)
            if req_msg.request_code == self.RQ_ECHO_SYNC:
                if msg.has_ack_reply():
                    msg_data = self.protocol.create_data_for(req_msg)
                    msg_data.type_data = msg.type_data
                    msg_data.data.append(req_msg.data.pop(0))
                    if req_msg.data:
                        msg_data.set_flag(MsgFlag.ACK_REQ)
                    else:
                        session.request_done(req_msg)
                    self.send(msg_data, session)
                else: # regular DATA without ACK_REPLY is a client error
                    self.send_error(session, req_msg, ErrorCode.PROTOCOL_VIOLATION,
                                    "Expected DATA with ACK_REPLY")
                    session.request_done(req_msg)
            elif req_msg.request_code == self.RQ_ECHO_DATA_MORE:
                if len(req_msg.data) == 3:
                    # too many data messages
                    self.send_error(session, req_msg, ErrorCode.PROTOCOL_VIOLATION,
                                    "Too many DATA messages")
                    session.request_done(req_msg)
                req_msg.data.append(msg)
                if not msg.has_more():
                    # That was last one, send them back all at once
                    msg_data = self.protocol.create_data_for(req_msg)
                    while req_msg.data:
                        pkg = req_msg.data.pop(0)
                        msg_data.data.extend(pkg.data)
                        if req_msg.data:
                            msg_data.set_flag(MsgFlag.MORE)
                        else:
                            msg_data.clear_flag(MsgFlag.MORE)
                        self.send(msg_data, session)
                        msg_data.data.clear()
                    session.request_done(req_msg)
            elif req_msg.request_code == self.RQ_ECHO_DATA_SYNC:
                req_msg.data.append(msg)
                if msg.has_ack_req():
                    if len(req_msg.data) == req_msg.expect:
                        # Error, the last one should not have ACK_REQ
                        self.send_error(session, req_msg, ErrorCode.PROTOCOL_VIOLATION,
                                        "Last DATA message must not have ACK_REQ flag")
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
                                msg_data.set_flag(MsgFlag.MORE)
                            else:
                                msg_data.clear_flag(MsgFlag.MORE)
                            self.send(msg_data, session)
                            msg_data.data.clear()
                        session.request_done(req_msg)
                    else:
                        # Did we miss a DATA message?
                        self.send_error(session, req_msg, ErrorCode.PROTOCOL_VIOLATION,
                                        f"Announced {req_msg.expect} messages, but only {len(req_msg.data)} received")
                        session.request_done(req_msg)
        else:
            self.send_error(session, session.greeting, ErrorCode.PROTOCOL_VIOLATION,
                            "Invalid DATA.type_data content")
            session.request_done(req_msg)
    def handle_echo(self, session: Session, msg: RequestMessage):
        """ECHO request handler."""
        if __debug__:
            log.debug("%s.handle_echo(%s)", self.__class__.__name__, session.routing_id)
        session.note_request(msg)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        reply = self.protocol.create_reply_for(msg)
        reply.data.extend(list(msg.data)) # copy data
        self.send(reply, session)
        session.request_done(msg)
    def handle_echo_roman(self, session: Session, msg: RequestMessage):
        """ECHO_ROMAN request handler."""
        if __debug__:
            log.debug("%s.handle_echo_roman(%s)", self.__class__.__name__, session.routing_id)
        session.note_request(msg)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        #
        if self.roman_address and self.roman_cli is not None and not self.roman_cli.is_active():
            # ROMAN service is not yet connected
            try:
                self.roman_cli.open(self.roman_address)
            except Exception as exc:
                log.warning("ROMAN service not available: %s", exc)
                self.send_error(session, msg, ErrorCode.FAILED_DEPENDENCY,
                                "ROMAN service not available", exc=exc)
                session.request_done(msg)
                return
        if self.roman_cli is not None and self.roman_cli.is_active():
            reply = self.protocol.create_reply_for(msg)
            # copy data from ROMAN's reply
            try:
                reply.data.extend(list(self.roman_cli.roman(*msg.data, timeout=1000)))
            except TimeoutError as exc:
                reply = self.protocol.create_error_for(msg, ErrorCode.REQUEST_TIMEOUT)
                note_exception(reply, exc)
            except SaturninError as exc:
                reply = self.protocol.create_error_for(msg, ErrorCode.ERROR)
                note_exception(reply, exc)
            self.send(reply, session)
        else:
            # ROMAN service not available
            self.send_error(session, msg, ErrorCode.FAILED_DEPENDENCY,
                            "ROMAN service not available")
        session.request_done(msg)
    def handle_echo_more(self, session: Session, msg: RequestMessage):
        """ECHO_MORE request handler."""
        if __debug__:
            log.debug("%s.handle_echo_more(%s)", self.__class__.__name__, session.routing_id)
        session.note_request(msg)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        reply = self.protocol.create_reply_for(msg)
        if msg.data: # Required by FBSP, rules for MORE handling
            reply.set_flag(MsgFlag.MORE)
        self.send(reply, session)
        data_msg = self.protocol.create_data_for(msg)
        while msg.data:
            data_msg.data.append(msg.data.pop(0))
            if msg.data:
                data_msg.set_flag(MsgFlag.MORE)
            else:
                data_msg.clear_flag(MsgFlag.MORE)
            self.send(data_msg, session)
            data_msg.data.clear()
        session.request_done(msg.token)
    def handle_echo_state(self, session: Session, msg: RequestMessage):
        """ECHO_STATE request handler."""
        if __debug__:
            log.debug("%s.handle_echo_state(%s)", self.__class__.__name__, session.routing_id)
        session.note_request(msg)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
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
    def handle_echo_sync(self, session: Session, msg: RequestMessage):
        """Handle ECHO_SYNC message."""
        if __debug__:
            log.debug("%s.handle_echo_sync(%s)", self.__class__.__name__, session.routing_id)
        session.note_request(msg)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        reply = self.protocol.create_reply_for(msg)
        reply.set_flag(MsgFlag.ACK_REQ)
        self.send(reply, session)
    def handle_echo_data_more(self, session: Session, msg: RequestMessage):
        """Handle ECHO_DATA_MORE message."""
        if __debug__:
            log.debug("%s.handle_echo_data_more(%s)", self.__class__.__name__, session.routing_id)
        session.note_request(msg)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        msg.data.clear() # Clear data, we will accumulate sent DATA messages there
        reply = self.protocol.create_reply_for(msg)
        hnd = session.get_handle(msg)
        reply.data.append(pack('H', hnd)) # handle for type_data in DATA messages
        self.send(reply, session)
    def handle_echo_data_sync(self, session: Session, msg: RequestMessage):
        """Handle ECHO_DATA_SYNC message."""
        if __debug__:
            log.debug("%s.handle_echo_data_sync(%s)", self.__class__.__name__,
                      session.routing_id)
        session.note_request(msg)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        # Data frame must contain number of DATA messages that would follow
        i, = unpack('H', msg.data[0])
        if i > 3:
            # too many data messages
            self.send_error(session, msg, ErrorCode.PROTOCOL_VIOLATION,
                            "Too many DATA messages")
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
    def __init__(self, descriptor: ServiceDescriptor, stop_event: Any):
        super().__init__(descriptor, stop_event)
        self.roman_chn = None
    def initialize(self, svc: BaseService):
        super().initialize(svc)
        # Message handler for ECHO service
        self.svc_chn.set_handler(EchoMessageHandler(self.welcome_df))
    def configure(self, svc: BaseService, config: EchoConfig) -> None:
        """Service configuration."""
        super().configure(svc, config)
        # Channel to ROMAN service
        if config.roman_address is not None:
            self.roman_chn = DealerChannel(self.instance_id.hex().encode('ascii'), False)
            self.mngr.add(self.roman_chn)
            self.roman_chn.socket.connect_timeout = 1
            self.svc_chn.handler.roman_address = config.roman_address.value
            self.svc_chn.handler.roman_cli = RomanClient(self.roman_chn, self.peer, self.agent)
