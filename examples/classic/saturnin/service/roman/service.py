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

from uuid import UUID
from itertools import groupby
from saturnin.sdk.types import ServiceError, InvalidMessageError, MsgType, ErrorCode, \
     TSession
from saturnin.service.roman.api import RomanRequest, SERVICE_AGENT, SERVICE_API
from saturnin.sdk.base import BaseChannel, BaseService
from saturnin.sdk.classic import SimpleServiceImpl
from saturnin.sdk.fbsp import Session, ServiceMessagelHandler, HelloMessage, \
     CancelMessage, RequestMessage, bb2h

# Functions

def arabic2roman(line: str) -> bytes:
    "Returns UTF-8 bytestring with arabic numbers replaced with Roman ones."
    def i2r(num: int) -> str:
        "Converts Arabic number to Roman number."
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
    def __init__(self, chn: BaseChannel, service):
        super().__init__(chn, service)
        # Our message handlers
        self.handlers.update({(MsgType.REQUEST, bb2h(1, RomanRequest.ROMAN)): self.on_roman,
                              MsgType.DATA: self.send_protocol_violation,
                             })
    def on_invalid_message(self, session: TSession, exc: InvalidMessageError):
        "Invalid Message event."
        raise ServiceError("Invalid message") from exc
    def on_invalid_greeting(self, exc: InvalidMessageError):
        "Invalid Greeting event."
        raise ServiceError("Invalid Greeting") from exc
    def on_dispatch_error(self, session: TSession, exc: Exception):
        "Exception unhandled by `dispatch()`."
        raise ServiceError("Unhandled exception") from exc
    def on_hello(self, session: TSession, msg: HelloMessage):
        "HELLO message handler. Sends WELCOME message back to the client."
        super().on_hello(session, msg)
        welcome = self.protocol.create_welcome_reply(msg)
        welcome.peer.CopyFrom(self.impl.welcome_df)
        self.send(welcome, session)
    def on_cancel(self, session: TSession, msg: CancelMessage):
        "Handle CANCEL message."
        # ROMAN uses simple REQUEST/REPLY API, so there is no point to send CANCEL
        # messages. However, we have to handle it although we'll do nothing.
        # In such cases we could either override the on_cancel() method like now,
        # or assign self.do_nothing handler to MsgType.CANCEL in __init__().
    def on_roman(self, session: TSession, msg: RequestMessage):
        """Handle REQUEST/ROMAN message.

Data frames must contain strings as UTF-8 encoded bytes. We'll send them back in REPLY with
Arabic numbers replaced with Roman ones.
"""
        reply = self.protocol.create_reply_for(msg)
        try:
            for data in msg.data:
                line = data.decode('utf8')
                reply.data.append(arabic2roman(line))
            self.send(reply, session)
        except UnicodeDecodeError:
            err_msg = self.protocol.create_error_for(msg, ErrorCode.BAD_REQUEST)
            err = err_msg.add_error()
            err.description = "Data must be UTF-8 bytestrings"
            self.send(err_msg, session)

class RomanServiceImpl(SimpleServiceImpl):
    """Implementation of ROMAN service."""
    def __init__(self):
        super().__init__()
        self.agent = SERVICE_AGENT
        self.api = SERVICE_API
    def initialize(self, svc: BaseService):
        super().initialize(svc)
        self.msg_handler = RomanMessageHandler(self.svc_chn, self)
