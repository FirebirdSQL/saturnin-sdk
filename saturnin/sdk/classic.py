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

from typing import List, Dict, Any
from uuid import uuid1
from time import sleep
from zmq import Context, POLLIN
from saturnin.sdk.base import ChannelManager, RouterChannel
from saturnin.sdk import fbsp

class DummyEvent:
    """Dummy Event class"""
    def __init__(self):
        self._flag = False
    def is_set(self):
        "Return true if and only if the internal flag is true."
        return self._flag
    isSet = is_set
    def set(self):
        "Set the internal flag to true."
        self._flag = True
    def clear(self):
        "Reset the internal flag to false."
        self._flag = False
    def wait(self, timeout=0):
        "Sleep for specified number of seconds and then return the internal flag state."
        sleep(timeout)
        return self._flag


class SimpleServiceImpl(fbsp.ServiceImpl):
    """Simple Firebird Butler Service implementation.

Attributes:
    :svc_chn: Inbound RouterChannel

Configuration options (retrieved via `get()`):
    :shutdown_linger:  (int) ZMQ Linger value used on shutdown [Default 0].
    :zmq_context: ZMQ context [default: Context.instance()]
    :instance_id: (bytes) Globally unique identification for this service instance
                  [Default uuid1().bytes].
    :stop_event: (Event) instance used to stop the service [Default `DummyEvent`].
    :svc_entrypoints:  Sequence of service entrypoints (ZMQ addresses).
"""
    def __init__(self, stop_event: Any, entrypoints: List[str], remotes: Dict[str, str]):
        super().__init__()
        self.stop_event = stop_event
        self.svc_entrypoints = entrypoints
        self.svc_remotes = remotes
        self.svc_chn: RouterChannel = None
    def initialize(self, svc: fbsp.Service):
        """Performs next actions:
    - Creates `ChannelManager` with shared ZMQ `Context` in service.
    - Creates managed (inbound) `RouterChannel` for service.
    - Creates/sets event to stop the service.
"""
        super().initialize(svc)
        svc.mngr = ChannelManager(self.get('zmq_context', Context.instance()))
        self.svc_chn = RouterChannel(self.get('instance_id', uuid1().bytes))
        svc.mngr.add(self.svc_chn)
        svc.event = self.get('stop_event', DummyEvent())
    def configure(self, svc):
        """Performs next actions:
    - Binds service router channel to specified entrypoints.
"""
        for addr in self.get('svc_entrypoints'):
            self.svc_chn.bind(addr)

class SimpleService(fbsp.Service):
    """Simple Firebird Butler Service.

Has simple Event-controlled I/O loop using `ChannelManager.wait()`. Incomming messages
are processed by `receive()` of channel handler.

Attributes:
    :mngr:         ChannelManager
    :event:        Event instance used to send STOP signal to the service.
    :validate_all: If True, validates all received messages (default False).
    :timeout:      How long it waits for incoming messages (default 1 sec).
"""
    def __init__(self, impl: SimpleServiceImpl):
        super().__init__(impl)
        self.event = None
        self.validate_all = False
        self.timeout = 1000  # 1sec
    def validate(self):
        """Validate that service is properly initialized and configured.

Raises:
    :AssertionError: When any issue is detected.
"""
        super().validate()
        assert hasattr(self.event, 'is_set'), "Event without is_set attribute"
        assert callable(self.event.is_set), "Event is_set is not callable"
    def on_idle(self):
        """Called when wait for messages exceeds timeout. Default implementation
does nothing.
"""
    def run(self):
        """Runs the service until `event` is set.
"""
        while not self.event.is_set():
            events = self.mngr.wait(self.timeout)
            if events:
                for channel, event in events.items():
                    if event == POLLIN:
                        channel.handler.receive()
            else:
                self.on_idle()
