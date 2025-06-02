# SPDX-FileCopyrightText: 2023-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin examples
# FILE:           saturnin/examples/apps/print_file/api.py
# DESCRIPTION:    API for Print text file application
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

"""Saturnin examples - API definitions for the Print Text File application.

This module defines constants (UID, version) and the `ApplicationDescriptor`
for the "Print File" application. The application itself prints a text file to the
screen, with optional syntax highlighting.
"""

from __future__ import annotations

import uuid

from saturnin.base import VENDOR_UID, ApplicationDescriptor

# It's not an official application, so we can use any UUID constant
APP_UID: uuid.UUID = uuid.UUID('826ecaca-d3b6-11ed-97b5-5c879cc92822')
APP_VERSION: str = '0.1.0'

# Application description

APP_DESCRIPTOR: ApplicationDescriptor = \
    ApplicationDescriptor(uid=APP_UID,
                          name='saturnin.app.print_file',
                          version=APP_VERSION,
                          vendor_uid=VENDOR_UID,
                          classification='text/print',
                          description="Print text file application",
                          cli_command='saturnin.examples.apps.print_file.application:print_file',
                          recipe_factory='saturnin.examples.apps.print_file.application:create_recipe'
                          )
