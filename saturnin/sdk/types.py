#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/types.py
# DESCRIPTION:    Type definitions
# CREATED:        22.4.2019
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

"""Saturnin SDK - Type definitions
"""

from typing import TypeVar, NamedTuple, Optional, Any, List, Tuple
from enum import Enum, IntEnum, Flag, IntFlag, auto
from uuid import UUID
#from typing_extensions import Protocol
from saturnin.sdk import PLATFORM_UID, PLATFORM_VERSION

# Type annotation types

TMessage = TypeVar('TMessage', bound='BaseMessage')
TProtocol = TypeVar('TProtocol', bound='BaseProtocol')
TSession = TypeVar('TSession', bound='BaseSession')
TChannel = TypeVar('TChannel', bound='BaseChannel')
TMessageHandler = TypeVar('TMessageHandler', bound='BaseMessageHandler')
TServiceImpl = TypeVar('TServiceImpl', bound='BaseServiceImpl')
TService = TypeVar('TService', bound='BaseService')
TClient = TypeVar('TClient', bound='ServiceClient')
Token = bytearray
ZMQAddress = bytes
ZMQAddressList = List[ZMQAddress]

# Enums

class Origin(Enum):
    "Origin of received message in protocol context."
    ANY = auto()
    UNKNOWN = ANY
    SERVICE = auto()
    CLIENT = auto()
    PROVIDER = SERVICE
    CONSUMER = CLIENT

class SocketMode(Enum):
    "ZMQ socket mode"
    UNKNOWN = auto()
    BIND = auto()
    CONNECT = auto()

class Direction(Flag):
    "ZMQ socket direction of transmission"
    IN = auto()
    OUT = auto()
    BOTH = OUT | IN

class DependencyType(Enum):
    "Service dependency type"
    OPTIONAL = 0
    REQUIRED = 1
    PREFERRED = 2

class ExecutionMode(Enum):
    "Service execution mode"
    ANY = 0
    THREAD = 1
    PROCESS = 2

class ServiceType(Enum):
    "Service type"
    UNKNOWN = 0
    MEASURING = 1 # Service that collects and pass on data.
    PROCESSING = 2 # Service that takes data on input, process them and have some data on output
    PROVIDER = 3 # Service that does things on request
    CONTROL = 4 # Service that manages other services

class MsgType(IntEnum):
    "FBSP Message Type"
    UNKNOWN = 0
    HELLO = 1  # initial message from client
    WELCOME = 2  # initial message from service
    NOOP = 3  # no operation, used for keep-alive & ping purposes
    REQUEST = 4  # client request
    REPLY = 5  # service response to client request
    DATA = 6  # separate data sent by either client or service
    CANCEL = 7  # cancel request
    STATE = 8  # operating state information
    CLOSE = 9  # sent by peer that is going to close the connection
    ERROR = 31 # error reported by service

class MsgFlag(IntFlag):
    "FBSP message flag"
    NONE = 0
    ACK_REQ = 1
    ACK_REPLY = 2
    MORE = 4


class ErrorCode(IntEnum):
    "FBSP Error Code"
    # Errors indicating that particular request cannot be satisfied
    INVALID_MESSAGE = 1
    NOT_IMPLEMENTED = 2
    BAD_REQUEST = 3
    INTERNAL_SERVICE_ERROR = 4
    TOO_MANY_REQUESTS = 5
    FAILED_DEPENDENCY = 6
    GONE = 7
    CONFLICT = 8
    REQUEST_TIMEOUT = 9
    NOT_FOUND = 10
    FORBIDDEN = 11
    UNAUTHORIZED = 12
    PAYLOAD_TOO_LARGE = 13
    INSUFFICIENT_STORAGE = 14
    PROTOCOL_VIOLATION = 15
    # Fatal errors indicating that connection would/should be terminated
    SERVICE_UNAVAILABLE = 2000
    FBSP_VERSION_NOT_SUPPORTED = 2001

# Named tuples

class InterfaceDescriptor(NamedTuple):
    """Interface descriptor.

Attributes:
    :uid:      Interface ID (UUID).
    :name:     Interface name.
    :revision: Interface revision number.
    :requests: Enum for interface FBSP request codes.
"""
    uid: UUID
    name: str
    revision: int
    requests: IntEnum

class AgentDescriptor(NamedTuple):
    """Service or Client descriptor.

Attributes:
    :uid:              Agent ID (UUID).
    :name:             Agent name.
    :version:          Agent version string.
    :vendor_uid:       Vendor ID (UUID).
    :classification:   Agent classification string.
    :platform_uid:     Butler platform ID (UUID)
    :platform_version: Butler platform version string.
    :supplement:       Optional list of supplemental information.
"""
    uid: UUID
    name: str
    version: str
    vendor_uid: UUID
    classification: str
    platform_uid: UUID = PLATFORM_UID
    platform_version: str = PLATFORM_VERSION
    supplement: Optional[List[Any]] = None

class PeerDescriptor(NamedTuple):
    """Peer descriptor.

Attributes:
    :uid:        Peer ID (UUID).
    :pid:        Peer process ID (int).
    :host:       Host name.
    :supplement: Optional list of supplemental information.
"""
    uid: UUID
    pid: int
    host: str
    supplement: Optional[List[Any]] = None

class ServiceDescriptor(NamedTuple):
    """Service descriptor.

Attributes:
    :agent:          Service agent descriptor.
    :api:            Service API descriptor.
    :dependencies:   List of (DependencyType, UUID) tuples.
    :execution_mode: Preferred execution mode.
    :service_type:   Type of service.
    :description:    Text describing the service.
    :implementation: Locator string for service implementation class.
    :container:      Locator string for service container class.
    :client:         Locator string for service client class.
    :tests:          Locator string for service test class.
"""
    agent: AgentDescriptor
    api: List[InterfaceDescriptor]
    dependencies: List[Tuple[DependencyType, UUID]]
    execution_mode: ExecutionMode
    service_type: ServiceType
    description: str
    implementation: str
    container: str
    client: str
    tests: str

#  Exceptions

class SaturninError(Exception):
    "General exception raised by Saturnin SDK"
class InvalidMessageError(SaturninError):
    "A formal error was detected in a message"
class ChannelError(SaturninError):
    "Transmission channel error"
class ServiceError(SaturninError):
    "Error raised by service"
class ClientError(SaturninError):
    "Error raised by Client"


