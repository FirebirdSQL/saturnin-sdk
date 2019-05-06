#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/fbsptest.py
# DESCRIPTION:    Base module for testing FBSP Services and Clients.
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

"""Base module for testing FBSP Services and Clients.
"""

from typing import List
import os
from time import monotonic
from struct import pack
from uuid import UUID, uuid1
import zmq
import saturnin.sdk
from saturnin.sdk.types import PeerDescriptor, AgentDescriptor, TSession
from saturnin.sdk.base import ChannelManager, DealerChannel
from saturnin.sdk.fbsp import Protocol, MsgType, Message

# Functions

def print_title(title, size=80, char='='):
    "Prints centered title surrounded by char."
    print(f"  {title}  ".center(size, char))

def print_msg(msg: Message, indent: int = 4):
    "Pretty-print message."
    print('\n'.join(('%s%s' % (' ' * indent, line) for line
                     in msg.get_printout().splitlines())))
    print('    ' + '~' * (80 - indent))

def print_session(session: TSession):
    "Print information about remote peer."
    print('Service information:')
    print(f'Peer uid:       {session.peer_id}')
    print(f'Host:           {session.host}')
    print(f'PID:            {session.pid}')
    print(f'Agent ID:       {session.agent_id}')
    print(f'Agent name:     {session.name}')
    print(f'Agent version:  {session.version}')
    print(f'Vendor ID:      {session.vendor}')
    print(f'Platform ID:    {session.platform}')
    print(f'Platform ver.:  {session.platform_version}')
    print(f'Calssification: {session.classification}')

# Classes

class BaseTestRunner:
    """Base Test Runner for Firebird Butler Services and Clients.

Attributes:
    :ctx:      ZMQ Context instance.
    :protocol: FBSP Protocol instance.
    :peer:     PeerDescriptor
    :agent:    AgentDescriptor
"""
    def __init__(self, context: zmq.Context = None):
        self.ctx = context if context else zmq.Context.instance()
        self._cnt = 0
        self.protocol: Protocol = Protocol.instance()
        self.peer: PeerDescriptor = PeerDescriptor(uuid1(), os.getpid(), 'localhost')
        self.agent: AgentDescriptor = AgentDescriptor(UUID('7608dca4-46d3-11e9-8f39-5404a6a1fd6e'),
                                                      "Saturnin SDK test client",
                                                      "Saturnin SDK test system",
                                                      '1.0',
                                                      saturnin.sdk.VENDOR_UID,
                                                      'system/test',
                                                      saturnin.sdk.PLATFORM_UID,
                                                      saturnin.sdk.PLATFORM_VERSION
                                                     )
    def get_token(self) -> bytes:
        "Return FBSP message token from integer."
        self._cnt += 1
        return pack('Q', self._cnt)
    def _raw_handshake(self, socket: zmq.Socket):
        "Raw ZMQ FBSP handshake test."
        print("Sending HELLO:")
        msg = self.protocol.create_message_for(MsgType.HELLO, self.get_token())
        msg.peer.instance.uid = self.peer.uid.bytes
        msg.peer.instance.pid = self.peer.pid
        msg.peer.instance.host = self.peer.host
        msg.peer.client.uid = self.agent.uid.bytes
        msg.peer.client.name = self.agent.name
        msg.peer.client.version = self.agent.version
        msg.peer.client.vendor.uid = self.agent.vendor_uid.bytes
        msg.peer.client.platform.uid = self.agent.platform_uid.bytes
        msg.peer.client.platform.version = self.agent.platform_version
        print_msg(msg)
        socket.send_multipart(msg.as_zmsg())
        print("Receiving response:")
        # get WELCOME
        zmsg = socket.recv_multipart()
        msg = self.protocol.parse(zmsg)
        print_msg(msg)
    def _run(self, test_names: List, *args):
        "Run test methods."
        start = monotonic()
        for name in test_names:
            try:
                print_title(name.replace('_raw_', '').replace('_client_', '').upper())
                test = getattr(self, name)
                test(*args)
            except Exception as exc:
                print_title("ERROR", char="*")
                print(exc)
        print_title("End")
        elapsed = monotonic() - start
        print(f"Ran {len(test_names)} tests in {elapsed} seconds")
    def run_raw_tests(self, endpoint: str, test_names: List[str] = None):
        "Run service tests using raw ZMQ messages."
        test_list = test_names if test_names else [name for name in dir(self)
                                                   if name.startswith('raw_')]
        test_list.insert(0, '_raw_handshake')
        socket = self.ctx.socket(zmq.DEALER)
        socket.identity = b'runner'
        socket.connect(endpoint)
        self._run(test_list, socket)
        socket.close()
    def run_client_tests(self, endpoint: str, test_names: List[str] = None):
        "Run service tests using service client."
        test_list = test_names if test_names else [name for name in dir(self)
                                                   if name.startswith('client_')]
        if hasattr(self, '_client_handshake'):
            test_list.insert(0, '_client_handshake')
        mngr = ChannelManager(self.ctx)
        try:
            chn = DealerChannel(b'runner', False)
            mngr.add(chn)
            self._run(test_list, chn, endpoint)
        finally:
            mngr.shutdown()
