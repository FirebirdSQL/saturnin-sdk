#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/client.py
# DESCRIPTION:    Butler Service Clients
# CREATED:        2.5.2019
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

"""Saturnin SDK - Butler Service Clients
"""

import logging
from typing import Dict
from saturnin.sdk import fbsp_pb2 as pb
#from .base import BaseService, BaseServiceImpl
from .types import TChannel, TSession, ClientError, AgentDescriptor, \
     PeerDescriptor, InterfaceDescriptor
from .fbsp import MsgType, WelcomeMessage, ClientMessageHandler, \
     validate_hello_pb

# Logger

log = logging.getLogger(__name__)

# Classes

class ServiceClient(ClientMessageHandler):
    """Base Service Client

Attributes:
    :interface_id:  Number assigned by service to interface used by client or None.

Abstract methods:
    :get_handlers:  Returns Dict for mapping FBSP messages sent by service to handler methods.
    :get_interface: Returns descriptor for service interface used by client.
"""
    def __init__(self, chn: TChannel, peer: PeerDescriptor, agent: AgentDescriptor):
        log.debug("%s.__init__", self.__class__.__name__)
        super().__init__(chn)
        self.hello_df: pb.HelloDataframe = pb.HelloDataframe()
        self.peer: PeerDescriptor = peer
        self.agent: AgentDescriptor = agent
        self.interface_id = None
        self.__handlers: Dict = None
    def on_welcome(self, session: TSession, msg: WelcomeMessage) -> None:
        """Handle WELCOME message.

Save WELCOME message into session.greeting, or raise `ServiceError` for unexpected WELCOME.
"""
        log.debug("%s.on_welcome", self.__class__.__name__)
        super().on_welcome(session, msg)
        intf_uid = self.get_interface().uid.bytes
        interface_id = None
        for api in msg.peer.api:
            if api.uid == intf_uid:
                interface_id = api.number
        if interface_id is None:
            raise ClientError("Service does not support required interface")
        self.interface_id = interface_id
        if self.__handlers is None:
            self.__handlers = self.handlers.copy()
        self.handlers = self.__handlers.copy()
        self.handlers.update(self.get_handlers(interface_id))
    def get_interface(self) -> InterfaceDescriptor:
        """Returns descriptor for service interface used by client."""
        raise NotImplementedError()
    def get_handlers(self, api_number: int) -> Dict:
        """Returns Dict for mapping FBSP messages sent by service to handler methods."""
        raise NotImplementedError()
    def open(self, endpoint: str, timeout: int = 1000) -> bool:
        """Opens connection to service.

Arguments:
    :endpoint: Service address.
    :timeout:  The timeout (in milliseconds) to wait for response from service. Value None
    means no time limit. [Defailt: 1000]

Returns:
    True if service was sucessfuly connected in specified time limit.
"""
        log.debug("%s.open", self.__class__.__name__)
        self.connect_peer(endpoint)
        token = self.new_token()
        hello = self.protocol.create_message_for(MsgType.HELLO, token)
        self.hello_df.instance.uid = self.peer.uid.bytes
        self.hello_df.instance.pid = self.peer.pid
        self.hello_df.instance.host = self.peer.host
        self.hello_df.client.uid = self.agent.uid.bytes
        self.hello_df.client.name = self.agent.name
        self.hello_df.client.version = self.agent.version
        self.hello_df.client.vendor.uid = self.agent.vendor_uid.bytes
        self.hello_df.client.platform.uid = self.agent.platform_uid.bytes
        self.hello_df.client.platform.version = self.agent.platform_version
        validate_hello_pb(self.hello_df)
        hello.peer.CopyFrom(self.hello_df)
        self.send(hello)
        return self.get_response(token, timeout)

