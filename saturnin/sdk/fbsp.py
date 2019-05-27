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

import logging
from typing import List, Dict, Sequence, Optional, Union
from uuid import UUID, uuid5, NAMESPACE_OID
from struct import pack, unpack
from enum import IntEnum
from time import monotonic
import zmq
from saturnin.sdk import fbsp_pb2 as pb
from saturnin.sdk.base import BaseMessage, BaseProtocol, BaseSession, BaseMessageHandler, \
     get_unique_key, peer_role
from saturnin.sdk.types import TChannel, TServiceImpl, TSession, TMessage, Token, \
     ServiceError, InvalidMessageError, Origin, MsgType, MsgFlag, ErrorCode

PROTOCOL_OID = '1.3.6.1.4.1.53446.1.5.0' # firebird.butler.protocol.fbsp
PROTOCOL_UID = uuid5(NAMESPACE_OID, PROTOCOL_OID)
PROTOCOL_REVISION = 1

# Message header
HEADER_FMT_FULL = '!4sBBH8s'
HEADER_FMT = '!4xBBH8s'
FOURCC = b'FBSP'
VERSION_MASK = 7
ERROR_TYPE_MASK = 31

# Protocol Buffer Enums

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

# Logger

log = logging.getLogger(__name__)

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
    __invalid_if(not pbo.HasField('vendor'), name, "vendor")
    __invalid_if(not pbo.HasField('platform'), name, "platform")
    validate_vendor_id_pb(pbo.vendor)
    validate_platform_id_pb(pbo.platform)

def validate_peer_id_pb(pbo: pb.PeerIdentification) -> None:
    "Validate fbsp.PeerIdentification protobuf. Raises InvalidMessage for missing required fields."
    name = "PeerIdentification"
    __invalid_if(len(pbo.uid) == 0, name, "uid")
    __invalid_if(pbo.pid == 0, name, "pid")
    __invalid_if(len(pbo.host) == 0, name, "host")

def validate_error_desc_pb(pbo: pb.ErrorDescription) -> None:
    "Validate fbsp.ErrorDescription protobuf. Raises InvalidMessage for missing required fields."
    name = "ErrorDescription"
    __invalid_if(pbo.code == 0, name, "code")
    __invalid_if(len(pbo.description) == 0, name, "description")

def validate_interface_spec_pb(pbo: pb.InterfaceSpec) -> None:
    "Validate fbsp.InterfaceSpec protobuf. Raises InvalidMessage for missing required fields."
    name = "InterfaceSpec"
    __invalid_if(pbo.number == 0, name, "number")
    __invalid_if(len(pbo.uid) == 0, name, "uid")

def validate_cancel_pb(pbo: pb.CancelRequests) -> None:
    "Validate fbsp.CancelRequests protobuf. Raises InvalidMessage for missing required fields."
    name = "CancelRequests"
    __invalid_if(len(pbo.token) == 0, name, "token")

def validate_hello_pb(pbo: pb.HelloDataframe) -> None:
    "Validate fbsp.HelloDataframe protobuf. Raises InvalidMessage for missing required fields."
    #name = "HelloDataframe"
    validate_peer_id_pb(pbo.instance)
    validate_agent_id_pb(pbo.client)

def validate_welcome_pb(pbo: pb.WelcomeDataframe) -> None:
    "Validate fbsp.WelcomeDataframe protobuf. Raises InvalidMessage for missing required fields."
    name = "WelcomeDataframe"
    validate_peer_id_pb(pbo.instance)
    validate_agent_id_pb(pbo.service)
    __invalid_if(len(pbo.api) == 0, name, "api")
    for ispec in pbo.api:
        validate_interface_spec_pb(ispec)

# Functions

def msg_bytes(msg: Union[bytes, bytearray, zmq.Frame]) -> bytes:
    "Return message frame as bytes."
    return msg.bytes if isinstance(msg, zmq.Frame) else msg

def bb2h(value_hi: int, value_lo: int) -> int:
    "Compose two bytes into word value."
    return unpack('!H', pack('!BB', value_hi, value_lo))[0]

def uid2uuid(lines: Sequence) -> List:
    """Replace ugly escaped "uid" strings with standard UUID string format.
"""
    result = []
    for line in lines:
        s = line.strip()
        if s.startswith('uid:') or '_uid:' in s:
            i = line[line.index('"')+1:line.rindex('"')]
            uuid = UUID(bytes=eval(f'b"{i}"'))
            line = line.replace(i, str(uuid))
        result.append(line)
    return result

# Base Message Classes

class Message(BaseMessage):
    """Base FBSP Message.

Attributes:
    :msg_type:  Type of message (int)
    :header:    FBSP control frame (bytes)
    :flasg:     flags (int)
    :type_data: Data associated with message (int)
    :token:     Message token (bytearray)
    :data:      List of data frames
"""
    def __init__(self):
        super().__init__()
        self.message_type: MsgType = MsgType.UNKNOWN
        self.type_data: int = 0
        self.flags: MsgFlag = MsgFlag(0)
        self.token: Token = bytearray(8)
    def _unpack_data(self) -> None:
        """Called when all fields of the message are set. Usefull for data deserialization."""
    def _pack_data(self, frames: list) -> None:
        """Called when serialization is requested."""
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        return ""
    def from_zmsg(self, frames: Sequence) -> None:
        _, flags, self.type_data, self.token = unpack(HEADER_FMT, frames[0])
        self.flags = MsgFlag(flags)
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
        return MsgFlag.MORE in self.flags
    def has_ack_req(self) -> bool:
        """Returns True if message has ACK_REQ flag set."""
        return MsgFlag.ACK_REQ in self.flags
    def has_ack_reply(self) -> bool:
        """Returns True if message has ASK_REPLY flag set."""
        return MsgFlag.ACK_REPLY in self.flags
    def set_flag(self, flag: MsgFlag) -> None:
        """Set flag specified by `flag` mask."""
        self.flags |= flag
    def clear_flag(self, flag: MsgFlag) -> None:
        """Clear flag specified by `flag` mask."""
        self.flags &= ~flag
    def clear(self) -> None:
        """Clears message attributes."""
        super().clear()
        self.token = bytearray(8)
        self.type_data = 0
        self.flags = MsgFlag(0)
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
            raise InvalidMessageError("Zero Request Code not allowed")
        if (message_type == MsgType.ERROR) and (type_data >> 5 == 0):
            raise InvalidMessageError("Zero Error Code not allowed")
        if (message_type == MsgType.ERROR) and ((type_data & ERROR_TYPE_MASK)
                                                not in (MsgType.HELLO, MsgType.NOOP,
                                                        MsgType.REQUEST, MsgType.DATA,
                                                        MsgType.CANCEL, MsgType.CLOSE)):
            raise InvalidMessageError("Invalid Request Code '%d' for ERROR message"
                                      % (type_data & ERROR_TYPE_MASK))
    def get_printout(self, with_data = True) -> str:
        """Returns printable, multiline representation of message.
"""
        lines = [f"Message type: {self.message_type.name}",
                 f"Flags: {self.flags.name}",
                 f"Type data: {self.type_data}",
                 f"Token: {unpack('Q',self.token)[0]}"
                ]
        extra = self._get_printout_ex()
        if extra:
            lines.extend(extra.strip().split('\n'))
        lines.append(f"# data frames: {len(self.data)}")
        if with_data and self.data:
            for index, frame in enumerate(self.data, 1):
                lines.append(f"{index}: {frame}")
        return "\n".join(lines)

class HandshakeMessage(Message):
    """Base FBSP client/service handshake message (HELLO or WELCOME).
    The message includes basic information about the Peer.
"""
    def __init__(self):
        super().__init__()
        self.peer = None
    def _unpack_data(self) -> None:
        self.peer.ParseFromString(self.data.pop(0))
    def _pack_data(self, frames: list) -> None:
        frames.append(self.peer.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        # protobuf returns UUIDs as ugly escaped strings
        # we prefer standard UUID string format
        return "Peer:\n%s" % '\n'.join(uid2uuid(str(self.peer).splitlines()))
        #lines = []
        #for line in str(self.peer).splitlines():
            #if line.strip().startswith('uid:'):
                #i = line[line.index('"')+1:line.rindex('"')]
                #uuid = UUID(bytes=eval(f'b"{i}"'))
                #line = line.replace(i, str(uuid))
            #lines.append(line)
        #return "Peer:\n%s" % '\n'.join(lines)
    def clear(self) -> None:
        super().clear()
        self.peer.Clear()

class HelloMessage(HandshakeMessage):
    """The HELLO message is a Client request to open a Connection to the Service.
    The message includes basic information about the Client and Connection parameters
    required by the Client."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.HELLO
        self.peer = pb.HelloDataframe()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        try:
            frame = pb.HelloDataframe()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_hello_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for HELLO or WELCOME") from exc

class WelcomeMessage(HandshakeMessage):
    """The WELCOME message is the response of the Service to the HELLO message sent by the Client,
    which confirms the successful creation of the required Connection and announces basic parameters
    of the Service and the Connection."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.WELCOME
        self.peer = pb.WelcomeDataframe()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        try:
            frame = pb.WelcomeDataframe()
            frame.ParseFromString(msg_bytes(zmsg[1]))
            validate_welcome_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for HELLO or WELCOME") from exc

class NoopMessage(Message):
    """The NOOP message means no operation.
    It’s intended for keep alive purposes and peer availability checks."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.NOOP
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        super().validate_zmsg(zmsg)
        if len(zmsg) > 1:
            raise InvalidMessageError("Data frames not allowed for NOOP")

class APIMessage(Message):
    """Base FBSP client/service API message (REQUEST, REPLY, STATE).
    The message includes information about the API call (interface ID and API Code)."""
    def __get_request_code(self) -> int:
        return self.type_data
    def __get_api_code(self) -> int:
        return unpack('!BB', pack('!H', self.type_data))[1]
    def __set_api_code(self, value: int) -> None:
        self.type_data = bb2h(self.interface_id, value)
    def __get_interface(self) -> int:
        return unpack('!BB', pack('!H', self.type_data))[0]
    def __set_interface(self, value: int) -> None:
        self.type_data = bb2h(value, self.api_code)
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        lines = [f"Interface ID: {self.interface_id}",
                 f"API code: {self.api_code}"
                ]
        return '\n'.join(lines)
    interface_id: int = property(__get_interface, __set_interface,
                                 doc="Interface ID (high byte of Request Code)")
    api_code: int = property(__get_api_code, __set_api_code,
                             doc="API Code (lower byte of Request Code)")
    request_code: int = property(__get_request_code,
                                 doc="Request Code (Interface ID + API Code)")

class RequestMessage(APIMessage):
    """The REQUEST message is a Client request to the Service."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.REQUEST

class ReplyMessage(APIMessage):
    """The REPLY message is a Service reply to the REQUEST message previously sent by Client."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.REPLY

class DataMessage(Message):
    """The DATA message is intended for delivery of arbitrary data between connected peers."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.DATA

class CancelMessage(Message):
    """The CANCEL message represents a request for a Service to stop processing the previous
    request from the Client."""
    def __init__(self):
        super().__init__()
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
            validate_cancel_pb(frame)
        except Exception as exc:
            raise InvalidMessageError("Invalid data frame for CANCEL") from exc

class StateMessage(APIMessage):
    """The STATE message is sent by Service to report its operating state to the Client."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.STATE
        self._state = pb.StateInformation()
    def __get_state(self) -> State:
        return State(self._state.state)
    def __set_state(self, value: State) -> None:
        self._state.state = value
    def _unpack_data(self) -> None:
        self._state.ParseFromString(msg_bytes(self.data.pop(0)))
    def _pack_data(self, frames: list) -> None:
        frames.append(self._state.SerializeToString())
    def _get_printout_ex(self) -> str:
        "Called for printout of attributes defined by descendant classes."
        lines = [f"State: {self.state.name}",
                 f"Interface ID: {self.interface_id}",
                 f"API code: {self.api_code}"
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

    state: State = property(__get_state, __set_state, doc="Service state")

class CloseMessage(Message):
    """The CLOSE message notifies the receiver that sender is going to close the Connection."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.CLOSE

class ErrorMessage(Message):
    """The ERROR message notifies the Client about error condition detected by Service."""
    def __init__(self):
        super().__init__()
        self.message_type = MsgType.ERROR
        self.errors = []
    def __get_error_code(self) -> int:
        return ErrorCode(self.type_data >> 5)
    def __set_error_code(self, value: ErrorCode) -> None:
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
        lines = [f"Error code: {self.error_code.name}",
                 f"Relates to: {self.relates_to.name}",
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

    error_code: ErrorCode = property(fget=__get_error_code, fset=__set_error_code,
                                     doc="Error code")
    relates_to: MsgType = property(fget=__get_relates_to, fset=__set_relates_to,
                                   doc="Message type this error relates to")

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
    def get_request(self, token: Token = None, handle: int = None) -> RequestMessage:
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
    peer_id: bytes = property(lambda self: UUID(bytes=self.greeting.peer.instance.uid))
    host: str = property(lambda self: self.greeting.peer.instance.host)
    pid: int = property(lambda self: self.greeting.peer.instance.pid)
    agent_id: bytes = property(lambda self: UUID(bytes=self.greeting.peer.service.uid))
    name: str = property(lambda self: self.greeting.peer.service.name)
    version: str = property(lambda self: self.greeting.peer.service.version)
    vendor: bytes = property(lambda self: UUID(bytes=self.greeting.peer.service.vendor.uid))
    platform: bytes = property(lambda self: UUID(bytes=self.greeting.peer.service.platform.uid))
    platform_version: str = property(lambda self: self.greeting.peer.service.platform.version)
    classification: str = property(lambda self: self.greeting.peer.service.classification)

class Protocol(BaseProtocol):
    """4/FBSP - Firebird Butler Service Protocol
    """
    OID: str = PROTOCOL_OID
    UID: UUID = PROTOCOL_UID
    REVISION: int = PROTOCOL_REVISION
    ORIGIN_MESSAGES = {Origin.SERVICE: (MsgType.ERROR, MsgType.WELCOME, MsgType.NOOP,
                                        MsgType.REPLY, MsgType.DATA, MsgType.STATE,
                                        MsgType.CLOSE),
                       Origin.CLIENT: (MsgType.HELLO, MsgType.NOOP, MsgType.REQUEST,
                                       MsgType.CANCEL, MsgType.DATA, MsgType.CLOSE)
                      }
    VALID_ACK = (MsgType.NOOP, MsgType.REQUEST, MsgType.REPLY, MsgType.DATA,
                 MsgType.STATE, MsgType.CANCEL)
    MESSAGE_MAP = {MsgType.HELLO: HelloMessage,
                   MsgType.WELCOME: WelcomeMessage,
                   MsgType.NOOP: NoopMessage,
                   MsgType.REQUEST: RequestMessage,
                   MsgType.REPLY: ReplyMessage,
                   MsgType.DATA: DataMessage,
                   MsgType.CANCEL: CancelMessage,
                   MsgType.STATE: StateMessage,
                   MsgType.CLOSE: CloseMessage,
                   MsgType.ERROR: ErrorMessage,
                  }
    @classmethod
    def instance(cls):
        """Returns global FBSP protocol instance."""
        return _FBSP_INSTANCE
    def create_message_for(self, message_type: int, token: Optional[Token] = None,
                           type_data: Optional[int] = None,
                           flags: Optional[MsgFlag] = None) -> TMessage:
        """Create new :class:`Message` child class instance for particular FBSP message type.

Uses :attr:`message_map` dictionary to find appropriate Message descendant for the messsage.
Raises an exception if no entry is found.

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
        cls = self.MESSAGE_MAP.get(message_type)
        if not cls:
            raise ValueError("Unknown message type: %d" % message_type)
        msg = cls()
        if token is not None:
            msg.token = token
        if type_data is not None:
            msg.type_data = type_data
        if flags is not None:
            msg.flags = flags
        return msg
    def create_ack_reply(self, msg: TMessage) -> TMessage:
        """Returns new Message that is an ACK-REPLY response message.
"""
        reply = self.create_message_for(msg.message_type, msg.token, msg.type_data,
                                        msg.flags)
        reply.clear_flag(MsgFlag.ACK_REQ)
        reply.set_flag(MsgFlag.ACK_REPLY)
        return reply
    def create_welcome_reply(self, msg: HelloMessage) -> WelcomeMessage:
        """Create new WelcomeMessage that is a reply to client's HELLO.

Arguments:
    :hello:  :class:`HelloMessage` from the client

Returns:
    New :class:`WelcomeMessage` instance.
"""
        return self.create_message_for(MsgType.WELCOME, msg.token)
    def create_error_for(self, msg: TMessage, error_code: IntEnum) -> ErrorMessage:
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
    def create_request_for(self, interface_id, api_code: int,
                           token: Optional[Token] = None) -> RequestMessage:
        """Create new RequestMessage that is best suited for specific request.

Arguments:
    :interface_id: Interface Identification Number
    :api_code:     API Code
    :token:        Message token

Returns:
    New :class:`RequestMessage` (or descendant) instance.
"""
        return self.create_message_for(MsgType.REQUEST, token, bb2h(interface_id, api_code))
    def has_greeting(self) -> bool:
        "Returns True if protocol uses greeting messages."
        return True
    def parse(self, zmsg: Sequence) -> TMessage:
        """Parse ZMQ message into protocol message.

Arguments:
    :zmsg: Sequence of bytes or :class:`zmq.Frame` instances that are a valid FBSP Message.

Returns:
    New :class:`Message` instance with parsed ZMQ message.
"""
        control_byte: int
        flags: int
        type_data: int
        token: Token
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
        message_type = MsgType(control_byte >> 3)
        flags = MsgFlag(flags)
        if kwargs.get('greeting', False):
            if not (((message_type == MsgType.HELLO) and (origin == Origin.CLIENT)) or
                    ((message_type == MsgType.WELCOME) and (origin == Origin.SERVICE))):
                raise InvalidMessageError("Invalid greeting %s from %s" %
                                          (message_type.name, origin.name))
        if message_type not in self.ORIGIN_MESSAGES[origin]:
            if MsgFlag.ACK_REPLY not in flags:
                raise InvalidMessageError("Illegal message type %s from %s" %
                                          (message_type.name, origin.name))
            if message_type not in self.VALID_ACK:
                raise InvalidMessageError("Illegal ACK message type %s from %s" %
                                          (message_type.name, origin.name))
        self.MESSAGE_MAP[message_type].validate_zmsg(zmsg)

_FBSP_INSTANCE = Protocol()

class BaseFBSPlHandler(BaseMessageHandler):
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
    :on_unknown: Default message handler.
    :on_data:    Handle DATA message.
    :on_close:   Handle CLOSE message.
"""
    def __init__(self, chn: TChannel, role: Origin):
        super().__init__(chn, role, Session)
        self.handlers = {MsgType.NOOP: self.on_noop,
                         MsgType.DATA: self.on_data,
                         MsgType.CLOSE: self.on_close,
                        }
        self.protocol = Protocol.instance()
    def raise_protocol_violation(self, session: TSession, msg: Message) -> None:
        """Raises ServiceError."""
        raise ServiceError("Protocol violation from service, message type: %d" %
                           msg.message_type.name)
    def send_protocol_violation(self, session: TSession, msg: Message) -> None:
        "Sends ERROR/PROTOCOL_VIOLATION message."
        errmsg = self.protocol.create_error_for(msg, ErrorCode.PROTOCOL_VIOLATION)
        err = errmsg.add_error()
        err.description = "Received message is a valid FBSP message, but does not " \
            "conform to the protocol."
        self.send(errmsg, session)
    def do_nothing(self, session: TSession, msg: Message) -> None:
        """Message handler that does nothing. Useful for cases when message must be handled
but no action is required, like handling CANCEL messages in simple protocols.
"""
        log.debug("%s.do_nothing", self.__class__.__name__)
    def on_unknown(self, session: TSession, msg: Message) -> None:
        """Default message handler. Called by `dispatch` when no appropriate message handler
is found in :attr:`handlers` dictionary.
"""
        raise NotImplementedError
    def on_noop(self, session: TSession, msg: NoopMessage) -> None:
        "Handle NOOP message. Sends ACK_REPLY back if required, otherwise it will do nothing."
        log.debug("%s.on_noop", self.__class__.__name__)
        if msg.has_ack_req():
            self.send(self.protocol.create_ack_reply(msg), session)
    def on_data(self, session: TSession, msg: DataMessage) -> None:
        "Handle DATA message."
        raise NotImplementedError
    def on_close(self, session: TSession, msg: CloseMessage) -> None:
        "Handle CLOSE message."
        raise NotImplementedError
    def dispatch(self, session: TSession, msg: TMessage) -> None:
        """Process message received from peer.

Uses :attr:`handlers` dictionary to find appropriate handler for the messsage.
First looks for `(message_type, type_data)` entry, then for `message_type`.
If no appropriate handler is located, calls `on_unknown()`.

Arguments:
    :session: Session attached to peer.
    :msg:     FBSP message received from client.
"""
        log.debug("%s.dispatch", self.__class__.__name__)
        handler = self.handlers.get((msg.message_type, msg.type_data))
        if not handler:
            handler = self.handlers.get(msg.message_type)
        if handler:
            handler(session, msg)
        else:
            self.on_unknown(session, msg)

class ServiceMessagelHandler(BaseFBSPlHandler):
    """Base class for Service handlers that process messages from Client.

Uses `handlers` dictionary to route received messages to appropriate handlers.
Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Messages handled:
    :unknown: Sends ERROR/INVALID_MESSAGE back to the client.
    :HELLO:   Sets session.greeting. MUST be overridden to send WELCOME message.
    :WELCOME: Sends ERROR/PROTOCOL_VIOLATION.
    :NOOP:    Sends ACK_REPLY back if required, otherwise it will do nothing.
    :REQUEST: Fall-back that sends an ERROR/BAD_REQUEST message.
    :REPLY:   Handles ACK_REPLY, sends ERROR/PROTOCOL_VIOLATION if it's not the ACK_REPLY.
    :DATA:    Sends ERROR/PROTOCOL_VIOLATION.
    :CANCEL:  Raises NotImplementedError
    :STATE:   Sends ERROR/PROTOCOL_VIOLATION.
    :CLOSE:   Disconnects from remote endpoint if defined, discards current session.
    :ERROR:   Sends ERROR/PROTOCOL_VIOLATION.

Abstract methods:
    :handle_cancel:  Handle CANCEL message.
"""
    def __init__(self, chn: TChannel, service_impl: TServiceImpl):
        super().__init__(chn, Origin.SERVICE)
        self.impl: TServiceImpl = service_impl
        self.handlers.update({MsgType.HELLO: self.on_hello,
                              MsgType.REQUEST: self.on_request,
                              MsgType.CANCEL: self.on_cancel,
                              MsgType.REPLY: self.on_reply,
                              MsgType.WELCOME: self.send_protocol_violation,
                              MsgType.STATE: self.send_protocol_violation,
                              MsgType.ERROR: self.send_protocol_violation,
                             })
    def close(self):
        "Close all connections to Clients."
        log.debug("%s.close", self.__class__.__name__)
        while self.sessions:
            _, session = self.sessions.popitem()
            self.send(self.protocol.create_message_for(MsgType.CLOSE, session.token),
                      session)
            if session.endpoint:
                self.chn.disconnect(session.endpoint)
    def on_ack_reply(self, session: TSession, msg: ReplyMessage) -> None:
        "Called to handle REPLY/ACK_REPLY message."
        log.debug("%s.on_ack_reply", self.__class__.__name__)
    def on_unknown(self, session: TSession, msg: Message) -> None:
        """Default message handler for unrecognized messages.
Sends ERROR/INVALID_MESSAGE back to the client.
"""
        log.debug("%s.on_unknown", self.__class__.__name__)
        errmsg = self.protocol.create_error_for(session.greeting, ErrorCode.INVALID_MESSAGE)
        err = errmsg.add_error()
        err.description = "Invalid message, type: %d" % msg.message_type
        self.send(errmsg, session)
    def on_data(self, session: TSession, msg: DataMessage) -> None:
        "Handle DATA message."
        log.debug("%s.on_data", self.__class__.__name__)
        err_msg = self.protocol.create_error_for(msg, ErrorCode.PROTOCOL_VIOLATION)
        err = err_msg.add_error()
        err.description = "Data message not allowed"
        self.send(err_msg, session)
    def on_close(self, session: TSession, msg: CloseMessage) -> None:
        """Handle CLOSE message.

If 'endpoint` is set in session, disconnects underlying channel from it. Then discards
the session.
"""
        log.debug("%s.on_close", self.__class__.__name__)
        if session.endpoint:
            self.chn.disconnect(session.endpoint)
        self.discard_session(session)
    def on_hello(self, session: TSession, msg: HelloMessage) -> None:
        """Handle HELLO message.

This method MUST be overridden in child classes to send WELCOME message back to the client.
Overriding method must call `super().on_hello(session, msg)`.
"""
        log.debug("%s.on_hello", self.__class__.__name__)
        session.greeting = msg
    def on_request(self, session: TSession, msg: RequestMessage) -> None:
        """Handle Client REQUEST message.

This is implementation that provides a fall-back handler for unsupported request codes (not
defined in `handler` table) that sends back an ERROR/BAD_REQUEST message.
"""
        log.debug("%s.on_request", self.__class__.__name__)
        self.send(self.protocol.create_error_for(msg, ErrorCode.BAD_REQUEST), session)
    def on_cancel(self, session: TSession, msg: CancelMessage) -> None:
        "Handle CANCEL message."
        raise NotImplementedError
    def on_reply(self, session: TSession, msg: ReplyMessage):
        """Handle REPLY message.

Unless it's an ACK_REPLY, client SHALL not send REPLY messages to the service.
"""
        log.debug("%s.on_reply", self.__class__.__name__)
        if msg.has_ack_reply():
            self.on_ack_reply(session, msg)
        else:
            self.send_protocol_violation(session, msg)


def exception_for(msg: ErrorMessage) -> ServiceError:
    "Returns ServiceError exception from ERROR message."
    desc = [f"{msg.error_code.name}, relates to {msg.relates_to.name}"]
    for err in msg.errors:
        desc.append(f"#{err.code} : {err.description}")
    exc = ServiceError('\n'.join(desc))
    log.debug("exception_for()->%s", exc)
    return exc

class ClientMessageHandler(BaseFBSPlHandler):
    """Base class for Client handlers that process messages from Service.

Uses `handlers` dictionary to route received messages to appropriate handlers.
Child classes may update this table with their own handlers in `__init__()`.
Dictionary key could be either a `tuple(<message_type>,<type_data>)` or just `<message_type>`.

Attributes:
    :last_token_seen: Token from last message processed by `on_*` handlers or None.

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
    :on_reply:   Handle Service REPLY message.
    :on_data:    Handle DATA message.
    :on_state:   Handle STATE message.
    :on_error:   Handle ERROR message received from Service.
"""
    def __init__(self, chn: TChannel):
        super().__init__(chn, Origin.CLIENT)
        self.handlers.update({MsgType.WELCOME: self.on_welcome,
                              MsgType.REPLY: self.on_reply,
                              MsgType.STATE: self.on_state,
                              MsgType.ERROR: self.on_error,
                              MsgType.HELLO: self.raise_protocol_violation,
                              MsgType.REQUEST: self.raise_protocol_violation,
                              MsgType.CANCEL: self.raise_protocol_violation,
                             })
        self._tcnt = 0 # Token generator
        self.last_token_seen: bytes = None
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
    def new_token(self) -> Token:
        "Return newly created `token` value."
        self._tcnt += 1
        return pack('Q', self._tcnt)
    def close(self):
        "Close connection to Service."
        log.debug("%s.close", self.__class__.__name__)
        session = self.get_session()
        try:
            self.send(self.protocol.create_message_for(MsgType.CLOSE,
                                                       session.greeting.token), session)
        except:
            # channel could be already closed from other side, as we are closing it too
            # we can ignore any send errors
            pass
        self.discard_session(session)
    def get_response(self, token: Token, timeout: int = None) -> bool:
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
        log.debug("%s.get_response", self.__class__.__name__)
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
                self.dispatch(session, msg)
            if self.last_token_seen and self.last_token_seen in (token, session.greeting.token):
                return True
            if timeout:
                stop = round((monotonic() - start) * 1000) >= timeout
        return False
    def on_unknown(self, session: TSession, msg: Message):
        "Default message handler for unrecognized messages. Raises `ServiceError`."
        log.debug("%s.on_unknown", self.__class__.__name__)
        raise ServiceError("Unhandled %s message from service" % msg.message_type.name)
    def on_close(self, session: TSession, msg: CloseMessage) -> None:
        """Handle CLOSE message.

If 'endpoint` is set in session, disconnects underlying channel from it. Then discards
the session and raises `ServiceError`.
"""
        log.debug("%s.on_close", self.__class__.__name__)
        self.last_token_seen = msg.token
        if session.endpoint:
            self.chn.disconnect(session.endpoint)
        self.discard_session(session)
        raise ServiceError("The service has closed the connection.")
    def on_welcome(self, session: TSession, msg: WelcomeMessage) -> None:
        """Handle WELCOME message.

Save WELCOME message into session.greeting, or raise `ServiceError` for unexpected WELCOME.
"""
        log.debug("%s.on_welcome", self.__class__.__name__)
        self.last_token_seen = msg.token
        if not session.greeting:
            session.greeting = msg
        else:
            raise ServiceError("Unexpected WELCOME message")
    def on_reply(self, session: TSession, msg: ReplyMessage) -> None:
        "Handle Service REPLY message."
        raise NotImplementedError
    def on_state(self, session: TSession, msg: StateMessage) -> None:
        "Handle STATE message."
        raise NotImplementedError
    def on_error(self, session: TSession, msg: ErrorMessage) -> None:
        "Handle ERROR message received from Service."
        raise NotImplementedError

