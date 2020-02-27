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

from uuid import UUID
from functools import partial
from saturnin.core import VENDOR_UID
from saturnin.core.types import Enum, AgentDescriptor, InterfaceDescriptor, ServiceDescriptor, \
     DependencyType, ExecutionMode, ServiceType, ServiceFacilities
from saturnin.sdk.service.roman import api as roman_api
from saturnin.core.config import create_config, ServiceConfig, ZMQAddressOption

# It's not an official service, so we can use any UUID constants
SERVICE_UID: UUID = UUID('7e59724e-46a4-11e9-8f39-5404a6a1fd6e')
SERVICE_VERSION: str = '0.3'

ECHO_INTERFACE_UID: UUID = UUID('24580be2-4434-11e9-b528-5404a6a1fd6e')

# Request Codes

class EchoRequest(Enum):
    """Echo Service Request Code"""
    ECHO = 1
    ECHO_ROMAN = 2
    ECHO_MORE = 3
    ECHO_STATE = 4
    ECHO_SYNC = 5
    ECHO_DATA_MORE = 6
    ECHO_DATA_SYNC = 7

# Configuration

class EchoConfig(ServiceConfig):
    """Echo service configuration"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.roman_address: ZMQAddressOption = \
            ZMQAddressOption('roman_address', "ROMAN service address")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name='firebird.saturnin.sdk.echo',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification='example/service')

SERVICE_INTERFACE: InterfaceDescriptor = \
    InterfaceDescriptor(uid=ECHO_INTERFACE_UID,
                        name="Echo service API",
                        revision=1, number=1,
                        requests=EchoRequest)

SERVICE_API = [SERVICE_INTERFACE]

SERVICE_DESCRIPTION: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=SERVICE_API,
                      dependencies=[(DependencyType.PREFERRED, roman_api.SERVICE_INTERFACE.uid)],
                      execution_mode=ExecutionMode.THREAD,
                      service_type=ServiceType.PROCESSING,
                      facilities=ServiceFacilities.FBSP_SOCKET,
                      description="Sample ECHO service",
                      implementation='saturnin.sdk.service.echo.service:EchoServiceImpl',
                      container='saturnin.core.classic:SimpleService',
                      config=partial(create_config, EchoConfig,
                                     '%s_service' % SERVICE_AGENT.name, "ECHO service."),
                      client='saturnin.sdk.service.echo.client:EchoClient',
                      tests='saturnin.sdk.service.echo.test:TestRunner'
                      )
