#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/classic.py
# DESCRIPTION:    Classic Firebird Butler Service
# CREATED:        27.2.2019
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

"""Saturnin SDK - Classic Firebird Butler Service and Client.

Classical services run their own message loop and do not use any asynchronous
programming techniques or Python libraries. Running the service effectively blocks
the main thread so that if the application needs to perform other tasks or if you
need to run multiple services in parallel in one application, each service must be
run in a separate thread or subprocess.
"""

import logging
from typing import Optional, Mapping
from zmq import POLLIN
from .types import TServiceImpl
from .service import Service

# Logger

log = logging.getLogger(__name__)

class SimpleService(Service):
    """Simple Firebird Butler Service.

Has simple Event-controlled I/O loop using `ChannelManager.wait()`. Incomming messages
are processed by `receive()` of channel handler.

Attributes:
    :mngr:    ChannelManager
    :timeout: How long it waits for incoming messages (default 1 sec).
    :remotes: Dictionary of remote service endpoints [interface_uid:addresss]. Initially empty.
"""
    def __init__(self, impl: TServiceImpl):
        super().__init__(impl)
        self.timeout: int = 1000  # 1sec
        self.remotes: Mapping[bytes, str] = {}
    def get_provider_address(self, interface_uid: bytes) -> Optional[str]:
        """Return address of interface provider or None if it's not available."""
        return self.remotes.get(interface_uid)
    def validate(self):
        """Validate that service is properly initialized and configured.

Raises:
    :AssertionError: When any issue is detected.
"""
        log.debug("%s.validate", self.__class__.__name__)
        super().validate()
        for uid, address in self.remotes.items():
            assert isinstance(uid, bytes)
            assert isinstance(address, str)
    def run(self):
        """Runs the service until `stop_event` is set.
"""
        log.info("Service %s:%s started", self.impl.agent.name, self.impl.agent.uid)
        while not self.impl.stop_event.is_set():
            events = self.impl.mngr.wait(self.timeout)
            if events:
                for channel, event in events.items():
                    if event == POLLIN:
                        channel.handler.receive()
            else:
                self.impl.on_idle()
