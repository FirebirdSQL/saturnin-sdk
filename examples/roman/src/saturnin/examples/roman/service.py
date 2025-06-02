# SPDX-FileCopyrightText: 2019-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
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

"""Saturnin SDK examples - Implementation of the sample ROMAN service.

This module provides the `RomanService` class, which implements a service that
receives text data frames and returns them with Arabic numbers converted to Roman numerals.

Supported requests:

    :ROMAN: REPLY with altered REQUEST data frames.
"""

from __future__ import annotations

from itertools import groupby

from saturnin.base import Channel
from saturnin.component.service import Service
from saturnin.protocol.fbsp import ErrorCode, FBSPMessage, FBSPService, FBSPSession

from .api import RomanAPI


def arabic2roman(line: str) -> bytes:
    """Returns UTF-8 bytestring with arabic numbers replaced with Roman ones.
    """
    def i2r(num: int) -> str:
        """Converts Arabic number to Roman number.
        """
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
    def isdigit(char: str) -> bool:
        return char.isdigit()
    def replace(convert: bool, segment: str) -> str:
        return i2r(int(segment)) if convert else segment
    # An one-liner to please Pythonistas and confuse others
    return bytes(''.join(replace(convert, segment) for convert, segment in
                         ((k, ''.join(list(g))) for k, g in groupby(line, isdigit))),
                 'utf8')


class RomanService(Service):
    """ROMAN service implementation.
    """
    def register_api_handlers(self, service: FBSPService) -> None:
        """Called by `initialize()` for registration of service API handlers and FBSP
        service event handlers.

        This method registers the `handle_roman` method to handle `RomanAPI.ROMAN` requests.
        """
        service.register_api_handler(RomanAPI.ROMAN, self.handle_roman)
    def handle_roman(self, channel: Channel, session: FBSPSession, msg: FBSPMessage,
                     protocol: FBSPService) -> None:
        """Handle REQUEST/ROMAN message.

        Data frames must contain strings as UTF-8 encoded bytes. We'll send them back in
        REPLY with Arabic numbers replaced with Roman ones.
        """
        if msg.has_ack_req():
            channel.send(protocol.create_ack_reply(msg), session)
        reply = protocol.create_reply_for(msg)
        try:
            for data in msg.data:
                line = data.decode('utf8')
                reply.data.append(arabic2roman(line))
            channel.send(reply, session)
        except UnicodeDecodeError:
            protocol.send_error(session, msg, ErrorCode.BAD_REQUEST,
                                        "Data must be UTF-8 bytestrings")
