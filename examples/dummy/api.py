#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           examples/dummy/api.py
# DESCRIPTION:    API for Dummy microservice
# CREATED:        18.12.2019
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

"""Saturnin SDK examples - API for Dummy microservice

This microservice does nothing, and is intended for testing of service management machinery.

It's possible to configure the service to fail (raise an exception) during `initialize()`,
`aquire_resources()`, `release_resources()`, `start_activities()` or `stop_activities()`.
"""

from __future__ import annotations
import uuid
from enum import Enum, auto
from functools import partial
from firebird.base.config import create_config, EnumOption, ListOption
from saturnin.base import VENDOR_UID, ComponentConfig, pkg_name, AgentDescriptor, ServiceDescriptor

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.dummy
SERVICE_OID: str = '1.3.6.1.4.1.53446.1.2.0.3.0'
SERVICE_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, SERVICE_OID)
SERVICE_VERSION: str = '0.1.0'

class FailOn(Enum):
    NEVER = auto()
    INIT = auto()
    RESOURCE_AQUISITION = auto()
    RESOURCE_RELEASE = auto()
    ACTIVITY_START = auto()
    ACTIVITY_STOP = auto()

# Configuration

class DummyConfig(ComponentConfig):
    """Text file reader microservice configuration.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.fail_on: EnumOption = \
            EnumOption('fail_on', FailOn, "Stage when dummy should raise an exception",
                       default=FailOn.NEVER)
        self.schedule: ListOption = \
            ListOption('schedule', int, "Delays for dummy scheduled actions", default=list())

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="saturnin.micro.dummy",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="test/dummy")

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Test dummy microservice",
                      facilities=[],
                      package=pkg_name(__name__),
                      factory=f'{pkg_name(__name__)}.service:MicroDummySvc',
                      config=partial(create_config, DummyConfig,
                                     f'{SERVICE_AGENT.name}.service'))

