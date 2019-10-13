#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/__init__.py
# DESCRIPTION:    Saturnin SDK Package
# CREATED:        21.2.2019
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

"Saturnin SDK Package"

import uuid

# firebird.butler.platform.saturnin-sdk
PLATFORM_OID: str = '1.3.6.1.4.1.53446.1.2.0'
PLATFORM_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, PLATFORM_OID)
PLATFORM_VERSION: str = '0.4.0'

# firebird.butler.vendor.firebird
VENDOR_OID: str = '1.3.6.1.4.1.53446.1.3.0'
VENDOR_UID: uuid.UUID = uuid.uuid5(uuid.NAMESPACE_OID, VENDOR_OID)

