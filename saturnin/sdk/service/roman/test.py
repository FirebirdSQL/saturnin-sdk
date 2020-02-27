#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/service/roman/test.py
# DESCRIPTION:    Test runner for ROMAN service (classic version)
# CREATED:        13.3.2019
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

"""Test runner for ROMAN service (classic version)
"""

#from saturnin.sdk.types import TClient
from saturnin.core.base import Channel
from saturnin.sdk.test.fbsp import BaseTestRunner, zmq, print_msg
#from saturnin.sdk.client import ServiceClient
from .api import RomanRequest, ROMAN_INTERFACE_UID
from .client import RomanClient

class TestRunner(BaseTestRunner):
    """Test Runner for ROMAN Service and Client.
"""
    def __init__(self, context):
        super().__init__(context)
        self.interface_uid = ROMAN_INTERFACE_UID.bytes
        self.test_data = [b"Back to the Future (1985) takes place in year 1985",
                          b"Back to the Future 2 (1989) takes place in year 2015",
                          b"Back to the Future 3 (1990) takes place in year 1885"]
    def create_client(self, channel: Channel) -> RomanClient:
        return RomanClient(channel, self.peer, self.agent)
    def run_request(self, api_call):
        """Execute Client API call."""
        print('Sent:')
        for line in self.test_data:
            print(' ' * 4, line)
        data = api_call(*self.test_data)
        print('Received:')
        for line in data:
            print(' ' * 4, line)
    def raw_roman(self, socket: zmq.Socket):
        """Raw test of ROMAN request."""
        print("Sending ROMAN request:")
        msg = self.protocol.create_request_for(self.interface_id, RomanRequest.ROMAN,
                                               self.get_token())
        msg.data.extend(self.test_data)
        print_msg(msg)
        socket.send_multipart(msg.as_zmsg())
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        print_msg(msg)
    def client_roman(self, client: RomanClient):
        """Client test of roman() API call."""
        self.run_request(client.roman)
