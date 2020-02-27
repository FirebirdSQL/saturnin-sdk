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
import logging
from socket import getfqdn
from time import monotonic
from struct import pack
import uuid
import zmq
from saturnin.core import VENDOR_UID
from saturnin.core.types import PeerDescriptor, AgentDescriptor, ClientError
from saturnin.core.base import ChannelManager, Channel, DealerChannel
from saturnin.core.client import ServiceClient
from saturnin.core.protocol.fbsp import Protocol, Session, MsgType, Message, HelloMessage, \
     WelcomeMessage, uid2uuid

# Logger

log = logging.getLogger(__name__)
"""Logger for tests"""

# Functions

def print_title(title, size=80, char='='):
    """Prints centered title surrounded by char."""
    print(f"  {title}  ".center(size, char))

def print_msg(msg: Message, data_frames: str = None, indent: int = 4):
    """Pretty-print message."""
    print('\n'.join(('%s%s' % (' ' * indent, line) for line
                     in msg.get_printout(with_data=data_frames is None).splitlines())))
    if data_frames is not None:
        print('\n'.join(('%s%s' % (' ' * indent, line) for line in
                         uid2uuid(data_frames.splitlines()))))
    print('    ' + '~' * (80 - indent))

def print_data(data: str = None, indent: int = 4):
    """Pretty-print data."""
    if data is not None:
        print('\n'.join(('%s%s' % (' ' * indent, line) for line in
                         uid2uuid(str(data).splitlines()))))
    print('    ' + '~' * (80 - indent))

def print_session(session: Session):
    """Print information about remote peer."""
    print('Service information:')
    print('Peer uid:      ', session.peer_id)
    print('Host:          ', session.host)
    print('PID:           ', session.pid)
    print('Agent ID:      ', session.agent_id)
    print('Agent name:    ', session.name)
    print('Agent version: ', session.version)
    print('Vendor ID:     ', session.vendor)
    print('Platform ID:   ', session.platform)
    print('Platform ver.: ', session.platform_version)
    print('Classification:', session.classification)

# Classes

class BaseTestRunner:
    """Base Test Runner for Firebird Butler Services and Clients.

Attributes:
    interface_uid: Interface UID (must be assigned by descendant class)
    interface_id:  Number assigned to interface
    ctx:           ZMQ Context instance.
    protocol:      FBSP Protocol instance.
    peer:          PeerDescriptor
    agent:         AgentDescriptor
"""
    def __init__(self, context: zmq.Context = None):
        self.interface_id: int = None
        self.interface_uid: bytes = None
        self.ctx: zmq.Context = context if context else zmq.Context.instance()
        self._cnt = 0
        self.protocol: Protocol = Protocol.instance()
        self.peer: PeerDescriptor = PeerDescriptor(uuid.uuid1(), os.getpid(), getfqdn())
        self.agent: AgentDescriptor = \
            AgentDescriptor(uuid.UUID('7608dca4-46d3-11e9-8f39-5404a6a1fd6e'),
                            "Saturnin SDK test client", '1.0',
                            VENDOR_UID, 'system/test')
    def get_token(self) -> bytes:
        """Return new FBSP message token from internal counter."""
        self._cnt += 1
        return pack('Q', self._cnt)
    def _raw_handshake(self, socket: zmq.Socket):
        """Raw ZMQ FBSP handshake test."""
        print("Sending HELLO:")
        msg: HelloMessage = self.protocol.create_message_for(MsgType.HELLO, self.get_token())
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
        for api in msg.peer.api:
            if api.uid == self.interface_uid:
                interface_id = api.number
        if interface_id is None:
            raise ClientError("Service does not support required interface")
        self.interface_id = interface_id
        self.process_welcome(msg)
    def _client_handshake(self, client: ServiceClient):
        """Client handshake test."""
        print_session(client.get_session())
    def _run(self, test_names: List[str], *args):
        """Run test methods."""
        test_names.sort()
        start = monotonic()
        for name in test_names:
            try:
                title = '_' + name.lstrip('_')
                print_title(title.replace('_raw_', '').replace('_client_', '').upper())
                test = getattr(self, name)
                test(*args)
            except Exception as exc:
                print_title("FAILED", char="*")
                print(exc)
                #log.exception("Test FAILED")
        print_title("End")
        elapsed = monotonic() - start
        print(f"Ran {len(test_names)} tests in {elapsed} seconds")
    def process_welcome(self, msg: WelcomeMessage):
        """Called by raw handshake to allow processing of WELCOME message by descendants."""
    def create_client(self, channel: Channel) -> ServiceClient:
        """Called to create Service client instance for testing.

Important:
    Abstract method, MUST be overridden in child classes.
"""
        raise NotImplementedError()
    def run_raw_tests(self, endpoint: str, test_names: List[str] = None):
        """Run service tests using raw ZMQ messages."""
        test_list = test_names if test_names else [name for name in dir(self)
                                                   if name.startswith('raw_')]
        test_list.insert(0, '_raw_handshake')
        socket = self.ctx.socket(zmq.DEALER)
        socket.sndtimeo = 100
        socket.LINGER = 1000
        socket.identity = b'test-runner:' + self.peer.uid.hex.encode('ascii')
        socket.connect(endpoint)
        self._run(test_list, socket)
        msg = self.protocol.create_message_for(MsgType.CLOSE, self.get_token())
        socket.send_multipart(msg.as_zmsg())
        socket.close()
    def run_client_tests(self, endpoint: str, test_names: List[str] = None):
        """Run service tests using service client."""
        test_list = test_names if test_names else [name for name in dir(self)
                                                   if name.startswith('client_')]
        test_list.insert(0, '_client_handshake')
        mngr = ChannelManager(self.ctx)
        try:
            chn = DealerChannel(b'test-runner:' + self.peer.uid.hex.encode('ascii'), False)
            mngr.add(chn)
            with self.create_client(chn) as client:
                try:
                    client.open(endpoint)
                except zmq.ZMQError as exc:
                    print_title("ERROR", char="*")
                    print(exc)
                    #log.exception("Test FAILED")
                    raise
                self._run(test_list, client)
        finally:
            mngr.remove(chn)
            chn.close()
            mngr.shutdown()
