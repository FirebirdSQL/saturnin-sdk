#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/fbsp.py
# DESCRIPTION:    Reference implementation of Firebird Butler Service Protocol
#                 See https://firebird-butler.readthedocs.io/en/latest/rfc/4/FBSP.html
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

"""Saturnin SDK - Reference implementation of Firebird Butler Service Protocol.

See https://firebird-butler.readthedocs.io/en/latest/rfc/4/FBSP.html
"""
# pylint: disable=C0302

from typing import List, Dict, Sequence, Optional, Union
from uuid import UUID, uuid5, uuid1, NAMESPACE_OID
from struct import pack, unpack
from enum import Enum, IntEnum, IntFlag
from time import monotonic
from os import getpid
import zmq
from . import fbsp_pb2 as pb
from .base import PLATFORM_UID, PLATFORM_VERSION, VENDOR_UID, InvalidMessageError, \
     ServiceError, Origin, BaseMessage, BaseProtocol, BaseSession, BaseHandler, \
     BaseChannel, BaseService, BaseServiceImpl, get_unique_key, peer_role

PROTOCOL_OID = '1.3.6.1.4.1.53446.1.5.0' # firebird.butler.protocol.fbsp
PROTOCOL_UID = uuid5(NAMESPACE_OID, PROTOCOL_OID)
PROTOCOL_REVISION = 1

# Message header
HEADER_FMT_FULL = '!4sBBH8s'
HEADER_FMT = '!4xBBH8s'
FOURCC = b'FBSP'
VERSION_MASK = 7
ERROR_TYPE_MASK = 31

# Enums

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

class Flag(IntFlag):
    "FBSP message flag"
    ACK_REQ = 1
    ACK_REPLY = 2
    MORE = 4

class RequestCode(IntEnum):
    "FBSP Request Code"
    ILLEGAL = 0
    SVC_ABILITIES = 1
    SVC_CONFIG = 2
    SVC_STATE = 3
    SVC_SET_CONFIG = 4
    SVC_SET_STATE = 5
    SVC_CONTROL = 6
    # Reserved 7..19
    CON_REPEAT = 20
    CON_CONFIG = 21
    CON_STATE = 22
    CON_SET_CONFIG = 23
    CON_SET_STATE = 24
    CON_CONTROL = 25
    # Reserved 26..999

class ErrorCode(IntEnum):
    "FBSP Error Code"
    # Errors indicating that particular request cannot be satisfied
    BAD_REQUEST = 1
    NOT_IMPLEMENTED = 2
    PROTOCOL_VERSION_NOT_SUPPORTED = 3
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
    INVALID_MESSAGE = 15
    PROTOCOL_VIOLATION = 16
    # Fatal errors indicating that connection would/should be terminated
    SERVICE_UNAVAILABLE = 2000
    FBSP_VERSION_NOT_SUPPORTED = 2001

# Protocol Buffer Enums
class DataHandlerType(IntEnum):
    "protobuf DataHandlerType enum as IntEnum"
    NONE = pb.NONE
    B_PROVIDER = pb.B_PROVIDER
    B_CONSUMER = pb.CONSUMER
    C_PROVIDER = pb.C_PROVIDER
    C_CONSUMER = pb.C_CONSUMER
    PUBLISHER = pb.PUBLISHER
    SUBSCRIBER = pb.SUBSCRIBER
    FAN_IN = pb.FAN_IN
    FAN_OUT = pb.FAN_OUT

class ServiceHandlerType(IntEnum):
    "protobuf ServiceHandlerType enum as IntEnum"
    ILLEGAL = pb.ILLEGAL
    PROVIDER = pb.PROVIDER
    CONSUMER = pb.CONSUMER

class State(IntEnum):
    "protobuf State enum as IntEnum"
    UNKNOWN = pb.UNKNOWN
    READY = pb.READY
    RUNNING = pb.RUNNING
    WAITING = pb.WAITING
    SUSPENDED = pb.SUSPENDED
    FINISHED = pb.FINISHED
    ABORTED = pb.ABORTED
    CREATED = pb.CREATED
    BLOCKED = pb.BLOCKED
    STOPPED = pb.STOPPED

# Protocol Buffer (fbsp.proto) validators

def __invalid_if(expr: bool, protobuf: str, field: str) -> None:
    """Raise InvalidMessage exception when expr is True."""
    if expr:
        raise InvalidMessageError("Missing required field '%s.%s'" % (protobuf, field))

def validate_vendor_id_pb(pbo: pb.VendorId) -> None:
    "Validate fbsp.VendorId protobuf. Raises InvalidMessage for missing required fields."
    name = "VendorId"
    __invalid_if(pbo.uid == 0, name, "uid")

def validate_platform_id_pb(pbo: pb.PlatformId) -> None:
    "Validate fbsp.PlatformId protobuf. Raises InvalidMessage for missing required fields."
    name = "PlatformId"
    __invalid_if(pbo.uid == 0, name, "uid")
    __invalid_if(pbo.version == 0, name, "version")

def validate_agent_id_pb(pbo: pb.AgentIdentification) -> None:
    "Validate fbsp.AgentIdentification protobuf. Raises InvalidMessage for missing required fields."
    name = "AgentIdentification"
    __invalid_if(pbo.uid == 0, name, "uid")
    __invalid_if(pbo.name == 0, name, "name")
    __invalid_if(pbo.version == 0, name, "version")
    __invalid_if(not pbo.HasField('fbsp'), name, "fbsp")
    __invalid_if(not pbo.HasField('protocol'), name, "protocol")
    __invalid_if(not pbo.HasField('vendor'), name, "vendor")
    __invalid_if(not pbo.HasField('platform'), name, "platform")
    validate_protocol_pb(pbo.fbsp)
    validate_protocol_pb(pbo.protocol)
    validate_vendor_id_pb(pbo.vendor)
    validate_platform_id_pb(pbo.platform)

def validate_peer_id_pb(pbo: pb.PeerIdentification) -> None:
    "Validate fbsp.PeerIdentification protobuf. Raises InvalidMessage for missing required fields."
    name = "PeerIdentification"
    __invalid_if(len(pbo.uid) == 0, name, "uid")
    __invalid_if(len(pbo.host) == 0, name, "host")
    __invalid_if(pbo.pid == 0, name, "pid")
    __invalid_if(not pbo.HasField('identity'), name, "identity")
    validate_agent_id_pb(pbo.identity)

def validate_error_desc_pb(pbo: pb.ErrorDescription) -> None:
    "Validate fbsp.ErrorDescription protobuf. Raises InvalidMessage for missing required fields."
    name = "ErrorDescription"
    __invalid_if(pbo.code == 0, name, "code")
    __invalid_if(len(pbo.description) == 0, name, "description")

def validate_cancel_req_pb(pbo: pb.CancelRequests) -> None:
    "Validate fbsp.CancelRequests protobuf. Raises InvalidMessage for missing required fields."
    name = "CancelRequests"
    __invalid_if(len(pbo.token) == 0, name, "token")

def validate_protocol_pb(pbo: pb.ProtocolDescription) -> None:
    "Validate fbsp.ProtocolDescription protobuf. Raises InvalidMessage for missing required fields."
    name = "ProtocolDescription"
    __invalid_if(len(pbo.uid) == 0, name, "uid")
    __invalid_if(len(pbo.version) == 0, name, "version")

def validate_service_ability(pbo: pb.ServiceAbility) -> None:
    "Validate fbsp.ServiceAbility protobuf. Raises InvalidMessage for missing required fields."
    name = "ServiceAbility"
    __invalid_if(pbo.service_type == 0, name, "service_type")
    __invalid_if(len(pbo.data_handler) == 0, name, "data_handler")
    __invalid_if(len(pbo.protocol) == 0, name, "protocol")
    validate_protocol_pb(pbo.protocol)

def validate_rep_svc_abilities_pb(pbo: pb.ReplySvcAbilities) -> None:
    "Validate fbsp.ReplySvcAbilities protobuf. Raises InvalidMessage for missing required fields."
    name = "ReplySvcAbilities"
    __invalid_if(not pbo.HasField('service_state'), name, "service_state")
    __invalid_if(not pbo.HasField('service_config'), name, "service_config")
    __invalid_if(not pbo.HasField('service_control'), name, "service_control")
    validate_protocol_pb(pbo.service_state)
    validate_protocol_pb(pbo.service_config)
    validate_protocol_pb(pbo.service_control)
    for ability in pbo.abilities:
        validate_service_ability(ability)

def validate_rq_con_repeat_pb(pbo: pb.ReqestConRepeat) -> None:
    "Validate fbsp.ReqestConRepeat protobuf. Raises InvalidMessage for missing required fields."
    name = "ReqestConRepeat"
    __invalid_if(pbo.last == 0, name, "last")

# Functions

def msg_bytes(msg: Union[bytes, bytearray, zmq.Frame]) -> bytes:
    "Return message frame as bytes."
    return msg.bytes if isinstance(msg, zmq.Frame) else msg

def enum_name_only(value: Enum) -> str:
    "Returns name of enum value without class name."
    name = str(value)
    return name[len(value.__class__.__name__)+1:]

def enum_name(value: Enum) -> str:
    "Returns name of enum value without class name."
    name = repr(value)
    return name[len(value.__class__.__name__)+2:-1]
# Base Message Classes

class Message(BaseMessage):
    """Base FBSP Message.

Attributes:
    :msg_type:  Type of message (int)
    :header:    FBSP control frame (bytes)
    :flasg:     flags (int)
    :type_data: Data associated with message (int)
    :token:     Message token (bytes)
    :data:      List of data frames
"""
    def __init__(self, protocol):
        """
Arguments:
    :protocol: `Protocol` instance that created the message.
"""
        super().__init__(protocol)
        self.message_type: MsgType = MsgType.UNKNOWN
        self.type_data = 0
        self.flags = Flag(0)
        self.token = bytearray(8)
    def _unpack_data(self) -> None:
        """Called when all fields of the message are set. Usefull for data deserialization."""
    def _pack_data(self, frames: list) -> None:
        """Called when serialization is requested."""
    def _get_printout_ex(self) -> str: # pylint: disable=R0201
        "Called for printout of attributes defined by descendant classes."
        return ""
    def from_zmsg(self, frames: Sequence) -> None:
        _, flags, self.type_data, self.token = unpack(HEADER_FMT, frames[0])
        self.flags = Flag(flags)
        self.data = frames[1:]  # First frame is a control frame
        self._unpack_data()
    def as_zmsg(self) -> Sequence:
        zmsg = []
        zmsg.append(self.get_header())
        self._pack_data(zmsg)
        zmsg.extend(self.data)
        return zmsg
    def get_header(self) -> bytes:
        """Return message header (FBSP control frame)."""
        return pack(HEADER_FMT_FULL, FOURCC, (self.message_type << 3) | PROTOCOL_REVISION,
                    self.flags, self.type_data, self.token)
    def has_more(self) -> bool:
        """Returns True if message has MORE flag set."""
        return Flag.MORE in self.flags
    def has_ack_req(self) -> bool:
        """Returns True if message has ACK_REQ flag set."""
        return Flag.ACK_REQ in self.flags
    def has_ack_reply(self) -> bool:
        """Returns True if message has ASK_REPLY flag set."""
        return Flag.ACK_REPLY in self.flags
    def set_flag(self, flag: Flag) -> None:
        """Set flag specified by `flag` mask."""
        self.flags |= flag
    def clear_flag(self, flag: Flag) -> None:
        """Clear flag specified by `flag` mask."""
        self.flags &= ~flag
    def clear(self) -> None:
        """Clears message attributes."""
        super().clear()
        self.token = bytearray(8)
        self.type_data = 0
        self.flags = Flag(0)
    def shall_ack(self) -> bool:
        """Returns True if message must be acknowledged."""
        return self.has_ack_req() and self.message_type in (MsgType.NOOP, MsgType.REQUEST,
                                                            MsgType.REPLY, MsgType.DATA,
                                                            MsgType.STATE, MsgType.CANCEL)
    @classmethod
    def validate_cframe(cls, zmsg: Sequence) -> None:
        """Verifies that first frame in sequence has valid structure of FBSP control
frame."""
        if not zmsg:
            raise InvalidMessageError("Empty message")
        fbsp_header = msg_bytes(zmsg[0])
        if len(fbsp_header) != 16:
            raise InvalidMessageError("Message header must be 16 bytes long")
        try:
            fourcc, control_byte, flags, _ = unpack('!4sBB10s', fbsp_header)
        except Exception as exp:
            raise InvalidMessageError("Can't parse the control frame") from exp
        if fourcc != FOURCC:
            raise InvalidMessageError("Invalid FourCC")
        if (control_byte & VERSION_MASK) != PROTOCOL_REVISION:
            raise InvalidMessageError("Invalid protocol version")
        if (flags | 7) > 7:
            raise InvalidMessageError("Invalid flags")
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        """Verifies that sequence of ZMQ zmsg frames is a valid FBSP base message.

It validates only FBSP Control Frame. FBSP Data Frames are validated in child classes.
This method does not consider the Origin of the ZMQ message (see :meth:`Protocol.validate()`).

Arguments:
    :zmsg: Sequence of ZMQ message frames for validation.

Raises:
    :InvalidMessageError: When formal error is detected in first zmsg frame.
"""
        cls.validate_cframe(zmsg)
        (control_byte, type_data) = unpack('!4xBxH8x', msg_bytes(zmsg[0]))
        message_type = control_byte >> 3
        if (message_type in (MsgType.REQUEST, MsgType.STATE)) and (type_data == 0):
            raise InvalidMessageError("Zero Request Code not allowed for REQUEST & STATE messages")
        if (message_type == MsgType.ERROR) and (type_data >> 5 == 0):
            raise InvalidMessageError("Zero Error Code not allowed")
        if (message_type == MsgType.ERROR) and ((type_data & ERROR_TYPE_MASK)
                                                not in (MsgType.HELLO, MsgType.NOOP,
                                                        MsgType.REQUEST, MsgType.DATA,
                                                        MsgType.CANCEL, MsgType.CLOSE)):
            raise InvalidMessageError("Invalid Request Code '%d' for ERROR message"
                                      % (type_data & ERROR_TYPE_MASK))
    def get_printout(self) -> str:
        """Returns printable, multiline representation of message.
"""
        lines = [f"Message type: {enum_name(self.message_type)}",
                 f"Flags: {enum_name_only(self.flags)}",
                 f"Type data: {self.type_data}",
                 f"Token: {unpack('Q',self.token)[0]}"
                ]
        extra = self._get_printout_ex()
        if extra:
            lines.extend(extra.strip().split('\n'))
        lines.append(f"# data frames: {len(self.data)}")
        if self.data:
            for index, frame in enumerate(self.data, 1):
                lines.append(f"{index}: {frame}")
        return "\n".join(lines)
    #def print(self, indent: int = 4) -> None:
        #"Print message"
        #print('\n'.join(('%s%s' % (' ' * indent, line) for line
                         #in self.get_printout().split('\n'))))
        #print('    ' + '~' * 76)

class HandshakeMessage(Message):
    """FBSP client/service handshake message (HELLO or WELCOME).
    The message includes basic information about the Peer.
"""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.peer = pb.PeerIdentification()
    def _unpack_data(self) -> None:
        self.peer.ParseFromString(self.data.pop(0))
    def _pack_data(self, frames: list) -> None:
        frames.append(self.peer.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        # protobuf returns UUIDs as ugly escaped strings
        # we prefer standard UUID string format
        lines = []
        for line in str(self.peer).splitlines():
            if line.strip().startswith('uid:'):
                i = line.split('"')
                uuid = UUID(bytes=eval(f'b"{i[1]}"')) # pylint: disable=W0123
                line = line.replace(i[1], str(uuid))
            lines.append(line)
        return "Peer:\n%s" % '\n'.join(lines)
    def clear(self) -> None:
        super().clear()
        self.peer.Clear()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        try:
            frame = pb.PeerIdentification()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_peer_id_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for HELLO or WELCOME") from exc

class HelloMessage(HandshakeMessage):
    """The HELLO message is a Client request to open a Connection to the Service.
    The message includes basic information about the Client and Connection parameters
    required by the Client."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.HELLO

class WelcomeMessage(HandshakeMessage):
    """The WELCOME message is the response of the Service to the HELLO message sent by the Client,
    which confirms the successful creation of the required Connection and announces basic parameters
    of the Service and the Connection."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.WELCOME

class NoopMessage(Message):
    """The NOOP message means no operation.
    It’s intended for keep alive purposes and peer availability checks."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.NOOP
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        if len(zmsg) > 1:
            raise InvalidMessageError("Data frames not allowed for NOOP")

class RequestMessage(Message):
    """The REQUEST message is a Client request to the Service."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.REQUEST
    def __get_reqest_code(self) -> IntEnum:
        return self._pr().get_request_code(self.type_data)
    def __set_reqest_code(self, value: int) -> None:
        self.type_data = value
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        return f"Request code: {enum_name(self.request_code)}"
    request_code: int = property(__get_reqest_code, __set_reqest_code, doc="Request Code")

class ReplyMessage(Message):
    """The REPLY message is a Service reply to the REQUEST message previously sent by Client."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.REPLY
    def __get_reqest_code(self) -> IntEnum:
        return self._pr().get_request_code(self.type_data)
    def __set_reqest_code(self, value: int) -> None:
        self.type_data = value
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        return f"Request code: {enum_name(self.request_code)}"
    request_code: int = property(__get_reqest_code, __set_reqest_code, doc="Request Code")

class DataMessage(Message):
    """The DATA message is intended for delivery of arbitrary data between connected peers."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.DATA

class CancelMessage(Message):
    """The CANCEL message represents a request for a Service to stop processing the previous
    request from the Client."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.CANCEL
        self.cancel_reqest = pb.CancelRequests()
    def _unpack_data(self) -> None:
        self.cancel_reqest.ParseFromString(msg_bytes(self.data.pop(0)))
    def _pack_data(self, frames: list) -> None:
        frames.append(self.cancel_reqest.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        return f"Cancel request:\n{self.cancel_reqest}"
    def clear(self) -> None:
        super().clear()
        self.cancel_reqest.Clear()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        if len(zmsg) > 2:
            raise InvalidMessageError("CANCEL must have exactly one data frame")
        try:
            frame = pb.CancelRequests()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_cancel_req_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for CANCEL") from exc

class StateMessage(Message):
    """The STATE message is sent by Service to report its operating state to the Client."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.STATE
        self._state = pb.StateInformation()
    def __get_state(self) -> State:
        return State(self._state.state)
    def __set_state(self, value: State) -> None:
        self._state.state = value
    def __get_reqest_code(self) -> IntEnum:
        return self._pr().get_request_code(self.type_data)
    def __set_reqest_code(self, value: int) -> None:
        self.type_data = value
    def _unpack_data(self) -> None:
        self._state.ParseFromString(msg_bytes(self.data.pop(0)))
    def _pack_data(self, frames: list) -> None:
        frames.append(self._state.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        lines = [f"State: {enum_name(self.state)}",
                 f"Request code: {enum_name(self.request_code)}"
                ]
        return '\n'.join(lines)
    def clear(self) -> None:
        super().clear()
        self._state.Clear()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        if len(zmsg) > 2:
            raise InvalidMessageError("STATE must have exactly one data frame")
        try:
            frame = pb.StateInformation()
            frame.ParseFromString(msg_bytes(zmsg[1]))
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for STATE") from exc

    request_code: int = property(__get_reqest_code, __set_reqest_code, doc="Request Code")
    state: State = property(__get_state, __set_state, doc="Service state")

class CloseMessage(Message):
    """The CLOSE message notifies the receiver that sender is going to close the Connection."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.CLOSE

class ErrorMessage(Message):
    """The ERROR message notifies the Client about error condition detected by Service."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.message_type = MsgType.ERROR
        self.errors = []
    def __get_error_code(self) -> IntEnum:
        return self._pr().get_error_code(self.type_data >> 5)
    def __set_error_code(self, value: IntEnum) -> None:
        self.type_data = (value << 5) | (self.type_data & ERROR_TYPE_MASK)
    def __get_relates_to(self) -> MsgType:
        return MsgType(self.type_data & ERROR_TYPE_MASK)
    def __set_relates_to(self, value: MsgType) -> None:
        self.type_data &= ~ERROR_TYPE_MASK
        self.type_data |= value
    def _unpack_data(self) -> None:
        while self.data:
            err = pb.ErrorDescription()
            err.ParseFromString(msg_bytes(self.data.pop(0)))
            self.errors.append(err)
    def _pack_data(self, frames: list) -> None:
        for err in self.errors:
            frames.append(err.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        lines = [f"Error code: {enum_name(self.error_code)}",
                 f"Relates to: {enum_name(self.relates_to)}",
                 f"# Error frames: {len(self.errors)}",
                ]
        for index, err in enumerate(self.errors, 1):
            lines.append(f"@{index}:")
            lines.append(f"{err}")
        return '\n'.join(lines)
    def clear(self) -> None:
        super().clear()
        self.errors.clear()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        frame = pb.ErrorDescription()
        for i, segment in enumerate(zmsg[1:]):
            try:
                frame.ParseFromString(msg_bytes(segment))
                validate_error_desc_pb(frame)
                frame.Clear()
            except Exception as exc:
                raise InvalidMessageError("Invalid data frame %d for ERROR" % i) from exc
    def add_error(self) -> pb.ErrorDescription:
        "Return newly created ErrorDescription associated with message."
        frame = pb.ErrorDescription()
        self.errors.append(frame)
        return frame

    error_code: IntEnum = property(fget=__get_error_code, fset=__set_error_code,
                                   doc="Error code")
    relates_to: MsgType = property(fget=__get_relates_to, fset=__set_relates_to,
                                   doc="Message type this error relates to")

# Extended Request Messages

class RequestConRepeat(RequestMessage):
    """The REQUEST/CON_REPEAT message is a Client request to the Service that
    shall repeat last message(s) sent."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.repeat = pb.ReqestConRepeat()
    def _unpack_data(self):
        self.repeat.ParseFromString(msg_bytes(self.data.pop(0)))
    def _pack_data(self, frames: list) -> None:
        frames.append(self.repeat.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        return f"Repeat:\n{self.repeat}"
    def clear(self):
        super().clear()
        self.repeat.Clear()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        try:
            frame = pb.ReqestConRepeat()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_rq_con_repeat_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for REQUEST/CON_REPEAT") from exc

# Extended Reply Messages

class ReplySvcAbilities(ReplyMessage):
    """The REPLY/SVC_ABILITIES message contains Service abilities."""
    def __init__(self, protocol):
        super().__init__(protocol)
        self.abilities = pb.ReplySvcAbilities()
    def _unpack_data(self):
        self.abilities.ParseFromString(msg_bytes(self.data.pop(0)))
    def _pack_data(self, frames: list) -> None:
        frames.append(self.abilities.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        return f"Abilities:\n{self.abilities}"
    def clear(self):
        super().clear()
        self.abilities.Clear()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        try:
            frame = pb.ReplySvcAbilities()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_rep_svc_abilities_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for REPLY/SVC_ABILITIES") from exc

# Session, Protocol and Message Handlers

class Session(BaseSession):
    """FBSP session. Contains information about peer.

Attributes:
    :greeting: `HandshakeMessage` received from peer.
    :peer_id:  Unique peer ID.
    :host:     Host identification
    :pid:      Process ID
    :agent_id: Unique Agent ID
    :name:     Agent name assigned by vendor
    :version:  Agent version
    :vendor:   Unique vendor ID
    :platform: Unique platform ID
    :platform_version: Platform version
    :classification: Agent classification
    :requests: List of stored RequestMessages
"""
    def __init__(self, routing_id: bytes):
        super().__init__(routing_id)
        self.greeting = None
        self._handles: Dict[int, RequestMessage] = {}
        self._requests: Dict[bytes, RequestMessage] = {}
    def get_handle(self, msg: RequestMessage) -> int:
        """Create new `handle` for request message.

The `handle` is unsigned short integer value that could be used to retrieve the message
from internal storage via :meth:`get_request()`. The message must be previously stored
in session with :meth:`note_request()`. Handle could be used in protocols that use DATA
messages send by client to assiciate them with particular request (handle is passed in
`type_data` field of DATA message).

Returns:
    Message handle.
"""
        assert msg.token in self._requests
        msg = self._requests[msg.token]
        if hasattr(msg, 'handle'):
            hnd = getattr(msg, 'handle')
        else:
            hnd = get_unique_key(self._handles)
            self._handles[hnd] = msg
            setattr(msg, 'handle', hnd)
        return hnd
    def is_handle_valid(self, hnd: int) -> bool:
        "Returns True if handle is valid."
        return hnd in self._handles
    def get_request(self, token: bytes = None, handle: int = None) -> RequestMessage:
        """Returns stored RequestMessage with given `token` or `handle`."""
        assert ((handle is not None) and (handle in self._handles) or
                (token is not None) and (token in self._requests))
        if token is None:
            msg = self._handles[handle]
        else:
            msg = self._requests[token]
        return msg
    def note_request(self, msg: RequestMessage) -> int:
        """Stores REQUEST message into session for later use.

It uses message `token` as key to request data store.
"""
        self._requests[msg.token] = msg
    def request_done(self, request: Union[bytes, RequestMessage]):
        """Removes REQUEST message from session.

Arguments:
    :request: `RequestMessage` instance or `token` associated with request message.
"""
        key = request.token if isinstance(request, Message) else request
        assert key in self._requests
        msg = self._requests[key]
        if hasattr(msg, 'handle'):
            del self._handles[getattr(msg, 'handle')]
            delattr(msg, 'handle')
        del self._requests[key]

    requests: List = property(lambda self: self._requests.values())
    peer_id: bytes = property(lambda self: UUID(bytes=self.greeting.peer.uid))
    host: str = property(lambda self: self.greeting.peer.host)
    pid: int = property(lambda self: self.greeting.peer.pid)
    agent_id: bytes = property(lambda self: UUID(bytes=self.greeting.peer.identity.uid))
    name: str = property(lambda self: self.greeting.peer.identity.name)
    version: str = property(lambda self: self.greeting.peer.identity.version)
    vendor: bytes = property(lambda self: UUID(bytes=self.greeting.peer.identity.vendor.uid))
    platform: bytes = property(lambda self: UUID(bytes=self.greeting.peer.identity.platform.uid))
    platform_version: str = property(lambda self: self.greeting.peer.identity.platform.version)
    classification: str = property(lambda self: self.greeting.peer.identity.classification)

class Protocol(BaseProtocol):
    """4/FBSP - Firebird Butler Service Protocol
    """
    ORIGIN_MESSAGES = {Origin.SERVICE: (MsgType.ERROR, MsgType.WELCOME, MsgType.NOOP,
                                        MsgType.REPLY, MsgType.DATA, MsgType.STATE,
                                        MsgType.CLOSE),
                       Origin.CLIENT: (MsgType.HELLO, MsgType.NOOP, MsgType.REQUEST,
                                       MsgType.CANCEL, MsgType.DATA, MsgType.CLOSE)
                      }
    VALID_ACK = (MsgType.NOOP, MsgType.REQUEST, MsgType.REPLY, MsgType.DATA,
                 MsgType.STATE, MsgType.CANCEL)
    def __init__(self):
        super().__init__()
        self.message_map = {MsgType.HELLO: HelloMessage,
                            MsgType.WELCOME: WelcomeMessage,
                            MsgType.NOOP: NoopMessage,
                            MsgType.REQUEST: RequestMessage,
                            MsgType.REPLY: ReplyMessage,
                            MsgType.DATA: DataMessage,
                            MsgType.CANCEL: CancelMessage,
                            MsgType.STATE: StateMessage,
                            MsgType.CLOSE: CloseMessage,
                            MsgType.ERROR: ErrorMessage,
                            (MsgType.REQUEST, RequestCode.CON_REPEAT): RequestConRepeat,
                            (MsgType.REPLY, RequestCode.SVC_ABILITIES): ReplySvcAbilities,
                           }
        self._request_enums = [RequestCode]
        self._error_enums = [ErrorCode]
        self.uid = PROTOCOL_UID
        self.revision = PROTOCOL_REVISION
    def is_request_code(self, code: int) -> bool:
        """Returns True if `get_request_code()` does not raise a ValueError."""
        try:
            self.get_request_code(code)
        except ValueError:
            return False
        return True
    def get_request_code(self, code: int) -> IntEnum:
        """Returns `enum` value for request code.

Looks up the proper enum value in internal `_request_enums` list.
"""
        for _enum in self._request_enums:
            if code in _enum._value2member_map_: # pylint: disable=E1101
                return _enum(code)
        raise ValueError(f"Invalid Request Code ({code})")
    def is_error_code(self, code: int) -> bool:
        """Returns True if `get_error_code()` does not raise a ValueError."""
        try:
            self.get_error_code(code)
        except ValueError:
            return False
        return True
    def get_error_code(self, code: int) -> IntEnum:
        """Returns `enum` value for error code.

Looks up the proper enum value in internal `_error_enums` list.
"""
        for _enum in self._error_enums:
            if code in _enum._value2member_map_: # pylint: disable=E1101
                return _enum(code)
        raise ValueError(f"Invalid Request Code ({code})")
    def create_message_for(self, message_type: int, token: Optional[bytes] = None,
                           type_data: Optional[int] = None,
                           flags: Optional[Flag] = None) -> Message:
        """Create new :class:`Message` child class instance for particular FBSP message type.

Uses :attr:`message_map` dictionary to find appropriate Message descendant for the messsage.
First looks for `(message_type, type_data)` entry, then for `message_type`. Raises
an exception if no entry is found.

Arguments:
    :message_type: Type of message to be created
    :token:        Message token
    :type_data:    Message control data
    :flags:        Flags

Returns:
    New :class:`Message` instance.

Raises:
    :ValueError: If there is no class associated with `message_type`.
"""
        cls = self.message_map.get((message_type, type_data))
        if not cls:
            cls = self.message_map.get(message_type)
        if not cls:
            raise ValueError("Unknown message type: %d" % message_type)
        msg = cls(self)
        if token is not None:
            msg.token = token
        if type_data is not None:
            msg.type_data = type_data
        if flags is not None:
            msg.flags = flags
        return msg
    def create_ack_reply(self, msg: Message) -> Message:
        """Returns new Message that is an ACK-REPLY response message.
"""
        reply = self.create_message_for(msg.message_type, msg.token, msg.type_data,
                                        msg.flags)
        reply.clear_flag(Flag.ACK_REQ)
        reply.set_flag(Flag.ACK_REPLY)
        return reply
    def create_message(self) -> Message:
        """Create new FBSP protocol message instance.

Returns:
   New :class:`Message` instance.
"""
        return Message(self)
    def create_welcome_reply(self, msg: HelloMessage) -> WelcomeMessage:
        """Create new WelcomeMessage that is a reply to client's HELLO.

Arguments:
    :hello:  :class:`HelloMessage` from the client

Returns:
    New :class:`WelcomeMessage` instance.
"""
        return self.create_message_for(MsgType.WELCOME, msg.token)
    def create_error_for(self, msg: Message, error_code: IntEnum) -> ErrorMessage:
        """Create new ErrorMessage that relates to specific message.

Arguments:
    :message:    :class:`Message` instance that error relates to
    :error_code: Error code

Returns:
    New :class:`ErrorMessage` instance.
"""
        err = self.create_message_for(MsgType.ERROR, msg.token)
        err.relates_to = msg.message_type
        err.error_code = error_code
        return err
    def create_reply_for(self, msg: RequestMessage) -> ReplyMessage:
        """Create new ReplyMessage for specific RequestMessage.

Arguments:
    :message: :class:`RequestMessage` instance that reply relates to
    :value:   State code

Returns:
    New :class:`ReplyMessage` instance.
"""
        return self.create_message_for(MsgType.REPLY, msg.token, msg.type_data)
    def create_state_for(self, msg: RequestMessage, value: int) -> StateMessage:
        """Create new StateMessage that relates to specific RequestMessage.

Arguments:
    :message: :class:`RequestMessage` instance that state relates to
    :value:   State code

Returns:
    New :class:`StateMessage` instance.
"""
        msg = self.create_message_for(MsgType.STATE, msg.token, msg.type_data)
        msg.state = value
        return msg
    def create_data_for(self, msg: RequestMessage) -> DataMessage:
        """Create new DataMessage for reply to specific RequestMessage.

Arguments:
    :message: :class:`RequestMessage` instance that data relates to

Returns:
    New :class:`DataMessage` instance.
"""
        return self.create_message_for(MsgType.DATA, msg.token)
    def create_request_for(self, request_code: int,
                           token: Optional[bytes] = None) -> RequestMessage:
        """Create new RequestMessage that is best suited for specific Request Code.

Arguments:
    :request_code: Request Code
    :token:        Message token

Returns:
    New :class:`RequestMessage` (or descendant) instance.
"""
        return self.create_message_for(MsgType.REQUEST, token, request_code)
    def has_greeting(self) -> bool:
        "Returns True if protocol uses greeting messages."
        return True
    def parse(self, zmsg: Sequence) -> BaseMessage:
        """Parse ZMQ message into protocol message.

Arguments:
    :zmsg: Sequence of bytes or :class:`zmq.Frame` instances that are a valid FBSP Message.

Returns:
    New :class:`Message` instance with parsed ZMQ message.
"""
        control_byte: int
        flags: int
        type_data: int
        token: bytes
        #
        header = msg_bytes(zmsg[0])
        if isinstance(header, zmq.Frame):
            header = header.bytes
        control_byte, flags, type_data, token = unpack(HEADER_FMT, header)
        #
        msg = self.create_message_for(control_byte >> 3, token, type_data, flags)
        msg.from_zmsg(zmsg)
        return msg
    def validate(self, zmsg: Sequence, origin: Origin, **kwargs) -> None:
        """Validate that ZMQ message is a valid FBSP message.

Arguments:
    :zmsg:   Sequence of bytes or :class:`zmq.Frame` instances.
    :origin: Origin of received message in protocol context.

Raises:
    :InvalidMessageError: If message is not a valid FBSP message.
"""
        Message.validate_cframe(zmsg)
        (control_byte, flags) = unpack('!4xBB10x', msg_bytes(zmsg[0]))
        message_type = control_byte >> 3
        flags = Flag(flags)
        if kwargs.get('greeting', False):
            if not (((message_type == MsgType.HELLO) and (origin == Origin.CLIENT)) or
                    ((message_type == MsgType.WELCOME) and (origin == Origin.SERVICE))):
                raise InvalidMessageError("Invalid greeting %s from %s" %
                                          (enum_name(message_type), enum_name(origin)))
        if message_type not in self.ORIGIN_MESSAGES[origin]:
            if Flag.ACK_REPLY not in flags:
                raise InvalidMessageError("Illegal message type %s from %s" %
                                          (enum_name(message_type), enum_name(origin)))
            if message_type not in self.VALID_ACK:
                raise InvalidMessageError("Illegal ACK message type %s from %s" %
                                          (enum_name(message_type), enum_name(origin)))
        self.message_map[message_type].validate_zmsg(zmsg)

class BaseFBSPlHandler(BaseHandler):
    """Base class for FBSP message handlers.

Uses `handlers` dictionary to route received messages to appropriate handlers.
Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Messages handled:
    :unknown: Raises NotImplementedError
    :NOOP:    Sends ACK_REPLY back if required, otherwise it will do nothing.
    :DATA:    Raises NotImplementedError
    :CLOSE:   Raises NotImplementedError

Abstract methods:
    :handle_unknown: Default message handler.
    :handle_data:    Handle DATA message.
    :handle_close:   Handle CLOSE message.
"""
    def __init__(self, chn: BaseChannel, role: Origin):
        super().__init__(chn, role, Session)
        self.handlers = {MsgType.NOOP: self.h_noop,
                         MsgType.DATA: self.h_data,
                         MsgType.CLOSE: self.h_close,
                        }
        self.protocol = Protocol()
    def raise_protocol_violation(self, session: Session, msg: Message) -> None: # pylint: disable=R0201
        """Raises ServiceError."""
        raise ServiceError("Protocol violation from service, message type: %d" %
                           enum_name(msg.message_type))
    def send_protocol_violation(self, session: Session, msg: Message) -> None:
        "Sends ERROR/PROTOCOL_VIOLATION message."
        errmsg = self.protocol.create_error_for(msg, ErrorCode.PROTOCOL_VIOLATION)
        err = errmsg.add_error()
        err.description = "Received message is a valid FBSP message, but does not " \
            "conform to the protocol."
        self.send(errmsg, session)
    def do_nothing(self, session: Session, msg: Message) -> None:
        """Message handler that does nothing."""
    def h_unknown(self, session: Session, msg: Message) -> None:
        """Default message handler. Called by `dispatch` when no appropriate message handler
is found in :attr:`handlers` dictionary.
"""
        raise NotImplementedError
    def h_noop(self, session: Session, msg: NoopMessage) -> None:
        "Handle NOOP message. Sends ACK_REPLY back if required, otherwise it will do nothing."
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
    def h_data(self, session: Session, msg: DataMessage) -> None:
        "Handle DATA message."
        raise NotImplementedError
    def h_close(self, session: Session, msg: CloseMessage) -> None:
        "Handle CLOSE message."
        raise NotImplementedError
    def dispatch(self, session: Session, msg: BaseMessage) -> None:
        """Process message received from peer.

Uses :attr:`handlers` dictionary to find appropriate handler for the messsage.
First looks for `(message_type, type_data)` entry, then for `message_type`.
If no appropriate handler is located, calls `handle_unknown()`.

Arguments:
    :session: Session attached to peer.
    :msg:     FBSP message received from client.
"""
        handler = self.handlers.get((msg.message_type, msg.type_data))
        if not handler:
            handler = self.handlers.get(msg.message_type)
        if handler:
            handler(session, msg)
        else:
            self.h_unknown(session, msg)

class ServiceMessagelHandler(BaseFBSPlHandler):
    """Base class for Service handlers that process messages from Client.

Uses `handlers` dictionary to route received messages to appropriate handlers.
Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Messages handled:
    :unknown: Sends ERROR/INVALID_MESSAGE back to the client.
    :HELLO:   Sets session.greeting. MUST be overridden to send WELCOME message.
    :WELCOME: Sends sends ERROR/PROTOCOL_VIOLATION.
    :NOOP:    Sends ACK_REPLY back if required, otherwise it will do nothing.
    :REQUEST: Fall-back that sends an ERROR/BAD_REQUEST message.
    :REPLY:   Handles ACK_REPLY, sends ERROR/PROTOCOL_VIOLATION if it's not the ACK_REPLY.
    :DATA:    Raises NotImplementedError
    :CANCEL:  Raises NotImplementedError
    :STATE:   Sends sends ERROR/PROTOCOL_VIOLATION.
    :CLOSE:   Disconnects from remote endpoint if defined, discards current session.
    :ERROR:   Sends sends ERROR/PROTOCOL_VIOLATION.

Abstract methods:
    :handle_data:    Handle DATA message.
    :handle_cancel:  Handle CANCEL message.
"""
    def __init__(self, chn: BaseChannel, service):
        super().__init__(chn, Origin.SERVICE)
        self.impl: ServiceImpl = service
        self.handlers.update({MsgType.HELLO: self.h_hello,
                              MsgType.REQUEST: self.h_request,
                              MsgType.CANCEL: self.h_cancel,
                              MsgType.REPLY: self.h_reply,
                              MsgType.WELCOME: self.send_protocol_violation,
                              MsgType.STATE: self.send_protocol_violation,
                              MsgType.ERROR: self.send_protocol_violation,
                             })
    def close(self):
        "Close all connections to Clients."
        while self.sessions:
            _, session = self.sessions.popitem()
            self.send(self.protocol.create_message_for(MsgType.CLOSE, session.token),
                      session)
            if session.endpoint:
                self.chn.disconnect(session.endpoint)
    def on_ack_reply(self, session: Session, msg: ReplyMessage) -> None:
        "Called to handle REPLY/ACK_REPLY message."
    def h_unknown(self, session: Session, msg: Message) -> None:
        """Default message handler for unrecognized messages.
Sends ERROR/INVALID_MESSAGE back to the client.
"""
        errmsg = self.protocol.create_error_for(session.greeting, ErrorCode.INVALID_MESSAGE)
        err = errmsg.add_error()
        err.description = "Invalid message, type: %d" % msg.message_type
        self.send(errmsg, session)
    def h_close(self, session: Session, msg: CloseMessage) -> None:
        """Handle CLOSE message.

If 'endpoint` is set in session, disconnects underlying channel from it. Then discards
the session.
"""
        if session.endpoint:
            self.chn.disconnect(session.endpoint)
        self.discard_session(session)
    def h_hello(self, session: Session, msg: HelloMessage) -> None: # pylint: disable=R0201
        """Handle HELLO message.

This method MUST be overridden in child classes to send WELCOME message back to the client.
Overriding method must call `super().handle_hello(session, msg)`.
"""
        session.greeting = msg
    def h_request(self, session: Session, msg: RequestMessage) -> None:
        """Handle Client REQUEST message.

This is implementation provides a fall-back handler for unsupported request codes (not
defined in `handler` table) that sends back an ERROR/BAD_REQUEST message.
"""
        self.send(self.protocol.create_error_for(msg, ErrorCode.BAD_REQUEST), session)
    def h_cancel(self, session: Session, msg: CancelMessage) -> None:
        "Handle CANCEL message."
        raise NotImplementedError
    def h_reply(self, session: Session, msg: ReplyMessage):
        """Handle REPLY message.

Unless it's an ACK_REPLY, client SHALL not send REPLY messages to the service.
"""
        if msg.has_ack_reply():
            self.on_ack_reply(session, msg)
        else:
            self.send_protocol_violation(session, msg)


def exception_for(msg: ErrorMessage) -> ServiceError:
    "Returns ServiceError exception from ERROR message."
    desc = [f"{enum_name(msg.error_code)}, relates to {enum_name_only(msg.relates_to)}"]
    for err in msg.errors:
        desc.append(f"#{err.code} : {err.description}")
    return ServiceError('\n'.join(desc))

class ClientMessageHandler(BaseFBSPlHandler):
    """Base class for Client handlers that process messages from Service.

Uses `handlers` dictionary to route received messages to appropriate handlers.
Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Attributes:
    :last_token_seen: Token from last message processed by `h_*` handlers or None.

Messages handled:
    :unknown: Raises ServiceError
    :HELLO:   Raises ServiceError
    :WELCOME: Store WELCOME to session.greeting or raise ServiceError on unexpected one.
    :NOOP:    Sends ACK_REPLY back if required, otherwise it will do nothing.
    :REQUEST: Raises ServiceError
    :REPLY:   Raises NotImplementedError
    :DATA:    Raises NotImplementedError
    :CANCEL:  Raises ServiceError
    :STATE:   Raises NotImplementedError
    :CLOSE:   Disconnects the service, closes the session, and raises ServiceError.
    :ERROR:   Raises NotImplementedError

Abstract methods:
    :handle_reply:   Handle Service REPLY message.
    :handle_data:    Handle DATA message.
    :handle_state:   Handle STATE message.
    :handle_error:   Handle ERROR message received from Service.
"""
    def __init__(self, chn: BaseChannel, instance_uid: UUID, host: str, agent_uid: UUID,
                 agent_name: str, agent_version: str):
        super().__init__(chn, Origin.CLIENT)
        self.handlers.update({MsgType.WELCOME: self.handle_welcome,
                              MsgType.REPLY: self.h_reply,
                              MsgType.STATE: self.h_state,
                              MsgType.ERROR: self.h_error,
                              MsgType.HELLO: self.raise_protocol_violation,
                              MsgType.REQUEST: self.raise_protocol_violation,
                              MsgType.CANCEL: self.raise_protocol_violation,
                             })
        self._tcnt = 0 # Token generator
        self.last_token_seen: bytes = None
        self.desc = pb.PeerIdentification()
        self.desc.uid = instance_uid.bytes
        self.desc.host = host
        self.desc.pid = getpid()
        self.desc.identity.uid = agent_uid.bytes
        self.desc.identity.name = agent_name
        self.desc.identity.version = agent_version
        self.desc.identity.fbsp.uid = PROTOCOL_UID.bytes
        self.desc.identity.fbsp.version = str(PROTOCOL_REVISION)
        self.desc.identity.vendor.uid = VENDOR_UID.bytes
        self.desc.identity.platform.uid = PLATFORM_UID.bytes
        self.desc.identity.platform.version = PLATFORM_VERSION
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    def new_token(self) -> bytes:
        "Return newly created `token` value."
        self._tcnt += 1
        return pack('Q', self._tcnt)
    def close(self):
        "Close connection to Service."
        session = self.get_session()
        try:
            self.send(self.protocol.create_message_for(MsgType.CLOSE,
                                                       session.greeting.token), session)
        except: # pylint: disable=W0702
            # channel could be already closed from other side, as we are closing it too
            # we can ignore any send errors
            pass
        self.discard_session(session)
    def get_response(self, token: bytes, timeout: int = None) -> bool:
        """Get reponse from Service.

Process incomming messages until timeout reaches out or response arrives. Valid response
is any message with token equal to: a) passed `token` argument or b) token from
session.greeting.

Arguments:
    :token:   Token used for request
    :timeout: Timeout for request [default: infinity]

Important:
    - All registered handler methods must store token of handled message into
      `last_token_seen` attribute.
    - Does not work with routed channels, and channels without active session.

Returns:
    True if response arrived in time, False on timeout.
"""
        assert not self.chn.routed, "Routed channels are not supported"
        stop = False
        session = self.get_session()
        assert session, "Active session required"
        start = monotonic()
        while not stop:
            self.last_token_seen = None
            event = self.chn.socket.poll(timeout)
            if event == zmq.POLLIN:
                zmsg = self.chn.receive()
                if not session.greeting:
                    self.protocol.validate(zmsg, peer_role(self.role), greeting=True)
                msg = self.protocol.parse(zmsg)
                try:
                    self.dispatch(session, msg)
                except Exception as exc:
                    raise ServiceError("Exception raised while processing response from service") from exc
            if self.last_token_seen and self.last_token_seen in (token, session.greeting.token):
                return True
            if timeout:
                stop = round((monotonic() - start) * 1000) >= timeout
        return False

    def h_unknown(self, session: Session, msg: Message):
        "Default message handler for unrecognized messages. Raises `ServiceError`."
        raise ServiceError("Unhandled %s message from service" % enum_name(msg.message_type))
    def h_close(self, session: Session, msg: CloseMessage) -> None:
        """Handle CLOSE message.

If 'endpoint` is set in session, disconnects underlying channel from it. Then discards
the session and raises `ServiceError`.
"""
        self.last_token_seen = msg.token
        if session.endpoint:
            self.chn.disconnect(session.endpoint)
        self.discard_session(session)
        raise ServiceError("The service has closed the connection.")
    def handle_welcome(self, session: Session, msg: WelcomeMessage) -> None:
        """Handle WELCOME message.

Save WELCOME message into session.greeting, or raise `ServiceError` for unexpected WELCOME.
"""
        self.last_token_seen = msg.token
        if not session.greeting:
            session.greeting = msg
        else:
            raise ServiceError("Unexpected WELCOME message")
    def h_reply(self, session: Session, msg: ReplyMessage) -> None:
        "Handle Service REPLY message."
        raise NotImplementedError
    def h_state(self, session: Session, msg: StateMessage) -> None:
        "Handle STATE message."
        raise NotImplementedError
    def h_error(self, session: Session, msg: ErrorMessage) -> None:
        "Handle ERROR message received from Service."
        raise NotImplementedError

#

class ServiceImpl(BaseServiceImpl):
    """Base FBSP service implementation.

Class attributes:
    :SERVICE_UID:     Must be assigned in child class.
    :SERVICE_NAME:    Must be assigned in child class.
    :SERVICE_VERSION: Must be assigned in child class.
    :PROTOCOL_UID:    Must be assigned in child class.
    :REQUIRES:        List of required services (UUIDs) [default: empty].
    :OPTIONAL:        List of optional services (UUIDs) [default: empty].

Attributes:
    :desc:  PeerIdentification instance.
"""
    SERVICE_UID: UUID = None
    SERVICE_NAME: str = None
    SERVICE_VERSION: str = None
    PROTOCOL_UID: UUID = None
    REQUIRES: List[UUID] = []
    OPTIONAL: List[UUID] = []
    def __init__(self):
        super().__init__()
        self.desc = pb.PeerIdentification()
        self.msg_handler = None
    def initialize(self, svc):
        "Partial initialization of service identity descriptor."
        self.desc.uid = uuid1().bytes
        self.desc.pid = getpid()
        self.desc.identity.uid = self.SERVICE_UID.bytes
        self.desc.identity.name = self.SERVICE_NAME
        self.desc.identity.version = self.SERVICE_VERSION
        self.desc.identity.fbsp.uid = PROTOCOL_UID.bytes
        self.desc.identity.fbsp.version = str(PROTOCOL_REVISION)
        self.desc.identity.vendor.uid = VENDOR_UID.bytes
        self.desc.identity.platform.uid = PLATFORM_UID.bytes
        self.desc.identity.platform.version = PLATFORM_VERSION

    instance_id: bytes = property(lambda self: self.desc.uid,
                                  doc="Service instance identification")

class Service(BaseService): # pylint: disable=W0223
    """Base FBSP service."""
    def validate(self):
        super().validate()
        # check implementation class
        assert isinstance(self.impl.SERVICE_UID, UUID), "Service implementation UID not defined"
        assert self.impl.SERVICE_NAME, "Service implementation NAME not defined"
        assert self.impl.SERVICE_VERSION, "Service implementation VERSION not defined"
        assert isinstance(self.impl.PROTOCOL_UID, UUID), \
               "Service implementation PROTOCOL_ID not defined"
        # check peer identification
        assert self.impl.desc.uid, "Service instance UID not defined"
        assert self.impl.desc.host, "Service host not defined"
        assert self.impl.desc.identity.protocol.uid, "Service protocol UID not defined"
        assert self.impl.desc.identity.protocol.version, "Service protocol version not defined"
        assert self.impl.desc.identity.classification, "Service classification not defined"
