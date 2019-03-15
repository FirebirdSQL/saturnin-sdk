#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/service/echo/api.py
# DESCRIPTION:    API for sample ECHO service
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

"""Saturnin SDK examples - ECHO service API

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

from enum import IntEnum
from uuid import UUID
from saturnin.sdk import fbsp

# It's not an official protocol, so we can use any UUID constant
PROTOCOL_UID = UUID('24580be2-4434-11e9-b528-5404a6a1fd6e')
PROTOCOL_REVISION = 1

# It's not an official service, so we can use any UUID constants
SERVICE_UID: UUID = UUID('7e59724e-46a4-11e9-8f39-5404a6a1fd6e')

#  Request Codes

class EchoRequest(IntEnum):
    "Echo Service Request Code"
    ECHO = 1000
    ECHO_ROMAN = 1001
    ECHO_MORE = 1002
    ECHO_STATE = 1003
    ECHO_SYNC = 1004
    ECHO_DATA_MORE = 1005
    ECHO_DATA_SYNC = 1006

# Error Codes

class EchoError(IntEnum):
    "Echo Service Error Code"
    PROTOCOL_VIOLATION = 1000

# ECHO protocol

class Protocol(fbsp.Protocol):
    """ECHO FBSP protocol.
"""
    def __init__(self):
        super().__init__()
        self._error_enums.append(EchoError)
        self._request_enums.append(EchoRequest)
        self.uid = PROTOCOL_UID
        self.revision = PROTOCOL_REVISION
