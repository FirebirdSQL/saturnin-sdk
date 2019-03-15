#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/service/roman/api.py
# DESCRIPTION:    API for sample ROMAN service
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

"""Saturnin SDK examples - ROMAN service API

ROMAN service returns data frames with arabic numbers replaced with Roman numbers.

Supported requests:

    :ROMAN: REPLY with altered REQUEST data frames.
"""

from enum import IntEnum
from uuid import UUID
from saturnin.sdk import fbsp

# It's not an official protocol, so we can use any UUID constants
PROTOCOL_UID = UUID('d0e35134-44af-11e9-b5b8-5404a6a1fd6e')
PROTOCOL_REVISION = 1

# It's not an official service, so we can use any UUID constants
SERVICE_UID: UUID = UUID('413f76e8-4662-11e9-aa0d-5404a6a1fd6e')

#  Request Codes

class RomanRequest(IntEnum):
    "Roman Service Request Code"
    ROMAN = 1000

# Error Codes

class RomanError(IntEnum):
    "Roman Service Error Code"
    PROTOCOL_VIOLATION = 1000

# ECHO protocol

class Protocol(fbsp.Protocol):
    """ROMAN FBSP protocol.
"""
    def __init__(self):
        super().__init__()
        self._error_enums.append(RomanError)
        self._request_enums.append(RomanRequest)
        self.uid = PROTOCOL_UID
        self.revision = PROTOCOL_REVISION
