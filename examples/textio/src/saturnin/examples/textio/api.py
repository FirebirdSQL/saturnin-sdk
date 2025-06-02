# SPDX-FileCopyrightText: 2019-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           textio/api.py
# DESCRIPTION:    API for sample TEXTIO microservice
# CREATED:        13.9.2019
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

"""Saturnin SDK examples - API definitions for the sample TEXTIO microservice.

This module defines the configuration (`TextIOConfig`, `FileOpenMode`), and descriptors
for the TEXTIO microservice. The microservice is designed to transfer data
between a specified file and a Saturnin Data Pipe.
"""

from __future__ import annotations

from enum import IntEnum, auto
from functools import partial
from uuid import UUID

from saturnin.base import (
    VENDOR_UID,
    AgentDescriptor,
    ComponentConfig,
    Error,
    ServiceDescriptor,
    SocketMode,
    create_config,
)

from firebird.base.config import MIME, BoolOption, EnumOption, IntOption, MIMEOption, StrOption, ZMQAddressOption

# It's not an official service, so we can use any UUID constant
SERVICE_UID: UUID = UUID('7fe7a9fe-d60b-11e9-ad9f-5404a6a1fd6e')
SERVICE_VERSION: str = '0.1.0'

# Configuration

class FileOpenMode(IntEnum):
    """File open mode."""
    READ = auto()
    CREATE = auto()
    WRITE = auto()
    APPEND = auto()
    RENAME = auto()

class TextIOConfig(ComponentConfig):
    """Configuration options for the TEXTIO microservice.

    Defines settings related to file operations (filename, mode, format)
    and Data Pipe interactions (address, mode, format, batch size, etc.),
    allowing flexible data transfer between files and pipes.
    """
    def __init__(self, name: str):
        super().__init__(name)
        self.stop_on_close: BoolOption = \
            BoolOption('stop_on_close', "Stop service when pipe is closed", default=True)
        self.data_pipe: StrOption = \
            StrOption('data_pipe', "Data Pipe Identification", required=True,
                      default='readfile')
        self.pipe_address: ZMQAddressOption = \
            ZMQAddressOption('pipe_address', "Data Pipe endpoint address",
                             required=True)
        self.pipe_mode: EnumOption = \
            EnumOption('pipe_mode', SocketMode, "Data Pipe Mode", required=True,
                       default=SocketMode.BIND)
        self.pipe_format: MIMEOption = \
            MIMEOption('pipe_format', "Pipe data format specification", required=True,
                       default=MIME('text/plain;charset=utf-8'))
        self.pipe_batch_size: IntOption = \
            IntOption('pipe_batch_size', "Data batch size", required=True, default=50)
        self.filename: StrOption = \
            StrOption('filename', "File specification", required=True)
        self.file_mode: EnumOption = \
            EnumOption('file_mode', FileOpenMode, "File I/O mode", required=False)
        self.file_format: MIMEOption = \
            MIMEOption('file_format', "File data format specification",
                       required=True, default=MIME('text/plain;charset=utf-8'))
    def validate(self) -> None:
        """Performs extended validation of the configuration.

        Ensures that standard I/O streams (stdin, stdout, stderr) are only used
        with compatible file modes (i.e., READ for stdin, WRITE for stdout/stderr).
        """
        super().validate()
        if (self.filename.value.lower() in ['stdin', 'stdout', 'stderr'] and
            self.file_mode.value not in [FileOpenMode.WRITE, FileOpenMode.READ]):
            raise Error("STD[IN|OUT|ERR] support only READ and WRITE modes")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name='saturnin.example.textio',
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification='example/micro')

SERVICE_DESCRIPTOR: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      description="Sample TEXTIO microservice",
                      facilities=[],
                      factory='saturnin.examples.textio.service:MicroTextIOSvc',
                      config=partial(create_config, TextIOConfig, SERVICE_UID,
                                     f'{SERVICE_AGENT.name}_service'))
