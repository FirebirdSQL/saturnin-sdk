# SPDX-FileCopyrightText: 2019-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           examples/dummy/service.py
# DESCRIPTION:    Dummy microservice
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
# pylint: disable=W0201

"""Saturnin SDK examples - Dummy microservice

This microservice does nothing, and is intended for testing of service management machinery.

It's possible to configure the service to fail (raise an exception) during `initialize()`,
`aquire_resources()`, `release_resources()`, `start_activities()` or `stop_activities()`.
"""

from __future__ import annotations
from typing import List
from functools import partial
from firebird.base.logging import get_logger
from saturnin.base import Error
from saturnin.component.micro import MicroService
from .api import DummyConfig, FailOn

# Classes

class MicroDummySvc(MicroService):
    """Implementation of Dummy microservice.
    """
    def initialize(self, config: DummyConfig) -> None:
        """Verify configuration and assemble component structural parts.
        """
        super().initialize(config)
        self.log_context = 'main'
        get_logger(self).info("Initialization...")
        self._fail_on: FailOn = config.fail_on.value
        get_logger(self).info("{fail_on=}", fail_on=self._fail_on.value)
        self._stop_after: List[int] = config.stop_after.value
        get_logger(self).info("{schedule=}", schedule=self._stop_after)
        if self._fail_on is FailOn.INIT:
            raise Error("Service configured to fail")
    def aquire_resources(self) -> None:
        """Aquire resources required by component (open files, connect to other services etc.).

        Must raise an exception when resource aquisition fails.
        """
        get_logger(self).info("Aquiring resources...")
        if self._fail_on is FailOn.RESOURCE_AQUISITION:
            raise Error("Service configured to fail")
    def release_resources(self) -> None:
        """Release resources aquired by component (close files, disconnect from other services etc.)
        """
        get_logger(self).info("Releasing resources...")
        if self._fail_on is FailOn.RESOURCE_RELEASE:
            raise Error("Service configured to fail")
    def start_activities(self) -> None:
        """Start normal component activities.

        Must raise an exception when start fails.
        """
        get_logger(self).info("Starting activities...")
        if self._fail_on is FailOn.ACTIVITY_START:
            raise Error("Service configured to fail")
        if self._stop_after:
            self.schedule(partial(self.action, self._stop_after), self._stop_after)
    def stop_activities(self) -> None:
        """Stop component activities.
        """
        get_logger(self).info("Stopping activities...")
        if self._fail_on is FailOn.ACTIVITY_STOP:
            raise Error("Service configured to fail")
    def action(self, delay: int) -> None:
        """Scheduled action.
        """
        get_logger(self).info("Scheduled action, {delay=}", delay=delay)
        if not self._heap:
            self.stop.set()
