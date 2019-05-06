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

from typing import Sequence
from . import fbsp_pb2 as pb
from .base import BaseService, BaseServiceImpl
from .types import AgentDescriptor, PeerDescriptor, InterfaceDescriptor
from .fbsp import validate_welcome_pb

# Classes

class ServiceImpl(BaseServiceImpl):
    """Base FBSP service implementation.

Attributes:
    :welcome_df:  WelcomeDataframe instance.

Configuration options (retrieved via `get()`):
    :agent:  AgentDescriptor.
    :peer:   PeerDescriptor.
    :api:    List[InterfaceDescriptor]
"""
    def __init__(self):
        super().__init__()
        self.welcome_df: pb.WelcomeDataframe = pb.WelcomeDataframe()
        self.msg_handler = None
        self.agent = None
        self.peer = None
        self.api = []
    def validate(self):
        super().validate()
        assert isinstance(self.get('agent'), AgentDescriptor)
        assert isinstance(self.get('peer'), PeerDescriptor)
        assert isinstance(self.get('api'), Sequence)
        for interface in self.get('api'):
            assert isinstance(interface, InterfaceDescriptor)
    def initialize(self, svc):
        """Partial initialization of FBSP Welcome Data Frame. It does not fill in any
supplement for peer or agent even if they are defined in descriptors.
"""
        agent: AgentDescriptor = self.get('agent')
        peer: PeerDescriptor = self.get('peer')
        self.welcome_df.instance.uid = peer.uid.bytes
        self.welcome_df.instance.pid = peer.pid
        self.welcome_df.instance.host = peer.host
        self.welcome_df.service.uid = agent.uid.bytes
        self.welcome_df.service.name = agent.name
        self.welcome_df.service.version = agent.version
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

class Service(BaseService):
    """Base FBSP service."""
    def validate(self):
        super().validate()
        validate_welcome_pb(self.impl.welcome_df)
