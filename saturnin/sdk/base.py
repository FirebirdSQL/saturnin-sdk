#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/base.py
# DESCRIPTION:    Base classes and other definitions
# CREATED:        28.2.2019
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

"Saturnin SDK - Base classes and other definitions"

from typing import Any, Dict, List, Sequence, ValuesView, Optional
from uuid import uuid5, NAMESPACE_OID, UUID
from weakref import proxy, ref
from enum import Enum, Flag, auto
from zmq import Context, Socket, Frame, Poller, POLLIN, ZMQError
from zmq import NOBLOCK, ROUTER, DEALER, PUSH, PULL, PUB, SUB, XPUB, XSUB, PAIR

# pylint: disable=R0902, R0913

# Constants

INTERNAL_ROUTE = b'INTERNAL'

# firebird.butler.platform.saturnin-sdk
PLATFORM_OID = '1.3.6.1.4.1.53446.1.2.0'
PLATFORM_UID = uuid5(NAMESPACE_OID, PLATFORM_OID)
PLATFORM_VERSION = '0.2'

# firebird.butler.vendor.firebird
VENDOR_OID = '1.3.6.1.4.1.53446.1.3.0'
VENDOR_UID = uuid5(NAMESPACE_OID, VENDOR_OID)

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

#  Exceptions
class InvalidMessageError(Exception):
    "A formal error was detected in a message"
class ChannelError(Exception):
    "Transmission channel error"
class ServiceError(Exception):
    "Error raised by service"

# Functions
def peer_role(my_role: Origin) -> Origin:
    "Return role for peer."
    return Origin.CLIENT if my_role == Origin.SERVICE else Origin.SERVICE

def get_unique_key(dict_: Dict[int, Any]) -> int:
    """Returns key value that is not in dictionary."""
    i = 1
    while i in dict_:
        i += 1
    return i


# Manager for ZMQ channels
class ChannelManager:
    "Manager of ZeroMQ communication channels."
    def __init__(self, context: Context):
        """Manager of ZeroMQ communication channels.

Arguments:
    :context: ZMQ Context instance.
"""
        self.ctx = context
        self._ch: Dict[int, BaseChannel] = {}
        self._poller = Poller()
        self.__chmap = {}
    def create_socket(self, socket_type: int, **kwargs) -> Socket:
        """Create new ZMQ socket.

Arguments:
    :socket_type: The socket type, which can be any of the 0MQ socket types:
                  REQ, REP, PUB, SUB, PAIR, DEALER, ROUTER, PULL, PUSH, etc.
    :**kwargs:    will be passed to the __init__ method of the socket class.
"""
        return self.ctx.socket(socket_type, **kwargs)
    def add(self, channel):
        """Add channel to the manager."""
        channel._mngr = proxy(self) # pylint: disable=W0212
        i = get_unique_key(self._ch)
        channel.uid = i
        self._ch[i] = channel
        channel.create_socket()
    def remove(self, channel):
        """Remove channel from the manager."""
        self.unregister(channel)
        channel._mngr = None # pylint: disable=W0212
        channel.uid = None
        del self._ch[channel.uid]
    def is_registered(self, channel) -> bool:
        """Returns True if channel is registered in Poller."""
        assert channel.socket, "Channel socket not created"
        return channel.socket in self._poller._map # pylint: disable=W0212
    def register(self, channel):
        """Register channel in Poller."""
        if not self.is_registered(channel):
            self._poller.register(channel.socket, POLLIN)
            self.__chmap[channel.socket] = channel
    def unregister(self, channel):
        """Unregister channel from Poller."""
        if self.is_registered(channel):
            self._poller.unregister(channel.socket)
            del self.__chmap[channel.socket]
    def wait(self, timeout: Optional[int] = None) -> Dict:
        """Wait for I/O events on registered channnels.

Arguments:
    :timeout: The timeout in milliseconds. `None` value means `infinite`.

Returns:
    {BaseChannel: events} dictionary.
"""
        return dict((self.__chmap[skt], e) for skt, e in self._poller.poll(timeout))
    def shutdown(self, *args):
        """Terminate all managed channels.

Arguments:
    :linger: Linger parameter for `BaseChannel.terminate()`
"""
        for chn in self.channels:
            self.unregister(chn)
            chn.close(*args)

    channels: ValuesView = property(lambda self: self._ch.values(), # pylint: disable=W0212
                                    doc="Channels associated with manager")

# Base Classes
class BaseMessage:
    """Base class for protocol message.

The base class simply holds ZMQ multipart message in its `data` attribute. Child classes
can override :meth:`from_zmsg` and :meth:`as_zmsg` methods to pack/unpack some or all
parts of ZMQ message into their own attributes. In such a case, unpacked data must be
removed from `data` attribute.

Abstract methods:
   :validate_zmsg: Verifies that sequence of ZMQ data frames is a valid message.

Attributes:
    :data:  Sequence of data frames
"""
    def __init__(self, protocol):
        self._pr = ref(protocol)
        self.data: List[bytes] = []
    def from_zmsg(self, frames: Sequence) -> None:
        """Populate message data from sequence of ZMQ data frames.

Arguments:
    :frames: Sequence of frames that should be deserialized.
"""
        self.data = frames
    def as_zmsg(self) -> Sequence:
        """Returns message as sequence of ZMQ data frames."""
        zmsg = []
        zmsg.extend(self.data)
        return zmsg
    def clear(self) -> None:
        """Clears message attributes."""
        self.data.clear()
    @classmethod
    def validate_zmsg(cls, zmsg: Sequence) -> None:
        """Verifies that sequence of ZMQ zmsg frames is a valid message.

This method MUST be overridden in child classes.

Arguments:
    :zmsg: Sequence of ZMQ zmsg frames for validation.

Raises:
    :InvalidMessageError: When formal error is detected in any zmsg frame.
"""
        raise NotImplementedError
    def has_data(self) -> bool:
        """Returns True if `data` attribute is not empty."""
        return len(self.data) > 0
    def has_zmq_frames(self) -> bool:
        """Returns True if any item in `data` attribute is a zmq.Frame object (False if all are
bytes).
"""
        for item in self.data:
            if isinstance(item, Frame):
                return True
        return False

class BaseSession: # pylint: disable=R0903
    """Base Peer Session class.

Attributes:
    :routing_id: (bytes) Channel routing ID
    :endpoint: (str) Connected service endpoint address, if any
"""
    def __init__(self, routing_id: bytes):
        self.routing_id = routing_id
        self.endpoint: Optional[str] = None

class BaseProtocol:
    """Base class for protocol.

The main purpose of protocol class is to validate ZMQ messages and create protocol messages.
This base class uses :class:`BaseMessage` for all protocol messages. Child classes can
use various `BaseMessage` descendants.

Attributes:
   :uid:        UUID instance that identifies the protocol. MUST be set in child class.
   :revision:   Protocol revision (default 1)
   :on_invalid: Optional `ON_INVALID_CALLBACK` invoked when :meth:`is_valid()` detects an
                invalid message.

Abstract methods:
   :validate: Verifies that sequence of ZMQ data frames is a valid protocol message.
   :has_greeting: Returns True if protocol uses greeting messages.
   :validate_greeting: Validates the introductory message from peer.
   :create_session: Create peer session
with peer.
"""
    def __init__(self):
        """Communication protocol.
"""
        # firebird.butler.protocol
        self.uid: UUID = uuid5(NAMESPACE_OID, '1.3.6.1.4.1.53446.1.5')
        self.revision: int = 1
    def create_message(self) -> BaseMessage: # pylint: disable=R0201
        """Create new base protocol message.

Returns:
   New instance of base message class used by protocol.
"""
        return BaseMessage(self)
    def has_greeting(self) -> bool:
        "Returns True if protocol uses greeting messages."
        raise NotImplementedError
    def parse(self, zmsg: Sequence) -> BaseMessage:
        """Parse ZMQ message into protocol message.

This method should be overridden in child classes, as the base class produces BaseMessage instances.

Arguments:
    :zmsg: Sequence of bytes or :class:`zmq.Frame` instances that must be a valid protocol message.

Returns:
    New protocol message instance with parsed ZMQ message.

Raises:
    :InvalidMessageError: If message is not a valid protocol message.
"""
        msg = self.create_message()
        msg.from_zmsg(zmsg)
        return msg
    def is_valid(self, zmsg: List, origin: Origin) -> bool:
        """Return True if ZMQ message is a valid protocol message, otherwise returns False.

Exceptions other than `InvalidMessageError` are not caught.

Arguments:
    :zmsg: Sequence of bytes or :class:`zmq.Frame` instances
    :origin: Origin of received message in protocol context.
"""
        try:
            self.validate(zmsg, origin)
        except InvalidMessageError:
            return False
        else:
            return True
    def validate(self, zmsg: Sequence, origin: Origin, **kwargs) -> None:
        """Verifies that sequence of ZMQ data frames is a valid protocol message.

This method MUST be overridden in child classes.

Arguments:
    :zmsg:   Sequence of bytes or :class:`zmq.Frame` instances.
    :origin: Origin of received message in protocol context.
    :kwargs: Additional keyword-only arguments

Raises:
    :InvalidMessageError: If message is not a valid protocol message.
"""
        raise NotImplementedError

class BaseChannel:
    """Base Class for ZeroMQ communication channel (socket).

Attributes:
    :routed:      True if channel uses internal routing
    :socket_type: ZMQ socket type.
    :direction:   Direction of transmission [default: SocketDirection.BOTH]
    :mode:        BIND/CONNECT mode for socket.
    :identity:    Identity value for ZMQ socket.
    :socket:      ZMQ socket for transmission of messages.
    :handler:     Protocol handler used to process messages received from peer(s).
    :uid:         Unique channel ID used by channel manager.
    :manager:     The channel manager to which this channel belongs.
    :mngr_poll:   True if channel should register its socket into manager Poller.
    :endpoints:   List of binded/connected endpoints.

Abstract methods:
   :create_socket: Create ZMQ socket for this channel.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True, send_timeout: int = 0):
        """Base Class for ZeroMQ communication channel (socket).

Arguments:
    :identity: Identity for ZMQ socket.
    :mngr_poll: True to register into Channel Manager `Poller`.
"""
        self.socket_type = None
        self.direction = Direction.BOTH
        self._identity = identity
        self._mngr_poll = mngr_poll
        self._send_timeout = send_timeout
        self._mode = SocketMode.UNKNOWN
        self.handler = None
        self.uid = None
        self._mngr = None
        self.socket: Socket = None
        self.routed = False
        self.endpoints: List[str] = []
    def __set_mngr_poll(self, value: bool):
        "Sets mngr_poll."
        if not value:
            self.manager.unregister(self)
        elif self.endpoints:
            self.manager.register(self)
        self._mngr_poll = value
    def __set_send_timeout(self, timeout: int) -> None:
        "Sets send_timeout."
        self.socket.sndtimeo = timeout
        self._send_timeout = timeout
    def drop_socket(self):
        "Unconditionally drops the ZMQ socket."
        try:
            if self.socket:
                self.socket.close()
        except ZMQError:
            pass
        self.socket = None
    def create_socket(self):
        """Create ZMQ socket for this channel.

Called when channel is assigned to manager.
"""
        self.socket = self.manager.create_socket(self.socket_type)
        if self._identity:
            self.socket.identity = self._identity
        self.socket.sndtimeo = self._send_timeout
    def on_first_endpoint(self):
        """Called after the first endpoint is successfully opened.

Registers channel socket into manager Poller if required.
"""
        if self.mngr_poll:
            self.manager.register(self)
    def on_last_endpoint(self):
        """Called after the last endpoint is successfully closed.

Unregisters channel socket from manager Poller.
"""
        self.manager.unregister(self)
    def bind(self, endpoint: str):
        """Bind the 0MQ socket to an address.

Raises:
    :ChannelError: On attempt to a) bind another endpoint for PAIR socket, or b) bind
    to already binded endpoint.
"""
        assert self.mode != SocketMode.CONNECT
        if (self.socket.socket_type == PAIR) and self.endpoints:
            raise ChannelError("Cannot open multiple endpoints for PAIR socket")
        if endpoint in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' already openned")
        self.socket.bind(endpoint)
        self._mode = SocketMode.BIND
        if not self.endpoints:
            self.on_first_endpoint()
        self.endpoints.append(endpoint)
    def unbind(self, endpoint: Optional[str] = None):
        """Unbind from an address (undoes a call to `bind()`).

Arguments:
    :endpoint: Endpoint address or None to unbind from all binded endpoints.

Raises:
    :ChannelError: If channel is not binded to specified `endpoint`.
"""
        assert self.mode == SocketMode.BIND
        if endpoint and endpoint not in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' not openned")
        addrs = [endpoint] if endpoint else self.endpoints
        for addr in addrs:
            self.socket.unbind(addr)
            self.endpoints.remove(addr)
        if not self.endpoints:
            self.on_last_endpoint()
            self._mode = SocketMode.UNKNOWN
    def connect(self, endpoint: str, routing_id: Optional[bytes] = None):
        """Connect to a remote channel.

Raises:
    :ChannelError: On attempt to a) connect another endpoint for PAIR socket, or b) connect
    to already connected endpoint.
"""
        assert self.mode != SocketMode.BIND
        if (self.socket.socket_type == PAIR) and self.endpoints:
            raise ChannelError("Cannot open multiple endpoints for PAIR socket")
        if endpoint in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' already openned")
        if self.routed and routing_id:
            self.socket.connect_rid = routing_id
        self.socket.connect(endpoint)
        self._mode = SocketMode.CONNECT
        if not self.endpoints:
            self.on_first_endpoint()
        self.endpoints.append(endpoint)
    def disconnect(self, endpoint: Optional[str] = None):
        """Disconnect from a remote socket (undoes a call to `connect()`).

Arguments:
    :endpoint: Endpoint address or None to disconnect from all connected endpoints.

Raises:
    :ChannelError: If channel is not connected to specified `endpoint`.
"""
        assert self.mode == SocketMode.CONNECT
        if endpoint and endpoint not in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' not openned")
        addrs = [endpoint] if endpoint else self.endpoints
        for addr in addrs:
            self.socket.disconnect(addr)
            self.endpoints.remove(addr)
        if not self.endpoints:
            self.on_last_endpoint()
            self._mode = SocketMode.UNKNOWN
    def send(self, zmsg: List):
        "Send ZMQ multipart message."
        assert Direction.OUT in self.direction, \
               "Call to send() on RECEIVE-only channel"
        self.socket.send_multipart(zmsg, NOBLOCK)
    def receive(self) -> List:
        "Receive ZMQ multipart message."
        assert Direction.IN in self.direction, \
               "Call to receive() on SEND-only channel"
        return self.socket.recv_multipart(NOBLOCK)
    def close(self, *args):
        """Permanently closes the channel by closing the ZMQ scoket.

Arguments:
    :linger: (int) Linger parameter for `zmq.socket.close()`
"""
        self.socket.close(*args)
        if self.handler:
            self.handler.on_close()
    # pylint: disable=W0212
    mode: SocketMode = property(lambda self: self._mode, doc="ZMQ Socket mode")
    manager: ChannelManager = property(lambda self: self._mngr, doc="Channel manager")
    identity: bytes = property(lambda self: self._identity, doc="ZMQ socket identity")
    mngr_poll = property(lambda self: self._mngr_poll, __set_mngr_poll,
                         doc="Uses central Poller")
    send_timeout = property(lambda self: self._send_timeout, __set_send_timeout,
                            doc="Timeout for send operations")

class BaseHandler:
    """Base class for message handlers.

Attributes:
    :chn: Handled I/O channel
    :role: Peer role
    :sessions: Dictionary of active sessions, key=routing_id
    :protocol: Protocol used [default: BaseProtocol]

Abstract methods:
    :dispatch: Process message received from peer.
"""
    def __init__(self, chn: BaseChannel, role: Origin,
                 session_class: BaseSession = BaseSession):
        """Message handler initialization.

Arguments:
    :chn: Channel to be handled.
    :role: The role that the handler performs.
    :session_class: Class for session objects.
"""
        self.chn: BaseChannel = chn
        chn.handler = self
        self.__role = role
        self.routed = isinstance(chn, RouterChannel)
        self.sessions: Dict[bytes, BaseSession] = {}
        self.protocol = BaseProtocol()
        self.__scls = session_class
    def create_session(self, routing_id: bytes):
        """Session object factory."""
        session = self.__scls(routing_id)
        self.sessions[routing_id] = session
        return session
    def get_session(self, routing_id: bytes = INTERNAL_ROUTE) -> BaseSession:
        "Returns session object registered for route or None."
        return self.sessions.get(routing_id)
    def discard_session(self, session):
        """Discard session object.

If `session.endpoint` value is set, it also disconnects channel from this endpoint.

Arguments:
    :session: Session object to be discarded.
"""
        if session.endpoint:
            self.chn.disconnect(session.endpoint)
        del self.sessions[session.routing_id]
    def on_close(self):
        "Called by channel on Close event."
    def on_invalid_message(self, session: BaseSession, exc: InvalidMessageError):
        "Called by `receive()` on Invalid Message event."
    def on_invalid_greeting(self, exc: InvalidMessageError):
        "Called by `receive()` on Invalid Greeting event."
    def on_dispatch_error(self, session: BaseSession, exc: Exception):
        "Called by `receive()` on Exception unhandled by `dispatch()`."
    def connect_peer(self, endpoint: str, routing_id: bytes = None) -> BaseSession:
        """Connects to a remote peer and creates a session for this connection.

Arguments:
    :endpoint:   Endpoint for connection.
    :routing_id: Channel routing ID (required for routed channels)
"""
        if self.chn.routed:
            assert routing_id
        else:
            routing_id = INTERNAL_ROUTE
        self.chn.connect(endpoint, routing_id)
        session = self.create_session(routing_id)
        session.endpoint = endpoint
        return session
    def receive(self, zmsg: Optional[List] = None):
        "Receive and process message from channel."
        if not zmsg:
            zmsg = self.chn.receive()
        routing_id = zmsg.pop(0) if self.chn.routed else INTERNAL_ROUTE
        session = self.sessions.get(routing_id)
        if not session:
            if self.protocol.has_greeting():
                try:
                    self.protocol.validate(zmsg, peer_role(self.role), greeting=True)
                except InvalidMessageError as exc:
                    self.on_invalid_greeting(exc)
            session = self.create_session(routing_id)
        try:
            msg = self.protocol.parse(zmsg)
        except InvalidMessageError as exc:
            self.on_invalid_message(session, exc)
            return
        try:
            self.dispatch(session, msg)
        except Exception as exc: # pylint: disable=W0703
            self.on_dispatch_error(session, exc)
    def send(self, msg: BaseMessage, session: BaseSession = None):
        "Send message through channel."
        zmsg = msg.as_zmsg()
        if self.chn.routed:
            assert session
            zmsg.insert(0, session.routing_id)
        self.chn.send(zmsg)
    def dispatch(self, session: BaseSession, msg: BaseMessage):
        """Process message received from peer.

This method MUST be overridden in child classes.

Arguments:
    :session: Session instance.
    :msg:     Received message.
"""
        raise NotImplementedError

    role: Origin = property(lambda self: self.__role,
                            doc="The role that the handler performs.")

class BaseServiceImpl:
    """Base Firebird Butler Service implementation.

Configuration options (retrieved via `get()`):
    :shutdown_linger:  ZMQ Linger value used on shutdown [Default 0].

Abstract methods:
    :initialize: Service initialization.
"""
    def get(self, name: str, *args) -> Any:
        """Returns value of variable.

Child chlasses must define the attribute with given name, or `get_<name>()` callable that
takes no arguments.

Arguments:
    :name:    Name of the variable.
    :default: Optional defaut value.

Raises:
    AttributeError if value couldn't be retrieved and there is no default value provided.
"""
        if hasattr(self, f'get_{name}'):
            fce = getattr(self, f'get_{name}')
            value = fce()
        else:
            value = getattr(self, name, *args)
        return value
    def initialize(self, svc):
        """Service initialization.

Must create the channel manager with zmq.context and at least one communication channel.
"""
        raise NotImplementedError
    def finalize(self, svc):
        """Service finalization.

Base implementation performs only ChannelManager.shutdown(). If `shutdown_linger`
is not defined, uses linger 0 for forced shutdown.
"""
        svc.mngr.shutdown(self.get('shutdown_linger', 0))
    def configure(self, svc):
        "Service configuration. Default implementation does nothing."

class BaseService:
    """Base Firebird Butler Service.

(Base)Service defines structure of the service, while actual implementation of individual
structural parts is provided by (Base)ServiceImpl instance.

Attributes:
    :impl: Service implementation.
    :mngr: ChannelManager instance. NOT INITIALIZED.

Abstract methods:
    :run: Runs the service.
"""
    def __init__(self, impl: BaseServiceImpl):
        """If context is not provided, it uses global Context instance.

Arguments:
    :impl:    Service implementation.
"""
        self.impl = impl
        self.mngr: ChannelManager = None
    def validate(self):
        """Validate that service is properly initialized and configured.

Raises:
    :AssertionError: When any issue is detected.
"""
        assert isinstance(self.mngr, ChannelManager), "Channel manager required"
        assert isinstance(self.mngr.ctx, Context), "Channel manager without ZMQ context"
        assert self.mngr.channels, "Channel manager without channels"
        for chn in self.mngr.channels:
            assert chn.handler, "Channel without handler"
    def run(self):
        """Runs the service."""
        raise NotImplementedError
    def start(self):
        """Starts the service. It initializes, configures and then runs the service.
Performs finalization when run() finishes.
"""
        self.impl.initialize(self)
        self.impl.configure(self)
        try:
            self.validate()
        except AssertionError as exc:
            raise Exception("Service is not properly initialized and configured.") from exc
        try:
            self.run()
        finally:
            self.impl.finalize(self)

# Channels for individual ZMQ socket types
class DealerChannel(BaseChannel):
    """Communication channel over DEALER socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = DEALER

class PushChannel(BaseChannel):
    """Communication channel over PUSH socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = PUSH
        self.direction = Direction.OUT

class PullChannel(BaseChannel):
    """Communication channel over PULL socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = PULL
        self.direction = Direction.IN

class PubChannel(BaseChannel):
    """Communication channel over PUB socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = PUB
        self.direction = Direction.OUT

class SubChannel(BaseChannel):
    """Communication channel over SUB socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = SUB
        self.direction = Direction.IN
    def subscribe(self, topic: bytes):
        "Subscribe to topic"
        self.socket.subscribe = topic
    def unsubscribe(self, topic: bytes):
        "Unsubscribe from topic"
        self.socket.unsubscribe = topic

class XPubChannel(BaseChannel):
    """Communication channel over XPUB socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = XPUB
    def create_socket(self):
        "Create XPUB socket for this channel."
        super().create_socket()
        self.socket.xpub_verboser = 1 # pass subscribe and unsubscribe messages on XPUB socket

class XSubChannel(BaseChannel):
    """Communication channel over XSUB socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = XSUB
    def subscribe(self, topic: bytes):
        "Subscribe to topic"
        self.socket.send_multipart(b'\x01', topic)
    def unsubscribe(self, topic: bytes):
        "Unsubscribe to topic"
        self.socket.send_multipart(b'\x00', topic)

class PairChannel(BaseChannel):
    """Communication channel over PAIR socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = PAIR

class RouterChannel(BaseChannel):
    """Communication channel over ROUTER socket.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True):
        super().__init__(identity, mngr_poll)
        self.socket_type = ROUTER
        self.routed = True
    def create_socket(self):
        super().create_socket()
        self.socket.router_mandatory = 1
