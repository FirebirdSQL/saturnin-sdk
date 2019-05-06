#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/service/echo/client.py
# DESCRIPTION:    Sample ECHO service client (classic version)
# CREATED:        9.3.2019
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

"""Saturnin SDK examples - Sample ECHO service Client (classic version)

ECHO service sends data frames back to the sender.
"""

from uuid import UUID
from typing import List
from struct import pack, unpack
from saturnin.service.echo.api import EchoRequest, Protocol
from saturnin.sdk.base import BaseChannel, ServiceError
from saturnin.sdk.fbsp import Session, ClientMessageHandler, MsgType, MsgFlag, State, \
     DataMessage, StateMessage, ReplyMessage, ErrorMessage, enum_name, exception_for

class EchoClient(ClientMessageHandler):
    """Message handler for ECHO client."""
    def __init__(self, chn: BaseChannel, instance_uid: UUID, host: str, agent_uid: UUID,
                 agent_name: str, agent_version: str):
        super().__init__(chn, instance_uid, host, agent_uid, agent_name, agent_version)
        self.protocol = Protocol()
        self.handlers.update({(MsgType.REPLY, EchoRequest.ECHO): self.on_simple_echo,
                              (MsgType.REPLY, EchoRequest.ECHO_ROMAN): self.on_simple_echo,
                             })
    def on_error(self, session: Session, msg: ErrorMessage):
        "Handle ERROR message received from Service."
        self.last_token_seen = msg.token
        if msg.token != session.greeting.token:
            session.request_done(msg.token)
        raise exception_for(msg)
    def on_reply(self, session: Session, msg: ReplyMessage):
        "Handle Service REPLY message."
        req = session.get_request(msg.token)
        req.response = []
        if req.request_code == EchoRequest.ECHO_SYNC:
            # Note that we'll not set the `last_token_seen` to keep the loop going.
            if msg.has_ack_req():
                self.send(self.protocol.create_ack_reply(msg))
        elif req.request_code in (EchoRequest.ECHO_DATA_MORE, EchoRequest.ECHO_DATA_SYNC):
            # Service accepted our request, and returned a handle we have to use in our
            # DATA messages (type_data), so we are done here and we'll return the handle
            # to the caller that will send the data to the service. However, we'll keep
            # the request.
            req.response, = unpack('H', msg.data[0])
            self.last_token_seen = msg.token
        elif req.request_code in (EchoRequest.ECHO_MORE, EchoRequest.ECHO_STATE):
            # REPLY to these requests is just information that service accepted it. However,
            # we must handle it somehow as it's part of ECHO protocol. Because there are
            # subsequent messages and we want to handle them in single call to
            # `get_response()` loop (so caller's timeout matches the one in socket poll),
            # we'll not set the `last_token_seen` to keep the loop going. So no much work
            # for us here.
            #
            # This elif branch is pointless and would be removed in normal code. It's here
            # only for sake of clarity how the client side of ECHO protocol works.
            pass
    def on_data(self, session: Session, msg: DataMessage):
        "Handle DATA message."
        req = session.get_request(msg.token)
        # DATA messages could be related to different requests, so we need the request to
        # decide how to handle them.
        if req.request_code in (EchoRequest.ECHO_MORE, EchoRequest.ECHO_DATA_MORE):
            req.response.extend(msg.data)
            if not msg.has_more():
                # It was last one, so stop the loop and wrap up the request.
                self.last_token_seen = msg.token
                session.request_done(req)
        elif req.request_code == EchoRequest.ECHO_STATE:
            req.response.extend(msg.data)
        elif req.request_code == EchoRequest.ECHO_SYNC:
            # The SYNC protocol uses Flag.ACK_REQ to signal that there is more to send.
            # But we should send ACK_REPLY only when we process current one and are ready
            # for another.
            req.response.extend(msg.data)
            if msg.has_ack_req():
                self.send(self.protocol.create_ack_reply(msg))
            else:
                # It was last one, so stop the loop and wrap up the request.
                self.last_token_seen = msg.token
                session.request_done(req)
        elif req.request_code == EchoRequest.ECHO_DATA_SYNC:
            # We should receive ACK_REPLY to send more data.
            if msg.has_ack_reply():
                # Return from loop so caller can send another data
                self.last_token_seen = msg.token
            else:
                # We are getting our response
                req.response.extend(msg.data)
                if not msg.has_more():
                    # It was last one, so stop the loop and wrap up the request.
                    self.last_token_seen = msg.token
                    session.request_done(req)
    def on_state(self, session: Session, msg: StateMessage):
        "Handle STATE message."
        if msg.state == State.FINISHED:
            self.last_token_seen = msg.token
            session.request_done(msg.token)
        else:
            raise ServiceError(f"Unexpected STATE {enum_name(msg.state)} response.")
    def on_simple_echo(self, session: Session, msg: ReplyMessage):
        "ECHO/ECHO_ROMAN reply handler."
        self.last_token_seen = msg.token
        req = session.get_request(msg.token)
        req.response = msg.data
        session.request_done(req)
    # ECHO API for clients
    def open(self, endpoint: str):
        "Opens connection to ECHO service."
        self.connect_peer(endpoint)
        token = self.new_token()
        hello = self.protocol.create_message_for(MsgType.HELLO, token)
        hello.peer.CopyFrom(self.desc)
        self.send(hello)
        self.get_response(token)
    def close(self):
        "Close connection to ECHO service."
        self.discard_session(self.get_session())
    def echo(self, *args, **kwargs) -> List:
        """Pass data through ECHO request.

Each positional argument is sent in separate data frame of single ECHO request. They are
returned back in data frames of REPLY message.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(EchoRequest.ECHO, token)
        session.note_request(msg)
        msg.data = list(args)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO request")
        return msg.response
    def echo_roman(self, *args, **kwargs) -> List:
        """Pass data through ECHO_ROMAN request.

Each positional argument is sent in separate data frame of single ECHO_ROMAN request.
They are returned back in data frames of REPLY message.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(EchoRequest.ECHO_ROMAN, token)
        session.note_request(msg)
        msg.data = list(args)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_ROMAN request")
        return msg.response
    def echo_more(self, *args, **kwargs) -> List:
        """Pass data through ECHO_MORE request.

Each positional argument is sent in separate data frame of single ECHO request. They are
returned back as sequence of DATA messages using MORE flag to organize the data stream.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(EchoRequest.ECHO_MORE, token)
        session.note_request(msg)
        msg.data = list(args)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_MORE request")
        return msg.response
    def echo_state(self, *args, **kwargs) -> List:
        """Pass data through ECHO_STATE request.

Each positional argument is sent in separate data frame of single ECHO request. They are
returned back as sequence of DATA messages using final STATE message to organize the data
stream.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(EchoRequest.ECHO_STATE, token)
        session.note_request(msg)
        msg.data = list(args)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_STATE request")
        return msg.response
    def echo_sync(self, *args, **kwargs) -> List:
        """Pass data through ECHO_SYNC request.

Each positional argument is sent in separate data frame of single ECHO request. They are
returned back as sequence of DATA messages using Flag.ACK_REQ to organize the data
stream into synchronized transmission.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(EchoRequest.ECHO_SYNC, token)
        session.note_request(msg)
        msg.data = list(args)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_SYNC request")
        return msg.response
    def echo_data_more(self, *args, **kwargs) -> List:
        """Pass data through ECHO_DATA_MORE request.

Each positional argument is sent in separate DATA message using MORE flag to organize
the data stream. They are returned back in the same way using MORE flag.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(EchoRequest.ECHO_DATA_MORE, token)
        session.note_request(msg)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_DATA_MORE request")
        # Ok, we got the handle and are clear to send data using MORE flag.
        data_msg = self.protocol.create_message_for(MsgType.DATA, msg.token, msg.response)
        data = list(args)
        msg.response = [] # prepare response to accept data back
        while data:
            data_msg.data.append(data.pop(0))
            if data:
                data_msg.set_flag(MsgFlag.MORE)
            else:
                data_msg.clear_flag(MsgFlag.MORE)
            self.send(data_msg)
            data_msg.data.clear()
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_DATA_MORE request")
        return msg.response
    def echo_data_sync(self, *args, **kwargs) -> List:
        """Pass data through ECHO_DATA_SYNC request.

Each positional argument is sent in separate DATA message using ACK_REQ flag to organize
the data stream into synchronized transmission. They are returned back also as stream using
MORE flag.

This is the most complicated transmission pattern from all presented in ECHO API.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(EchoRequest.ECHO_DATA_SYNC, token)
        # data frame must contain number of messages we'll send
        msg.data.append(pack('H', len(args)))
        session.note_request(msg)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_DATA_SYNC request")
        # Ok, we got the handle and are clear to send data using MORE flag.
        data_msg = self.protocol.create_message_for(MsgType.DATA, msg.token, msg.response)
        data = list(args)
        msg.response = [] # prepare response to accept data back
        while data:
            data_msg.data.append(data.pop(0))
            if data:
                data_msg.set_flag(MsgFlag.ACK_REQ)
            else:
                data_msg.clear_flag(MsgFlag.ACK_REQ)
            self.send(data_msg)
            # Receive ACK_REPLY
            if data_msg.has_ack_req():
                if not self.get_response(token, kwargs.get('timeout')):
                    raise TimeoutError("The service did not respond on time to ECHO_DATA_SYNC request")
            data_msg.data.clear()
        # Get data back
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ECHO_DATA_SYNC request")
        return msg.response
