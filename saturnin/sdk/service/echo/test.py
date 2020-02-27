#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/service/echo/test.py
# DESCRIPTION:    Test runner for ECHO service (classic version)
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

"""Test runner for ECHO service (classic version)
"""

from struct import pack, unpack
from saturnin.core.base import Channel
from saturnin.sdk.test.fbsp import BaseTestRunner, zmq, print_msg
from saturnin.core.protocol.fbsp import StateMessage, MsgType, MsgFlag
from .api import EchoRequest, ECHO_INTERFACE_UID
from .client import EchoClient

class TestRunner(BaseTestRunner):
    """Test Runner for ECHO Service and Client.
"""
    def __init__(self, context):
        super().__init__(context)
        self.interface_uid = ECHO_INTERFACE_UID.bytes
        self.test_data = [b"Back to the Future (1985) takes place in year 1985",
                          b"Back to the Future 2 (1989) takes place in year 2015",
                          b"Back to the Future 3 (1990) takes place in year 1885"]
    def create_client(self, channel: Channel) -> EchoClient:
        return EchoClient(channel, self.peer, self.agent)
    def run_request(self, api_call):
        """Execute Client API call."""
        print('Sent:')
        for line in self.test_data:
            print(' ' * 4, line)
        data = api_call(*self.test_data)
        print('Received:')
        for line in data:
            print(' ' * 4, line)
    def raw_echo(self, socket: zmq.Socket):
        """Raw test of ECHO request."""
        print("Sending ECHO request:")
        msg = self.protocol.create_request_for(self.interface_id, EchoRequest.ECHO,
                                               self.get_token())
        msg.data.extend(self.test_data)
        print_msg(msg)
        socket.send_multipart(msg.as_zmsg())
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        print_msg(msg)
    def raw_roman(self, socket: zmq.Socket):
        """Raw test of ECHO_ROMAN request."""
        print("Sending ECHO request:")
        msg = self.protocol.create_request_for(self.interface_id, EchoRequest.ECHO_ROMAN,
                                               self.get_token())
        msg.data.extend(self.test_data)
        print_msg(msg)
        socket.send_multipart(msg.as_zmsg())
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        print_msg(msg)
    def raw_echo_more(self, socket: zmq.Socket):
        """Raw test of ECHO_MORE request."""
        print("Sending ECHO_MORE request:")
        msg = self.protocol.create_request_for(self.interface_id, EchoRequest.ECHO_MORE,
                                               self.get_token())
        msg.data.extend(self.test_data)
        socket.send_multipart(msg.as_zmsg())
        print_msg(msg)
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        print_msg(msg)
        print("Receiving DATA:")
        while True:
            zmsg = socket.recv_multipart()
            msg = self.protocol.parse(zmsg)
            print_msg(msg)
            if not msg.has_more():
                break
        print("    End of data stream")
    def raw_echo_state(self, socket: zmq.Socket):
        """Raw test of ECHO_STATE request."""
        print("Sending ECHO_STATE request:")
        msg = self.protocol.create_request_for(self.interface_id, EchoRequest.ECHO_STATE,
                                               self.get_token())
        msg.data.extend(self.test_data)
        print_msg(msg)
        socket.send_multipart(msg.as_zmsg())
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        print_msg(msg)
        print("Receiving DATA:")
        while True:
            zmsg = socket.recv_multipart()
            msg = self.protocol.parse(zmsg)
            print_msg(msg)
            if isinstance(msg, StateMessage):
                break
        print("    End of data stream")
    def raw_echo_sync(self, socket: zmq.Socket):
        """Raw test of ECHO_SYNC request."""
        print("Sending ECHO_SYNC request:")
        msg = self.protocol.create_request_for(self.interface_id, EchoRequest.ECHO_SYNC,
                                               self.get_token())
        msg.data.extend(self.test_data)
        print_msg(msg)
        socket.send_multipart(msg.as_zmsg())
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        print_msg(msg)
        if msg.has_ack_req():
            print("Sending ACK to REPLY:")
            ack = self.protocol.create_ack_reply(msg)
            print_msg(ack)
            socket.send_multipart(ack.as_zmsg())
        while True:
            print("Receiving DATA:")
            zmsg = socket.recv_multipart()
            msg = self.protocol.parse(zmsg)
            print_msg(msg)
            if msg.has_ack_req():
                print("Sending ACK to DATA:")
                ack = self.protocol.create_ack_reply(msg)
                print_msg(ack)
                socket.send_multipart(ack.as_zmsg())
            else:
                break
        print("    End of data stream")
    def raw_echo_data_more(self, socket: zmq.Socket):
        """Raw test of ECHO_DATA_MORE request."""
        print("Sending ECHO_DATA_MORE request:")
        token = self.get_token()
        msg = self.protocol.create_request_for(self.interface_id,
                                               EchoRequest.ECHO_DATA_MORE, token)
        print_msg(msg)
        socket.send_multipart(msg.as_zmsg())
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        handle, = unpack('H', msg.data[0])
        print_msg(msg)
        print("Sending DATA:")
        msg = self.protocol.create_message_for(MsgType.DATA, token, handle)
        for i, data in enumerate(self.test_data, 1):
            msg.data.clear()
            msg.data.append(data)
            if i != len(self.test_data):
                msg.set_flag(MsgFlag.MORE)
            else:
                msg.clear_flag(MsgFlag.MORE)
            print_msg(msg)
            socket.send_multipart(msg.as_zmsg())
        print("Receiving DATA back:")
        while True:
            zmsg = socket.recv_multipart()
            msg = self.protocol.parse(zmsg)
            print_msg(msg)
            if not msg.has_more():
                break
        print("    End of data stream")
    def raw_echo_data_sync(self, socket: zmq.Socket):
        """Raw test of ECHO_DATA_SYNC request."""
        print("Sending ECHO_DATA_SYNC request:")
        token = self.get_token()
        msg = self.protocol.create_request_for(self.interface_id,
                                               EchoRequest.ECHO_DATA_SYNC, token)
        msg.data.append(pack('H', len(self.test_data)))
        socket.send_multipart(msg.as_zmsg())
        print("Receiving reply:")
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        handle, = unpack('H', msg.data[0])
        print_msg(msg)
        msg = self.protocol.create_message_for(MsgType.DATA, token, handle)
        for i, data in enumerate(self.test_data, 1):
            msg.data.clear()
            msg.data.append(data)
            if i != len(self.test_data):
                msg.set_flag(MsgFlag.ACK_REQ)
            else:
                msg.clear_flag(MsgFlag.ACK_REQ)
            print("Sending DATA:")
            print_msg(msg)
            socket.send_multipart(msg.as_zmsg())
            if msg.has_ack_req():
                print("Receiving ACK to DATA:")
                zmsg = socket.recv_multipart()
                ack = self.protocol.parse(zmsg)
                print_msg(ack)
        print("Receiving DATA back:")
        while True:
            zmsg = socket.recv_multipart()
            msg = self.protocol.parse(zmsg)
            print_msg(msg)
            if not msg.has_more():
                break
        print("    End of data stream")
    def client_echo(self, client: EchoClient):
        """Client test of echo() API call."""
        self.run_request(client.echo)
    def client_echo_roman(self, client: EchoClient):
        """Client test of echo_roman() API call."""
        self.run_request(client.echo_roman)
    def client_echo_more(self, client: EchoClient):
        """Client test of echo_more() API call."""
        self.run_request(client.echo_more)
    def client_echo_state(self, client: EchoClient):
        """Client test of echo_state() API call."""
        self.run_request(client.echo_state)
    def client_echo_sync(self, client: EchoClient):
        """Client test of echo_sync() API call."""
        self.run_request(client.echo_sync)
    def client_echo_data_more(self, client: EchoClient):
        """Client test of echo_data_more() API call."""
        self.run_request(client.echo_data_more)
    def client_echo_data_sync(self, client: EchoClient):
        """Client test of echo_data_sync() API call."""
        self.run_request(client.echo_data_sync)
