#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/service/roman/client.py
# DESCRIPTION:    Sample ROMAN service client (classic version)
# CREATED:        12.3.2019
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

"""Saturnin SDK examples - Sample ROMAN service client (classic version)

ROMAN service returns data frames with arabic numbers replaced with Roman numbers.
"""
from uuid import UUID
from typing import List
from saturnin.service.roman.api import RomanRequest, Protocol
from saturnin.sdk.base import BaseChannel
from saturnin.sdk.fbsp import Session, ClientMessageHandler, MsgType, \
     ReplyMessage, ErrorMessage, exception_for

class RomanClient(ClientMessageHandler):
    # pylint: disable=W0223,R0913
    """Message handler for ROMAN client."""
    def __init__(self, chn: BaseChannel, instance_uid: UUID, host: str, agent_uid: UUID,
                 agent_name: str, agent_version: str):
        super().__init__(chn, instance_uid, host, agent_uid, agent_name, agent_version)
        self.protocol = Protocol()
        self.handlers.update({(MsgType.REPLY, RomanRequest.ROMAN): self.h_roman,
                              MsgType.DATA: self.raise_protocol_violation,
                              MsgType.REPLY: self.raise_protocol_violation,
                              MsgType.STATE: self.raise_protocol_violation,
                             })
        self.desc.identity.protocol.uid = self.protocol.uid.bytes
        self.desc.identity.protocol.version = str(self.protocol.revision)
    def h_error(self, session: Session, msg: ErrorMessage):
        "Handle ERROR message received from Service."
        self.last_token_seen = msg.token
        if msg.token != session.greeting.token:
            session.request_done(msg.token)
        raise exception_for(msg)
    def h_roman(self, session: Session, msg: ReplyMessage):
        "ROMAN reply handler."
        self.last_token_seen = msg.token
        req = session.get_request(msg.token)
        req.response = msg.data
        session.request_done(req)
    # ROMAN API for clients
    def open(self, endpoint: str):
        "Opens connection to ROMAN service."
        self.connect_peer(endpoint)
        token = self.new_token()
        hello = self.protocol.create_message_for(MsgType.HELLO, token)
        hello.peer.CopyFrom(self.desc)
        self.send(hello)
        self.get_response(token, 1000)
    def roman(self, *args, **kwargs) -> List:
        """Pass data through ROMAN request.

Each positional argument is sent in separate data frame of single ROMAN request. They are
returned back in data frames of REPLY message.

Keyword arguments:
    :timeout: Timeout for operation.

Returns:
    List of positional arguments passed.
"""
        session: Session = self.get_session()
        assert session
        token = self.new_token()
        msg = self.protocol.create_request_for(RomanRequest.ROMAN, token)
        session.note_request(msg)
        msg.data = list(args)
        self.send(msg)
        if not self.get_response(token, kwargs.get('timeout')):
            raise TimeoutError("The service did not respond on time to ROMAN request")
        return msg.response
