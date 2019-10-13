#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/micro/textio/api.py
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

"""Saturnin SDK examples - API for sample TEXTIO microservice

The TEXTIO microservice transfers data between a file and a Data Pipe.
"""

from uuid import UUID
from functools import partial
from saturnin.sdk import VENDOR_UID
from saturnin.sdk.types import Enum, AgentDescriptor, ServiceDescriptor, \
     ExecutionMode, ServiceType, ServiceFacilities, SocketMode, PipeSocket, \
     SaturninError
from saturnin.sdk.config import create_config, MicroserviceConfig, StrOption, EnumOption, \
     IntOption, BoolOption, ZMQAddressOption, MIMEOption

# It's not an official service, so we can use any UUID constants
SERVICE_UID: UUID = UUID('7fe7a9fe-d60b-11e9-ad9f-5404a6a1fd6e')
SERVICE_VERSION: str = '0.1'

# Configuration

class FileOpenMode(Enum):
    "File open mode"
    READ = Enum.auto()
    CREATE = Enum.auto()
    WRITE = Enum.auto()
    APPEND = Enum.auto()
    RENAME = Enum.auto()

class TextIOConfig(MicroserviceConfig):
    "TextIO service configuration"
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.stop_on_close: BoolOption = \
            self.add_option(BoolOption('stop_on_close', "Stop service when pipe is closed",
                                       default=True))
        self.data_pipe: StrOption = \
            self.add_option(StrOption('data_pipe', "Data Pipe Identification", required=True,
                                      default='readfile'))
        self.pipe_address: ZMQAddressOption = \
            self.add_option(ZMQAddressOption('pipe_address', "Data Pipe endpoint address",
                                             required=True))
        self.pipe_mode: EnumOption = \
            self.add_option(EnumOption('pipe_mode', SocketMode, "Data Pipe Mode",
                                       required=True, default=SocketMode.BIND))
        self.socket_type: EnumOption = \
            self.add_option(EnumOption('socket_type', PipeSocket, "Data Pipe Socket",
                                       required=True, options=(PipeSocket.INPUT,
                                                               PipeSocket.OUTPUT)))
        self.pipe_format: StrOption = \
            self.add_option(MIMEOption('pipe_format', "Pipe data format specification",
                                      required=True, default='text/plain;charset=utf-8'))
        self.pipe_batch_size: IntOption = \
            self.add_option(IntOption('pipe_batch_size', "Data batch size",
                                      required=True, default=50))
        self.file: StrOption = self.add_option(StrOption('file', "File specification",
                                                         required=True))
        self.file_mode: EnumOption = \
            self.add_option(EnumOption('file_mode', FileOpenMode, "File I/O mode",
                                       required=False))
        self.file_format: StrOption = \
            self.add_option(MIMEOption('file_format', "File data format specification",
                                      required=True, default='text/plain;charset=utf-8'))
    def validate(self) -> None:
        "Extended validation"
        super().validate()
        output_modes = [FileOpenMode.READ, FileOpenMode.APPEND]
        input_modes = [FileOpenMode.CREATE, FileOpenMode.WRITE, FileOpenMode.RENAME]
        if self.pipe_mode.value == SocketMode.BIND:
            if (self.socket_type.value == PipeSocket.OUTPUT and self.file_mode.value not in output_modes):
                raise SaturninError("File mode %s not allowed for pipe mode %s"
                                    % (self.file_mode.name, self.socket_type.name))
            elif self.socket_type.value == PipeSocket.INPUT and self.file_mode.value not in input_modes:
                raise SaturninError("File mode %s not allowed for pipe mode %s"
                                    % (self.file_mode.name, self.socket_type.name))
        else:
            if (self.socket_type.value == PipeSocket.INPUT and self.file_mode.value not in output_modes):
                raise SaturninError("File mode %s not allowed for pipe mode %s"
                                    % (self.file_mode.name, self.socket_type.name))
            elif self.socket_type.value == PipeSocket.OUTPUT and self.file_mode.value not in input_modes:
                raise SaturninError("File mode %s not allowed for pipe mode %s"
                                    % (self.file_mode.name, self.socket_type.name))
        if (self.file.value.lower() in ['stdin', 'stdout', 'stderr'] and
            self.file_mode.value not in [FileOpenMode.WRITE, FileOpenMode.READ]):
            raise SaturninError("STD[IN|OUT|ERR] support only READ and WRITE modes")

# Service description

SERVICE_AGENT: AgentDescriptor = \
    AgentDescriptor(uid=SERVICE_UID,
                    name="textio",
                    version=SERVICE_VERSION,
                    vendor_uid=VENDOR_UID,
                    classification="example/microservice")

SERVICE_DESCRIPTION: ServiceDescriptor = \
    ServiceDescriptor(agent=SERVICE_AGENT,
                      api=[],
                      dependencies=[],
                      execution_mode=ExecutionMode.THREAD,
                      service_type=ServiceType.DATA_PROVIDER,
                      facilities=(ServiceFacilities.INPUT_CLIENT | ServiceFacilities.INPUT_SERVER |
                                  ServiceFacilities.OUTPUT_CLIENT | ServiceFacilities.OUTPUT_SERVER),
                      description="Sample TEXTIO microservice",
                      implementation='saturnin.micro.textio.service:TextIOServiceImpl',
                      container='saturnin.sdk.classic:SimpleService',
                      config=partial(create_config, TextIOConfig,
                                     '%s_service' % SERVICE_AGENT.name,
                                     "TEXTIO microservice"),
                      client=None,
                      tests=None)
