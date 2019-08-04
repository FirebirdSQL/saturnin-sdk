#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/fbdp.py
# DESCRIPTION:    Firebird Butler Data Pipe Protocol
# CREATED:        30.7.2019
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

"Saturnin SDK - Firebird Butler Data Pipe Protocol"

import logging
from typing import Sequence
from uuid import UUID, uuid5, NAMESPACE_OID
from struct import unpack
from enum import IntEnum
from .types import TChannel, TMessage, TSession, TProtocol, TMessageFactory, \
     Origin, InvalidMessageError
from .base import BaseProtocol, BaseMessage, BaseSession, BaseMessageHandler, msg_bytes

# Constants

PROTOCOL_OID = '1.3.6.1.4.1.53446.1.5.5' # firebird.butler.protocol.fbdp
PROTOCOL_UID = uuid5(NAMESPACE_OID, PROTOCOL_OID)
PROTOCOL_REVISION = 1

HEADER_FMT_FULL = '!4sBBH'
HEADER_FMT = '!4xBBH'
FOURCC = b'FBDP'
VERSION_MASK = 7

# Enums

class MsgType(IntEnum):
    "FBDP Message Type"
    UNKNOWN = 0 # Not a valid option, defined only to handle undefined values
    OPEN = 1    # attachment to pipe socket
    CLOSE = 2   # detachment from pipe socket
    READY = 3   # confirmation, transfer voucher
    DATA = 4    # data

class PipeSocket(IntEnum):
    "Data Pipe Socket identification"
    UNKNOWN_PIPE_SOCKET = 0 # Not a valid option, defined only to handle undefined values
    PIPE_INPUT = 1
    PIPE_OUPUT = 2
    PIPE_MONITOR = 3

# Logger

log = logging.getLogger(__name__)

# Functions

# Classes

class Message(BaseMessage):
    """FBDP Message.

Attributes:
    :message_type: Type of message
    :type_data:    Data associated with message (int)
    :data:         List of message frames
"""
    def __init__(self):
        super().__init__()
        self.message_type: MsgType = MsgType.UNKNOWN
        self.type_data: int = 0
    def from_zmsg(self, frames: Sequence) -> None:
        """Populate message attributes from sequence of ZMQ data frames. The `data`
attribute contains a copy of all message frames.

Arguments:
    :frames: Sequence of frames that should be deserialized.
"""
        self.data = list(frames)
        _, msg_type, self.type_data = unpack(HEADER_FMT, msg_bytes(self.data[0]))
        self.message_type = MsgType(msg_type)
        if self.message_type == MsgType.OPEN:
            pass # unpack OPEN data frame
    def clear(self) -> None:
        """Clears message attributes."""
        super().clear()
        self.message_type = MsgType.UNKNOWN
        self.type_data = 0
        # clear unpacked OPEN data frame
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        """Verifies that sequence of ZMQ zmsg frames is a valid FBDP message.

Arguments:
    :zmsg: Sequence of ZMQ message frames for validation.

Raises:
    :InvalidMessageError: When formal error is detected.
"""
        if not zmsg:
            raise InvalidMessageError("Empty message")
        fbdp_header = msg_bytes(zmsg[0])
        if len(fbdp_header) != 8:
            raise InvalidMessageError("Message header must be 8 bytes long")
        try:
            fourcc, control_byte, msg_type, msg_data = unpack(HEADER_FMT_FULL, fbdp_header)
        except Exception as exp:
            raise InvalidMessageError("Can't parse the control frame") from exp
        if fourcc != FOURCC:
            raise InvalidMessageError("Invalid FourCC")
        if (control_byte & VERSION_MASK) != PROTOCOL_REVISION:
            raise InvalidMessageError("Invalid protocol version")
        if (control_byte >> 3) > 0:
            raise InvalidMessageError("Invalid flags")
        try:
            message_type = MsgType(msg_type)
        except ValueError:
            raise InvalidMessageError("Illegal message type %s" % msg_type)
        if len(zmsg) > 2:
            raise InvalidMessageError("Too many frames (allowed 2, found %s)" % len(zmsg))
        if len(zmsg) == 2:
            if not ((message_type == MsgType.OPEN) or
                    (message_type == MsgType.DATA and msg_data != 0)):
                raise InvalidMessageError("Data frame not allowed")
        if message_type == MsgType.OPEN:
            pass # validate OPEN data frame
    def copy(self) -> TMessage:
        "Returns copy of the message."
        msg = super().copy()
        msg.message_type = self.message_type
        msg.type_data = self.type_data
        if self.message_type == MsgType.OPEN:
            pass # unpack OPEN data frame
        return msg

class Protocol(BaseProtocol):
    """9/FBDP - Firebird Butler Data Pipe Protocol

The main purpose of protocol class is to validate ZMQ messages and create FBDP messages.

Class attributes:
   :OID:        string with protocol OID (dot notation).
   :UID:        UUID instance that identifies the protocol.
   :REVISION:   Protocol revision

Attributes:
    :message_factory: Callable that returns FBDP Message instance.
"""
    OID: str = PROTOCOL_OID
    UID: UUID = PROTOCOL_UID
    REVISION: int = PROTOCOL_REVISION
    def __init__(self, message_factory: TMessageFactory = Message):
        self.message_factory: TMessageFactory = message_factory
    @classmethod
    def instance(cls) -> TProtocol:
        """Returns global FBDP protocol instance with default message factory."""
        return _FBDP_INSTANCE
    def has_greeting(self) -> bool:
        "Returns True if protocol uses greeting messages."
        return True
    def parse(self, zmsg: Sequence) -> TMessage:
        """Parse ZMQ message into protocol message.

Arguments:
    :zmsg: Sequence of bytes or :class:`zmq.Frame` instances that must be a valid protocol message.

Returns:
    New protocol message instance with parsed ZMQ message. The BaseProtocol implementation
    returns BaseMessage instance.

Raises:
    :InvalidMessageError: If message is not a valid protocol message.
"""
        msg = self.message_factory()
        msg.from_zmsg(zmsg)
        return msg
    def validate(self, zmsg: Sequence, origin: Origin, **kwargs) -> None:
        """Validate that ZMQ message is a valid FBSP message.

Arguments:
    :zmsg:   Sequence of bytes or :class:`zmq.Frame` instances.
    :origin: Origin of received message in protocol context.
    :kwargs: Additional keyword-only arguments.

Supported kwargs:
    :greeting: (bool) If True, the message is validated as greeting message from origin.

Raises:
    :InvalidMessageError: If message is not a valid FBSP message.
"""
        Message.validate_zmsg(zmsg)
        if kwargs.get('greeting', False):
            _, msg_type, _ = unpack(HEADER_FMT, msg_bytes(zmsg[0]))
            message_type = MsgType(msg_type)
            if not (((message_type == MsgType.OPEN) and (origin == Origin.CLIENT)) or
                    ((message_type == MsgType.READY) and (origin == Origin.SERVICE)) or
                    ((message_type == MsgType.CLOSE) and (origin == Origin.SERVICE))):
                raise InvalidMessageError("Invalid greeting %s from %s" %
                                          (message_type.name, origin.name))

_FBDP_INSTANCE = Protocol()

class BaseFBDPHandler(BaseMessageHandler):
    """Base class for FBDP message handlers.

Uses :attr:`handlers` dictionary to route received messages to appropriate handlers.

.. important::

   Protocol uses message factory that returns singleton message instance owned by handler.

Messages handled:
    :unknown: Raises InvalidMessageError
    :OPEN:    Raises NotImplementedError
    :CLOSE:   Raises NotImplementedError
    :READY:   Raises NotImplementedError
    :DATA:    Raises NotImplementedError

Abstract methods:
    :on_open:    Handle OPEN message.
    :on_close:   Handle CLOSE message.
    :on_ready:   Handle READY message.
    :on_data:    Handle DATA message.
"""
    def __init__(self, chn: TChannel, role: Origin,
                 session_class: TSession = BaseSession, resume_timeout: int = 10):
        super().__init__(chn, role, session_class, resume_timeout)
        self.__msg = Message()
        self.handlers = {MsgType.OPEN: self.on_open,
                         MsgType.CLOSE: self.on_close,
                         MsgType.READY: self.on_ready,
                         MsgType.DATA: self.on_data,
                        }
        self.protocol = Protocol(self.message_factory)
    def message_factory(self) -> Message:
        "Returns private Message instance. The instance is cleared before returning."
        self.__msg.clear()
        return self.__msg
    def on_unknown(self, session: TSession, msg: Message) -> None:
        """Default message handler. Called by `dispatch` when no appropriate message handler
is found in :attr:`handlers` dictionary.
"""
        raise InvalidMessageError("Invalid FBDP message")
    def on_open(self, session: TSession, msg: Message) -> None:
        "Handle OPEN message."
        raise NotImplementedError
    def on_close(self, session: TSession, msg: Message) -> None:
        "Handle CLOSE message."
        raise NotImplementedError
    def on_ready(self, session: TSession, msg: Message) -> None:
        "Handle READY message."
        raise NotImplementedError
    def on_data(self, session: TSession, msg: Message) -> None:
        "Handle DATA message."
        raise NotImplementedError
    def dispatch(self, session: TSession, msg: TMessage) -> None:
        """Process message received from peer.

Uses :attr:`handlers` dictionary to find appropriate handler for the messsage.
If no appropriate handler is located, calls :meth:`on_unknown()`.

Arguments:
    :session: Session attached to peer.
    :msg:     FBDP message received from client.
"""
        log.debug("%s.dispatch", self.__class__.__name__)
        handler = self.handlers.get(msg.message_type)
        if handler:
            handler(session, msg)
        else:
            self.on_unknown(session, msg)

class ClientFBDPHandler(BaseFBDPHandler):
    """Base class for Client handlers that process messages from Data Pipe.

Messages handled:
    :unknown: Raises InvalidMessageError
    :OPEN:
    :CLOSE:
    :READY:
    :DATA:
"""
    def __init__(self, chn: TChannel, resume_timeout: int = 10):
        super().__init__(chn, Origin.CLIENT, BaseSession, resume_timeout)
        self.pipe_socket = PipeSocket.UNKNOWN_PIPE_SOCKET
    def on_open(self, session: TSession, msg: Message) -> None:
        "Handle OPEN message."
        raise NotImplementedError
    def on_close(self, session: TSession, msg: Message) -> None:
        "Handle CLOSE message."
        raise NotImplementedError
    def on_ready(self, session: TSession, msg: Message) -> None:
        "Handle READY message."
        raise NotImplementedError
    def on_data(self, session: TSession, msg: Message) -> None:
        "Handle DATA message."
        raise NotImplementedError
    def open(self, pipe_socket: PipeSocket) -> None:
        """Attach to pipe socket."""
    def close(self) -> None:
        """Detach from pipe socket."""
