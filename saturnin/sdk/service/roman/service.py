#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/service/roman/service.py
# DESCRIPTION:    Sample ROMAN service (classic version)
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

"""Saturnin SDK examples - Sample ROMAN service (classic version)

ROMAN service returns data frames with arabic numbers replaced with Roman numbers.

Supported requests:

    :ROMAN: REPLY with altered REQUEST data frames.
"""

import logging
from itertools import groupby
from .api import RomanRequest
from saturnin.core.protocol.fbsp import MsgType, ErrorCode, Session, ServiceMessagelHandler, \
     HelloMessage, CancelMessage, RequestMessage, bb2h, fbsp_proto
from saturnin.core.service import SimpleServiceImpl, BaseService

# Logger

log = logging.getLogger(__name__)

# Functions

def arabic2roman(line: str) -> bytes:
    """Returns UTF-8 bytestring with arabic numbers replaced with Roman ones."""
    def i2r(num: int) -> str:
        """Converts Arabic number to Roman number."""
        val = [1000, 900, 500, 400, 100, 90, 50, 40, 10, 9, 5, 4, 1]
        syb = ["M", "CM", "D", "CD", "C", "XC", "L", "XL", "X", "IX", "V", "IV", "I"]
        roman_num = ''
        i = 0
        while num > 0:
            for _ in range(num // val[i]):
                roman_num += syb[i]
                num -= val[i]
            i += 1
        return roman_num
    def isdigit(char):
        return char.isdigit()
    def replace(convert, segment):
        return i2r(int(segment)) if convert else segment
    # An one-liner to please Pythonistas and confuse others
    return bytes(''.join(replace(convert, segment) for convert, segment in
                         ((k, ''.join(list(g))) for k, g in groupby(line, isdigit))),
                 'utf8')

# Classes

class RomanMessageHandler(ServiceMessagelHandler):
    """Message handler for ROMAN service."""
    RQ_ROMAN = bb2h(1, RomanRequest.ROMAN)
    def __init__(self, welcome_df: fbsp_proto.FBSPWelcomeDataframe):
        super().__init__()
        self.welcome_df = welcome_df
        # Our message handlers
        self.handlers.update({(MsgType.REQUEST, self.RQ_ROMAN): self.handle_roman,
                              MsgType.DATA: self.send_protocol_violation,
                             })
    def handle_hello(self, session: Session, msg: HelloMessage):
        """HELLO message handler. Sends WELCOME message back to the client."""
        if __debug__:
            log.debug("%s.handle_hello(%s)", self.__class__.__name__, session.routing_id)
        super().handle_hello(session, msg)
        welcome = self.protocol.create_welcome_reply(msg)
        welcome.peer.CopyFrom(self.welcome_df)
        self.send(welcome, session)
    def handle_cancel(self, session: Session, msg: CancelMessage):
        """Handle CANCEL message."""
        # ROMAN uses simple REQUEST/REPLY API, so there is no reason to support CANCEL
        if __debug__:
            log.debug("%s.handle_cancel(%s)", self.__class__.__name__, session.routing_id)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        self.send_error(session, session.greeting, ErrorCode.NOT_IMPLEMENTED,
                        "ROMAN service does not support request cancelation")
    def handle_roman(self, session: Session, msg: RequestMessage):
        """Handle REQUEST/ROMAN message.

Data frames must contain strings as UTF-8 encoded bytes. We'll send them back in REPLY with
Arabic numbers replaced with Roman ones.
"""
        if __debug__:
            log.debug("%s.handle_roman(%s)", self.__class__.__name__, session.routing_id)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
        reply = self.protocol.create_reply_for(msg)
        try:
            for data in msg.data:
                line = data.decode('utf8')
                reply.data.append(arabic2roman(line))
            self.send(reply, session)
        except UnicodeDecodeError:
            self.send_error(session, msg, ErrorCode.BAD_REQUEST,
                            "Data must be UTF-8 bytestrings")

class RomanServiceImpl(SimpleServiceImpl):
    """Implementation of ROMAN service."""
    def initialize(self, svc: BaseService):
        super().initialize(svc)
        self.svc_chn.set_handler(RomanMessageHandler(self.welcome_df))
