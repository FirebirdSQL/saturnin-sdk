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

import sys
import logging
from typing import Any, Dict, List, Sequence, ValuesView, Optional
from uuid import uuid5, NAMESPACE_OID, UUID
from weakref import proxy
from time import sleep
from zmq import Context, Socket, Frame, Poller, POLLIN, ZMQError
from zmq import NOBLOCK, ROUTER, DEALER, PUSH, PULL, PUB, SUB, XPUB, XSUB, PAIR
from .types import TChannel, TMessageHandler, TProtocol, TServiceImpl, \
     TService, TSession, TMessage, ZMQAddress, Origin, SocketMode, Direction, \
     InvalidMessageError, ChannelError, ServiceError

# Constants

INTERNAL_ROUTE = b'INTERNAL'

# Logger

log = logging.getLogger(__name__)

# Functions
def peer_role(my_role: Origin) -> Origin:
    "Return role for peer."
    return Origin.CLIENT if my_role == Origin.SERVICE else Origin.SERVICE

def get_unique_key(dict_: Dict[int, Any]) -> int:
    """Returns int key value that is not in dictionary."""
    i = 1
    while i in dict_:
        i += 1
    return i

def load(spec: str) -> Any:
    """Return object from module. Module is imported if necessary.

Arguments:
    :spec: Object specification in format module[.submodule.[submodule...]]:object_name

"""
    module_spec, name = spec.split(':')
    if module_spec in sys.modules:
        module = sys.modules[module_spec]
    else:
        module = __import__(module_spec, globals(), locals(), [name], 0)
    return getattr(module, name)

# Manager for ZMQ channels
class ChannelManager:
    "Manager of ZeroMQ communication channels."
    def __init__(self, context: Context):
        """Manager of ZeroMQ communication channels.

Arguments:
    :context: ZMQ Context instance.
"""
        self.ctx: Context = context
        self._ch: Dict[int, TChannel] = {}
        self._poller: Poller = Poller()
        self.__chmap: Dict[Socket, TChannel] = {}
    def create_socket(self, socket_type: int, **kwargs) -> Socket:
        """Create new ZMQ socket.

Arguments:
    :socket_type: The socket type, which can be any of the 0MQ socket types:
                  REQ, REP, PUB, SUB, PAIR, DEALER, ROUTER, PULL, PUSH, etc.
    :**kwargs:    will be passed to the __init__ method of the socket class.
"""
        return self.ctx.socket(socket_type, **kwargs)
    def add(self, channel: TChannel) -> None:
        """Add channel to the manager."""
        log.debug("%s.add", self.__class__.__name__)
        channel._mngr = proxy(self)
        i = get_unique_key(self._ch)
        channel.uid = i
        self._ch[i] = channel
        channel.create_socket()
    def remove(self, channel: TChannel) -> None:
        """Remove channel from the manager."""
        log.debug("%s.remove", self.__class__.__name__)
        self.unregister(channel)
        channel._mngr = None
        del self._ch[channel.uid]
        channel.uid = None
    def is_registered(self, channel: TChannel) -> bool:
        """Returns True if channel is registered in Poller."""
        assert channel.socket, "Channel socket not created"
        return channel.socket in self._poller._map
    def register(self, channel: TChannel) -> None:
        """Register channel in Poller."""
        log.debug("%s.register", self.__class__.__name__)
        if not self.is_registered(channel):
            self._poller.register(channel.socket, POLLIN)
            self.__chmap[channel.socket] = channel
    def unregister(self, channel: TChannel) -> None:
        """Unregister channel from Poller."""
        log.debug("%s.unregister", self.__class__.__name__)
        if self.is_registered(channel):
            self._poller.unregister(channel.socket)
            del self.__chmap[channel.socket]
    def wait(self, timeout: Optional[int] = None) -> Dict:
        """Wait for I/O events on registered channnels.

Arguments:
    :timeout: The timeout in milliseconds. `None` value means `infinite`.

Returns:
    {TChannel: events} dictionary.
"""
        return dict((self.__chmap[skt], e) for skt, e in self._poller.poll(timeout))
    def shutdown(self, *args) -> None:
        """Terminate all managed channels.

Arguments:
    :linger: Linger parameter for `BaseChannel.terminate()`
"""
        log.debug("Shutting down channel manager")
        for chn in self.channels:
            self.unregister(chn)
            chn.close(*args)

    channels: ValuesView = property(lambda self: self._ch.values(),
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
    def __init__(self):
        self.data: List[bytes] = []
    def from_zmsg(self, frames: Sequence) -> None:
        """Populate message data from sequence of ZMQ data frames.

Arguments:
    :frames: Sequence of frames that should be deserialized.
"""
        self.data = list(frames)
    def as_zmsg(self) -> Sequence:
        """Returns message as sequence of ZMQ data frames."""
        zmsg = []
        zmsg.extend(self.data)
        return zmsg
    def clear(self) -> None:
        """Clears message data."""
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


class BaseSession:
    """Base Peer Session class.

Attributes:
    :routing_id: (bytes) Channel routing ID
    :endpoint: (str) Connected service endpoint address, if any
"""
    def __init__(self, routing_id: bytes):
        self.routing_id: bytes = routing_id
        self.endpoint_address: Optional[ZMQAddress] = None


class BaseProtocol:
    """Base class for protocol.

The main purpose of protocol class is to validate ZMQ messages and create protocol messages.
This base class defines common interface for parsing and validation. Descendant classes
typically add methods for creation of protocol messages.

Class attributes:
   :OID:        string with protocol OID (dot notation). MUST be set in child class.
   :UID:        UUID instance that identifies the protocol. MUST be set in child class.
   :REVISION:   Protocol revision (default 1)
"""
    OID: str = '1.3.6.1.4.1.53446.1.5' # firebird.butler.protocol
    UID: UUID = uuid5(NAMESPACE_OID, OID)
    REVISION: int = 1
    def has_greeting(self) -> bool:
        """Returns True if protocol uses greeting messages.

The BaseProtocol always returns False.
"""
        return False
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
        msg = BaseMessage()
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

The BaseProtocol implementation does nothing.

Arguments:
    :zmsg:   Sequence of bytes or :class:`zmq.Frame` instances.
    :origin: Origin of received message in protocol context.
    :kwargs: Additional keyword-only arguments

Raises:
    :InvalidMessageError: If message is not a valid protocol message.
"""
        return

class BaseChannel:
    """Base Class for ZeroMQ communication channel (socket).

Attributes:
    :routed:      True if channel uses internal routing
    :socket_type: ZMQ socket type.
    :direction:   Direction of transmission [default: SocketDirection.BOTH]
    :socket:      ZMQ socket for transmission of messages.
    :handler:     Message handler used to process messages received from peer(s).
    :uid:         Unique channel ID used by channel manager.
    :mngr_poll:   True if channel should register its socket into manager Poller.
    :endpoints:   List of binded/connected endpoints.

R/O attributes:
    :mode:        BIND/CONNECT mode for socket.
    :manager:     The channel manager to which this channel belongs.
    :identity:    Identity value for ZMQ socket.

Abstract methods:
   :create_socket: Create ZMQ socket for this channel.
"""
    def __init__(self, identity: bytes, mngr_poll: bool = True, send_timeout: int = 0,
                 flags: int = NOBLOCK):
        """Base Class for ZeroMQ communication channel (socket).

Arguments:
    :identity: Identity for ZMQ socket.
    :mngr_poll: True to register into Channel Manager `Poller`. [default=True]
    :send_timeout: Timeout for send operation on the socket. [default=0]
    :flags: Flags for send() and receive(). [default=NOBLOCK]
"""
        self.socket_type: int = None
        self.direction: Direction = Direction.BOTH
        self._identity: bytes = identity
        self._mngr_poll: bool = mngr_poll
        self._send_timeout: int = send_timeout
        self._mode: SocketMode = SocketMode.UNKNOWN
        self.handler: TMessageHandler = None
        self.uid: int = None
        self._mngr: ChannelManager = None
        self.socket: Socket = None
        self.routed: bool = False
        self.endpoints: List[ZMQAddress] = []
        self.flags = flags
    def __set_mngr_poll(self, value: bool) -> None:
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
    def drop_socket(self) -> None:
        "Unconditionally drops the ZMQ socket."
        try:
            if self.socket:
                self.socket.close()
        except ZMQError:
            pass
        self.socket = None
    def create_socket(self) -> None:
        """Create ZMQ socket for this channel.

Called when channel is assigned to manager.
"""
        log.debug("%s.create_socket [%s/%s]", self.__class__.__name__, self.socket_type,
                  self.identity)
        self.socket = self.manager.create_socket(self.socket_type)
        if self._identity:
            self.socket.identity = self._identity
        self.socket.sndtimeo = self._send_timeout
    def on_first_endpoint(self) -> None:
        """Called after the first endpoint is successfully opened.

Registers channel socket into manager Poller if required.
"""
        if self.mngr_poll:
            self.manager.register(self)
    def on_last_endpoint(self) -> None:
        """Called after the last endpoint is successfully closed.

Unregisters channel socket from manager Poller.
"""
        self.manager.unregister(self)
    def bind(self, endpoint: ZMQAddress) -> ZMQAddress:
        """Bind the 0MQ socket to an address.

Returns:
    The endpoint address. The returned address MAY differ from original address when
    wildcard specification is used.

Raises:
    :ChannelError: On attempt to a) bind another endpoint for PAIR socket, or b) bind
    to already binded endpoint.
"""
        log.debug("%s.bind(%s)", self.__class__.__name__, endpoint)
        assert self.mode != SocketMode.CONNECT
        if (self.socket.socket_type == PAIR) and self.endpoints:
            raise ChannelError("Cannot open multiple endpoints for PAIR socket")
        if endpoint in self.endpoints:
            raise ChannelError(f"Endpoint '{endpoint}' already openned")
        self.socket.bind(endpoint)
        if '*' in endpoint:
            endpoint = str(self.socket.LAST_ENDPOINT, 'utf8')
        self._mode = SocketMode.BIND
        if not self.endpoints:
            self.on_first_endpoint()
        self.endpoints.append(endpoint)
        return endpoint
    def unbind(self, endpoint: Optional[ZMQAddress] = None) -> None:
        """Unbind from an address (undoes a call to `bind()`).

Arguments:
    :endpoint: Endpoint address or None to unbind from all binded endpoints.
               Note: The address must be the same as the addresss returned by `bind()`.

Raises:
    :ChannelError: If channel is not binded to specified `endpoint`.
"""
        log.debug("%s.unbind(%s)", self.__class__.__name__, endpoint)
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
    def connect(self, endpoint: ZMQAddress, routing_id: Optional[bytes] = None) -> None:
        """Connect to a remote channel.

Raises:
    :ChannelError: On attempt to a) connect another endpoint for PAIR socket, or b) connect
    to already connected endpoint.
"""
        log.debug("%s.connect(%s,%s)", self.__class__.__name__, endpoint, routing_id)
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
    def disconnect(self, endpoint: Optional[ZMQAddress] = None) -> None:
        """Disconnect from a remote socket (undoes a call to `connect()`).

Arguments:
    :endpoint: Endpoint address or None to disconnect from all connected endpoints.
               Note: The address must be the same as the addresss returned by `connect()`.

Raises:
    :ChannelError: If channel is not connected to specified `endpoint`.
"""
        log.debug("%s.disconnect(%s)", self.__class__.__name__, endpoint)
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
    def send(self, zmsg: List) -> None:
        "Send ZMQ multipart message."
        log.debug("%s.send", self.__class__.__name__)
        assert Direction.OUT in self.direction, "Call to send() on RECEIVE-only channel"
        self.socket.send_multipart(zmsg, self.flags)
    def receive(self) -> List:
        "Receive ZMQ multipart message."
        log.debug("%s.receive", self.__class__.__name__)
        assert Direction.IN in self.direction, "Call to receive() on SEND-only channel"
        return self.socket.recv_multipart(self.flags)
    def close(self, *args) -> None:
        """Permanently closes the channel by closing the ZMQ scoket.

Arguments:
    :linger: (int) Linger parameter for `zmq.socket.close()`
"""
        log.debug("%s.close", self.__class__.__name__)
        self.socket.close(*args)
        if self.handler:
            self.handler.closing()
    def is_active(self) -> bool:
        "Returns True if channel is active (binded or connected)."
        return bool(self.endpoints)

    mode: SocketMode = property(lambda self: self._mode, doc="ZMQ Socket mode")
    manager: ChannelManager = property(lambda self: self._mngr, doc="Channel manager")
    identity: bytes = property(lambda self: self._identity, doc="ZMQ socket identity")
    mngr_poll: bool = property(lambda self: self._mngr_poll, __set_mngr_poll,
                               doc="Uses central Poller")
    send_timeout: int = property(lambda self: self._send_timeout, __set_send_timeout,
                                 doc="Timeout for send operations")


class BaseMessageHandler:
    """Base class for message handlers.

Attributes:
    :chn: Handled I/O channel
    :role: Peer role
    :sessions: Dictionary of active sessions, key=routing_id
    :protocol: Protocol used [default: BaseProtocol]

Abstract methods:
    :dispatch: Process message received from peer.
"""
    def __init__(self, chn: TChannel, role: Origin,
                 session_class: TSession = BaseSession):
        """Message handler initialization.

Arguments:
    :chn: Channel to be handled.
    :role: The role that the handler performs.
    :session_class: Class for session objects.
"""
        self.chn: TChannel = chn
        chn.handler = self
        self.__role: Origin = role
        self.sessions: Dict[bytes, BaseSession] = {}
        self.protocol: TProtocol = BaseProtocol()
        self.__scls: TSession = session_class
    def create_session(self, routing_id: bytes) -> TSession:
        """Session object factory."""
        log.debug("%s.create_session(%s)", self.__class__.__name__, routing_id)
        session = self.__scls(routing_id)
        self.sessions[routing_id] = session
        return session
    def get_session(self, routing_id: bytes = INTERNAL_ROUTE) -> TSession:
        "Returns session object registered for route or None."
        return self.sessions.get(routing_id)
    def discard_session(self, session: TSession) -> None:
        """Discard session object.

If `session.endpoint` value is set, it also disconnects channel from this endpoint.

Arguments:
    :session: Session object to be discarded.
"""
        log.debug("%s.discard_session(%s)", self.__class__.__name__, session.routing_id)
        if session.endpoint_address:
            self.chn.disconnect(session.endpoint_address)
        del self.sessions[session.routing_id]
    def closing(self) -> None:
        """Called by channel on Close event.

The base implementation does nothing.
"""
    def on_invalid_message(self, session: TSession, exc: InvalidMessageError) -> None:
        """Called by `receive()` when message parsing raises InvalidMessageError.

The base implementation does nothing.
"""
        log.error("%s.on_invalid_message(%s/%s)", self.__class__.__name__,
                  session.routing_id, exc)
    def on_invalid_greeting(self, routing_id: bytes, exc: InvalidMessageError) -> None:
        """Called by `receive()` when greeting message parsing raises InvalidMessageError.

The base implementation does nothing.
"""
        log.error("%s.on_invalid_greeting(%s/%s)", self.__class__.__name__, routing_id, exc)
    def on_dispatch_error(self, session: TSession, msg: TMessage, exc: Exception) -> None:
        """Called by `receive()` on Exception unhandled by `dispatch()`.

The base implementation does nothing.
"""
        log.error("%s.on_dispatch_error(%s/%s)", self.__class__.__name__,
                  session.routing_id, exc)
    def connect_peer(self, endpoint_address: str, routing_id: bytes = None) -> TSession:
        """Connects to a remote peer and creates a session for this connection.

Arguments:
    :endpoint_address: Endpoint for connection.
    :routing_id:       Channel routing ID (required for routed channels)
"""
        log.debug("%s.connect_peer(%s,%s)", self.__class__.__name__, endpoint_address, routing_id)
        if self.chn.routed:
            assert routing_id
        else:
            routing_id = INTERNAL_ROUTE
        self.chn.connect(endpoint_address, routing_id)
        session = self.create_session(routing_id)
        session.endpoint_address = endpoint_address
        return session
    def receive(self, zmsg: Optional[List] = None) -> None:
        "Receive and process message from channel."
        if not zmsg:
            zmsg = self.chn.receive()
        routing_id: bytes = zmsg.pop(0) if self.chn.routed else INTERNAL_ROUTE
        session = self.sessions.get(routing_id)
        if not session:
            if self.protocol.has_greeting():
                try:
                    self.protocol.validate(zmsg, peer_role(self.role), greeting=True)
                except InvalidMessageError as exc:
                    self.on_invalid_greeting(routing_id, exc)
                    return
            session = self.create_session(routing_id)
        try:
            msg = self.protocol.parse(zmsg)
        except InvalidMessageError as exc:
            self.on_invalid_message(session, exc)
            return
        try:
            self.dispatch(session, msg)
        except Exception as exc:
            self.on_dispatch_error(session, msg, exc)
    def send(self, msg: TMessage, session: TSession = None) -> None:
        "Send message through channel."
        zmsg = msg.as_zmsg()
        if self.chn.routed:
            assert session
            zmsg.insert(0, session.routing_id)
        self.chn.send(zmsg)
    def dispatch(self, session: TSession, msg: TMessage) -> None:
        """Process message received from peer.

This method MUST be overridden in child classes.

Arguments:
    :session: Session instance.
    :msg:     Received message.
"""
        raise NotImplementedError
    def is_active(self) -> bool:
        "Returns True if habndler has any active session (connection)."
        return bool(self.sessions)

    role: Origin = property(lambda self: self.__role,
                            doc="The role that the handler performs.")

class DummyEvent:
    """Dummy Event class.
"""
    def __init__(self):
        self._flag: bool = False
    def is_set(self) -> bool:
        "Return true if and only if the internal flag is true."
        return self._flag
    isSet = is_set
    def set(self) -> None:
        "Set the internal flag to true."
        self._flag = True
    def clear(self) -> None:
        "Reset the internal flag to false."
        self._flag = False
    def wait(self, timeout=0) -> bool:
        "Sleep for specified number of seconds and then return the internal flag state."
        sleep(timeout)
        return self._flag


class BaseServiceImpl:
    """Base Firebird Butler Service implementation.

Attributes:
    :mngr:       ChannelManager instance. NOT INITIALIZED.
    :stop_event: Event object used to stop the service.

Configuration options (retrieved via `get()`):
    :shutdown_linger:  ZMQ Linger value used on shutdown [Default 0].

Abstract methods:
    :initialize: Service initialization.
"""
    def __init__(self, stop_event: Any):
        self.stop_event = stop_event
        self.mngr: ChannelManager = None
    def get(self, name: str, *args) -> Any:
        """Returns value of variable.

Child chlasses must define the attribute with given name, or `get_<name>()` callable that
takes no arguments.

Arguments:
    :name:    Name of the variable.
    :default: Optional defaut value. Used only for attribute, not callable.

Raises:
    AttributeError if value couldn't be retrieved and there is no default value provided.
"""
        if hasattr(self, f'get_{name}'):
            fce = getattr(self, f'get_{name}')
            value = fce()
        else:
            value = getattr(self, name, *args)
        return value
    def validate(self) -> None:
        """Validate that service implementation defines all necessary configuration options
needed for initialization and configuration.

Raises:
    :AssertionError: When any issue is detected.
"""
        log.debug("%s.validate", self.__class__.__name__)
        assert isinstance(self.mngr, ChannelManager), "Channel manager required"
        assert isinstance(self.mngr.ctx, Context), "Channel manager without ZMQ context"
        assert self.mngr.channels, "Channel manager without channels"
        for chn in self.mngr.channels:
            assert chn.handler, "Channel without handler"
    def initialize(self, svc: TService) -> None:
        """Service initialization.

Must create the channel manager with zmq.context and at least one communication channel.
"""
        raise NotImplementedError
    def finalize(self, svc: TService) -> None:
        """Service finalization.

Base implementation only calls shutdown() on service ChannelManager. If `shutdown_linger`
is not defined, uses linger 1 for forced shutdown.
"""
        log.debug("%s.finalize", self.__class__.__name__)
        self.mngr.shutdown(self.get('shutdown_linger', 1))
    def configure(self, svc: TService) -> None:
        "Service configuration. Default implementation does nothing."
    def on_idle(self) -> None:
        """Should by called by service when waiting for messages exceeds timeout. Default
implementation does nothing.
"""

class BaseService:
    """Base Firebird Butler Service.

(Base)Service defines structure of the service, while actual implementation of individual
structural parts is provided by (Base)ServiceImpl instance.

Attributes:
    :impl: Service implementation.

Abstract methods:
    :run: Runs the service.
"""
    def __init__(self, impl: TServiceImpl):
        """
Arguments:
    :impl:    Service implementation.
"""
        self.impl: TServiceImpl = impl
        self.__ready = False
    def get_provider_address(self, interface_uid: bytes) -> Optional[str]:
        """Return address of interface provider or None if it's not available. Default
implementation always returns None.
"""
        return None
    def validate(self) -> None:
        """Validate that service is properly initialized and configured.

Raises:
    :AssertionError: When any issue is detected.
"""
        log.debug("%s.validate", self.__class__.__name__)
        self.impl.validate()
    def run(self) -> None:
        """Runs the service."""
        raise NotImplementedError
    def initialize(self) -> None:
        """Runs initialization, configuration and validation of the service implementation.

Raises:
    :ServiceError: When service is not properly initialized and configured.
"""
        log.info("Initialization of the service %s:%s", self.impl.agent.name, self.impl.agent.uid)
        self.impl.initialize(self)
        self.impl.configure(self)
        try:
            self.validate()
        except AssertionError as exc:
            raise ServiceError("Service is not properly initialized and configured.") from exc
        self.__ready = True
    def start(self) -> None:
        """Starts the service. Initializes the service if necessary. Performs finalization
when run() finishes.
"""
        log.info("Starting service %s:%s", self.impl.agent.name, self.impl.agent.uid)
        if not self.__ready:
            self.initialize()
        try:
            self.run()
        finally:
            self.impl.finalize(self)
        log.info("Service %s:%s stopped", self.impl.agent.name, self.impl.agent.uid)
    ready: bool = property(lambda self: self.__ready, doc="True if service is ready to start")

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
