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

from uuid import UUID
from functools import partial
from saturnin.core import VENDOR_UID
from saturnin.core.types import Enum, AgentDescriptor, InterfaceDescriptor, \
     ServiceDescriptor, ExecutionMode, ServiceType, ServiceFacilities
from saturnin.core.config import ServiceConfig, create_config

# It's not an official service, so we can use any UUID constants
SERVICE_UID: UUID = UUID('413f76e8-4662-11e9-aa0d-5404a6a1fd6e')
SERVICE_VERSION: str = '0.2'

ROMAN_INTERFACE_UID: UUID = UUID('d0e35134-44af-11e9-b5b8-5404a6a1fd6e')

# Request Codes

class RomanRequest(Enum):
    """Roman Service Request Code"""
    ROMAN = 1

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name='firebird.saturnin.sdk.roman',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification='example/service')

SERVICE_INTERFACE: InterfaceDescriptor = \
    InterfaceDescriptor(uid=ROMAN_INTERFACE_UID,
                        name="Roman service API",
                        revision=1, number=1,
                        requests=RomanRequest)

SERVICE_API = [SERVICE_INTERFACE]

SERVICE_DESCRIPTION: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=SERVICE_API,
                      dependencies=[],
                      execution_mode=ExecutionMode.THREAD,
                      service_type=ServiceType.PROCESSING,
                      facilities=ServiceFacilities.FBSP_SOCKET,
                      description="Sample ROMAN service",
                      implementation='saturnin.sdk.service.roman.service:RomanServiceImpl',
                      container='saturnin.core.classic:SimpleService',
                      config=partial(create_config, ServiceConfig,
                                     '%s_service' % SERVICE_AGENT.name, "ROMAN service."),
                      client='saturnin.sdk.service.roman.client:RomanClient',
                      tests='saturnin.sdk.service.roman.test:TestRunner'
                      )
