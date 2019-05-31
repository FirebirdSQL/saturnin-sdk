#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/service.py
# DESCRIPTION:    Butler Services
# CREATED:        22.4.2019
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

"""Saturnin SDK - Butler Services
"""

import logging
from typing import Any, Sequence
from zmq import Context
from saturnin.sdk import fbsp_pb2 as pb
from .types import TService, AgentDescriptor, PeerDescriptor, \
     InterfaceDescriptor, InvalidMessageError
from .base import ChannelManager, RouterChannel, BaseService, BaseServiceImpl
from .fbsp import validate_welcome_pb

# Logger

log = logging.getLogger(__name__)

# Classes

class ServiceImpl(BaseServiceImpl):
    """Base FBSP service implementation.

Attributes:
    :welcome_df:  WelcomeDataframe instance.
    :instance_id: R/O property returning Instance UID (from Welcome data frame).

Configuration options (retrieved via `get()`):
    :agent:  AgentDescriptor.
    :peer:   PeerDescriptor.
    :api:    List[InterfaceDescriptor]
"""
    def __init__(self, stop_event: Any):
        log.debug("%s.__init__", self.__class__.__name__)
        super().__init__(stop_event)
        self.welcome_df: pb.WelcomeDataframe = pb.WelcomeDataframe()
        self.msg_handler = None
        self.agent: AgentDescriptor = None
        self.peer: PeerDescriptor = None
        self.api: Sequence[InterfaceDescriptor] = []
    def validate(self) -> None:
        log.debug("%s.validate", self.__class__.__name__)
        super().validate()
        assert isinstance(self.get('agent'), AgentDescriptor)
        assert isinstance(self.get('peer'), PeerDescriptor)
        assert isinstance(self.get('api'), Sequence)
        for interface in self.get('api'):
            assert isinstance(interface, InterfaceDescriptor)
    def initialize(self, svc) -> None:
        """Initialization of FBSP Welcome Data Frame. It does not fill in any
supplement for peer or agent even if they are defined in descriptors.
"""
        log.debug("%s.initialize", self.__class__.__name__)
        agent: AgentDescriptor = self.get('agent')
        peer: PeerDescriptor = self.get('peer')
        self.welcome_df.instance.uid = peer.uid.bytes
        self.welcome_df.instance.pid = peer.pid
        self.welcome_df.instance.host = peer.host
        self.welcome_df.service.uid = agent.uid.bytes
        self.welcome_df.service.name = agent.name
        self.welcome_df.service.version = agent.version
        self.welcome_df.service.classification = agent.classification
        self.welcome_df.service.vendor.uid = agent.vendor_uid.bytes
        self.welcome_df.service.platform.uid = agent.platform_uid.bytes
        self.welcome_df.service.platform.version = agent.platform_version
        i = 1
        for interface in self.get('api'):
            intf = self.welcome_df.api.add()
            intf.number = i
            intf.uid = interface.uid.bytes
            i += 1

    instance_id: bytes = property(lambda self: self.welcome_df.instance.uid,
                                  doc="Service instance identification")

class SimpleServiceImpl(ServiceImpl):
    """Simple FBSP Service implementation.

Uses one RouterChannel to handle all service clients.

Attributes:
    :svc_chn: Inbound RouterChannel

Configuration options (retrieved via `get()`):
    :shutdown_linger:  (int) ZMQ Linger value used on shutdown [Default 0].
    :zmq_context: ZMQ context [default: Context.instance()]
"""
    def __init__(self, stop_event: Any):
        super().__init__(stop_event)
        self.svc_chn: RouterChannel = None
    def initialize(self, svc: TService) -> None:
        """Performs next actions:

    - Creates `ChannelManager` with shared ZMQ `Context` in service.
    - Creates managed (inbound) `RouterChannel` for service.
    - Creates/sets event to stop the service.
"""
        log.debug("%s.initialize", self.__class__.__name__)
        super().initialize(svc)
        self.mngr = ChannelManager(self.get('zmq_context', Context.instance()))
        self.svc_chn = RouterChannel(self.instance_id)
        self.mngr.add(self.svc_chn)
    def configure(self, svc: TService) -> None:
        """Performs next actions:
    - Binds service router channel to specified endpoints.
"""
        log.debug("%s.configure", self.__class__.__name__)
        real_endpoints = []
        for addr in self.endpoints:
            real_endpoints.append(self.svc_chn.bind(addr))
        self.endpoints = real_endpoints

class Service(BaseService):
    """Base FBSP service.

Validates that service implementation has properly derfined and configured WELCOME data frame.

Abstract methods:
    :run: Runs the service.
"""
    def validate(self) -> None:
        """Validate that service is properly initialized and configured.

Raises:
    :AssertionError: When any issue is detected.
"""
        log.debug("%s.validate", self.__class__.__name__)
        super().validate()
        try:
            validate_welcome_pb(self.impl.welcome_df)
        except InvalidMessageError as exc:
            raise AssertionError() from exc
