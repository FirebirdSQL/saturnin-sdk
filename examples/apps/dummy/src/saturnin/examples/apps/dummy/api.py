# SPDX-FileCopyrightText: 2023-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin examples
# FILE:           saturnin/examples/apps/dummy/api.py
# DESCRIPTION:    API for Test application
# CREATED:        24.2.2023
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
# Copyright (c) 2023 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin examples - API definitions for the Dummy Test application.

This module defines constants (like OID, UID, version) and the `ApplicationDescriptor`
for the dummy test application, which is used for internal development and testing purposes.
"""

from __future__ import annotations

import uuid

from saturnin.base import VENDOR_UID, ApplicationDescriptor

# OID: iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.application.dummy
APP_OID: str = '1.3.6.1.4.1.53446.1.1.0.4.0'
APP_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, APP_OID)
APP_VERSION: str = '0.1.0'

# Application description

APP_DESCRIPTOR: ApplicationDescriptor = \
    ApplicationDescriptor(uid=APP_UID,
                          name='saturnin.app.dummy',
                          version=APP_VERSION,
                          vendor_uid=VENDOR_UID,
                          classification='test/dummy',
                          description="Test dummy application",
                          cli_command='saturnin.examples.apps.dummy.application:dummy_app'
                          )
