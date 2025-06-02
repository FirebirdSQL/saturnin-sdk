# SPDX-FileCopyrightText: 2019-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           roman/api.py
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

"""Saturnin SDK examples - API definitions for the ROMAN service.

This module defines the API interface (`RomanAPI`), configuration, and descriptors
for the ROMAN service. The service converts Arabic numerals in text data to Roman numerals.

Supported requests:

    :ROMAN: REPLY with altered REQUEST data frames.
"""

from __future__ import annotations

from functools import partial
from uuid import UUID

from saturnin.base import VENDOR_UID, AgentDescriptor, ButlerInterface, ServiceDescriptor, create_config
from saturnin.component.service import ServiceConfig

# It's not an official service, so we can use any UUID constant
SERVICE_UID: UUID = UUID('413f76e8-4662-11e9-aa0d-5404a6a1fd6e')
SERVICE_VERSION: str = '0.2.0'

ROMAN_INTERFACE_UID: UUID = UUID('d0e35134-44af-11e9-b5b8-5404a6a1fd6e')

class RomanAPI(ButlerInterface):
    """Defines the interface and request codes for the ROMAN service.

    Currently, it includes the `ROMAN` request code used to ask the service to perform number conversion.
    """
    ROMAN = 1
    @classmethod
    def get_uid(cls) -> UUID:
        return ROMAN_INTERFACE_UID

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name='saturnin.example.roman',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification='example/service')

SERVICE_API = [RomanAPI]

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=SERVICE_API,
                      description="Sample ROMAN service",
                      facilities=[],
                      factory='saturnin.examples.roman.service:RomanService',
                      config=partial(create_config, ServiceConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
