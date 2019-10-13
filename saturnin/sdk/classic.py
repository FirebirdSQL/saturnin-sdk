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

"""Saturnin SDK - Classic Firebird Butler Service

Classical services run their own message loop and do not use any asynchronous
programming techniques or Python libraries. Running a service effectively blocks
the main thread, so if an application needs to perform other tasks or if you need
to run multiple services in parallel in one application, each service must run
in a separate thread or subprocess.
"""

import logging
import typing as t
import uuid
from os import getpid
import ctypes
import platform
import threading
import multiprocessing
import zmq
from google.protobuf.struct_pb2 import Struct
from .types import Distinct, ZMQAddress, ZMQAddressList, ExecutionMode, ServiceFacilities, \
     PeerDescriptor, ServiceDescriptor, SaturninError
from .service import MicroserviceImpl, BaseService, load
from .config import MicroserviceConfig

# Logger

log = logging.getLogger(__name__)

# Types

TRuntime = t.Union[None, threading.Thread, multiprocessing.Process]
TRuntimeEvent = t.Union[None, threading.Event, multiprocessing.Event]

# Classes

class SimpleService(BaseService):
    """Simple Firebird Butler Service.

Has simple Event-controlled I/O loop using `ChannelManager.wait()`. Incomming messages
are processed by `receive()` of channel handler.

Attributes:
    :mngr:    ChannelManager
    :timeout: How long (in milliseconds) it waits for incoming messages (default 1 sec).
"""
    def __init__(self, impl: MicroserviceImpl, zmq_context: zmq.Context, config: MicroserviceConfig):
        super().__init__(impl, zmq_context, config)
        self.impl: MicroserviceImpl = impl # to make type-checker happy
        self.timeout: int = 1000  # 1sec
    def run(self):
        """Runs the service until `stop_event` is set.

The I/O loop has next steps:

- It runs deferred ChannelManager tasks (typically resend operations). By default it runs
one deferred task per loop cycle, unless ServiceImpl-defined `all_deferred` is True.
- Uses ChannelManager.wait(timeout) for messages.
- One message per channel is received per loop cycle.
- If there are no messages on input, runs ServiceImpl.on_idle()
"""
        log.info("Service %s:%s started", self.impl.agent.name, self.impl.agent.uid)
        while not self.impl.stop_event.is_set():
            self.impl.mngr.process_deferred(self.impl.get('all_deferred', False))
            events = self.impl.mngr.wait(self.timeout)
            if events:
                for channel, event in events.items():
                    if event == zmq.POLLIN:
                        channel.handler.receive()
            else:
                self.impl.idle()
        log.info("Service %s:%s is shuting down", self.impl.agent.name, self.impl.agent.uid)

def service_run(peer_uid: uuid.UUID, config: MicroserviceConfig, svc_descriptor: ServiceDescriptor,
                stop_event: TRuntimeEvent, ctrl_addr: ZMQAddress, mode: ExecutionMode):
    "Process or thread target code to run the service."
    if __debug__: log.debug("service_run(%s)", mode.name)
    if mode == ExecutionMode.PROCESS:
        ctx = zmq.Context()
    else:
        ctx = zmq.Context.instance()
    pipe = ctx.socket(zmq.DEALER)
    pipe.CONNECT_TIMEOUT = 5000 # 5sec
    pipe.IMMEDIATE = 1
    pipe.LINGER = 5000 # 5sec
    pipe.SNDTIMEO = 5000 # 5sec
    if __debug__:
        log.debug("service_run: Connecting service control socket at %s", ctrl_addr)
    pipe.connect(ctrl_addr)
    #
    try:
        svc_implementation = load(svc_descriptor.implementation)
        svc_class = load(svc_descriptor.container)
        svc_impl = svc_implementation(svc_descriptor, stop_event)
        svc_impl.peer = PeerDescriptor(peer_uid, getpid(), platform.node())
        svc = svc_class(svc_impl, ctx, config)
        svc.initialize()
        pipe.send_pyobj(0)
        if hasattr(svc_impl, 'endpoints'):
            pipe.send_pyobj(svc_impl.endpoints)
        else:
            pipe.send_pyobj(None)
        if hasattr(svc_impl, 'facilities'):
            pipe.send_pyobj(svc_impl.facilities)
        else:
            pipe.send_pyobj(None)
        pipe.send_pyobj(svc_impl.peer)
        pipe.close()
        if __debug__: log.debug("service_run: Entering service")
        svc.start()
        if __debug__: log.debug("service_run: Exit from service")
    except zmq.ZMQError as zmqerr:
        log.error("service_run: Send to service control socket failed, error: [%s] %s",
                  zmqerr.errno, zmqerr)
    except KeyboardInterrupt:
        if __debug__: log.debug("service_run: KeyboardInterrupt")
    except Exception as exc:
        exc.__traceback__ = None
        log.error("service_run: Service execution failed", exc_info=exc)
        #log.exception("service_run: Service execution failed")
        if not pipe.closed:
            pipe.send_pyobj(1)
            pipe.send_pyobj(exc)
            pipe.close()
    finally:
        if not pipe.closed:
            pipe.close()
        if mode == ExecutionMode.PROCESS:
            if __debug__: log.debug("service_run: Terminating ZMQ context")
            ctx.term()

class ServiceExecutor(Distinct):
    """Service executor.

Attributes:
    :uid:        Peer UID.
    :name:       Service instance name.
    :endpoints:  List of service endpoints, or None for microservice.
    :descriptor: Service descriptor.
    :facilities: Service run-time facilities.
    :mode:       Service execution mode.
    :config:     Copy of configuration object used to start the service.
    :peer:       PeerDescriptor for running service or None
    :runtime:    None, or threading.Thread or multiprocessing.Process instance.
    :stop_event: Event used to stop the service.
"""
    def __init__(self, svc_descriptor: ServiceDescriptor, peer_uid: uuid.UUID = None,
                 name: str = None):
        """Initialization.

Arguments:
    :svc_descriptor: Service descriptor.
    :peer_uid: Optional instance (peer) ID [default: uuid1()].
    :name: Instance (peer) name [default: peer_id.hex].
"""
        self._peer_uid: uuid.UUID = peer_uid if peer_uid else uuid.uuid1()
        self.name: str = name if name else self.uid.hex
        self.descriptor: ServiceDescriptor = svc_descriptor
        self.facilities: ServiceFacilities = svc_descriptor.facilities
        self.mode: ExecutionMode = svc_descriptor.execution_mode
        self.config: MicroserviceConfig = None
        self.stop_event: TRuntimeEvent = None
        self.runtime: TRuntime = None
        self.peer: PeerDescriptor = None
    def is_running(self) -> bool:
        """Returns True if service is running."""
        if self.runtime is None:
            return False
        if self.runtime.is_alive():
            return True
        # It's dead, so dispose the runtime
        self.runtime = None
        return False
    def start(self, config: MicroserviceConfig, timeout: int=10000):
        """Start the service.

If `mode` is ANY or THREAD, the service is executed in it's own thread. Otherwise it is
executed in separate child process.

Arguments:
    :config:  Service configuration.
    :timeout: The timeout (in milliseconds) to wait for service to start [Default: DEFAULT_TIMEOUT].

Raises:
    :SaturninError: The service is already running.
    :TimeoutError:  The service did not start on time.
"""
        if __debug__: log.debug("%s(%s).start", self.__class__.__name__, self.name)
        if __debug__:
            timeout = None
        if self.is_running():
            raise SaturninError("The service is already running")
        #
        self.config = self.descriptor.config()
        proto = Struct()
        config.save_proto(proto)
        self.config.load_proto(proto)
        del proto
        #
        if 'execution_mode' in config.options:
            self.mode = config.execution_mode.value
        ctx: zmq.Context = zmq.Context.instance()
        pipe: zmq.Socket = ctx.socket(zmq.DEALER)
        uid_bytes: str = uuid.uuid1().hex
        try:
            addr: ZMQAddress
            if self.mode in (ExecutionMode.ANY, ExecutionMode.THREAD):
                addr = ZMQAddress('inproc://%s' % uid_bytes)
                pipe.bind(addr)
                self.stop_event = threading.Event()
                self.runtime = threading.Thread(target=service_run, name=self.name,
                                                args=(self.uid, config,
                                                      self.descriptor,
                                                      self.stop_event, addr,
                                                      ExecutionMode.THREAD))
            else:
                if platform.system() == 'Linux':
                    addr = ZMQAddress('ipc://@%s' % uid_bytes)
                else:
                    addr = ZMQAddress('tcp://127.0.0.1:*')
                if __debug__:
                    log.debug("%s(%s).start: Binding service control socket to %s",
                              self.__class__.__name__, self.name, addr)
                pipe.bind(addr)
                addr = ZMQAddress(pipe.LAST_ENDPOINT)
                if __debug__:
                    log.debug("%s(%s).start: Binded to %s",
                              self.__class__.__name__, self.name, addr)
                self.stop_event = multiprocessing.Event()
                self.runtime = multiprocessing.Process(target=service_run, name=self.name,
                                                       args=(self.uid, config,
                                                             self.descriptor,
                                                             self.stop_event, addr,
                                                             ExecutionMode.PROCESS))
            self.runtime.start()
            if pipe.poll(timeout, zmq.POLLIN) == 0:
                raise TimeoutError("The service did not start on time")
            msg = pipe.recv_pyobj()
            if msg == 0: # OK
                msg = pipe.recv_pyobj()
                if msg is not None:
                    setattr(self, '_endpoints', msg)
                msg = pipe.recv_pyobj()
                if msg is not None:
                    self.facilities = msg
                msg = pipe.recv_pyobj()
                self.peer = msg
            else: # Exception
                msg = pipe.recv_pyobj()
                raise SaturninError("Service start failed") from msg
        finally:
            pipe.LINGER = 0
            pipe.close()
    def stop(self, timeout: float=10.0):
        """Stop the service. Does nothing if service is not running.

Arguments:
    :timeout: None (infinity), or a floating point number specifying a timeout for
              the operation in seconds (or fractions thereof) [Default: 10s].

Raises:
    :TimeoutError:  The service did not stop on time.
"""
        if __debug__: log.debug("%s(%s).stop", self.__class__.__name__, self.name)
        if self.is_running():
            self.stop_event.set()
            self.runtime.join(timeout=timeout)
            if self.runtime.is_alive():
                raise TimeoutError("The service did not stop on time")
            self.runtime = None
            if __debug__:
                log.debug("%s(%s).stop: SUCCESS", self.__class__.__name__, self.name)
    def terminate(self):
        """Terminate the service.

Terminate should be called ONLY when call to stop() (with sensible timeout) fails.
Does nothing when service is not running.

Raises:
    :SaturninError:  When service termination fails.
"""
        if __debug__: log.debug("%s(%s).terminate", self.__class__.__name__, self.name)
        if self.is_running():
            tid = ctypes.c_long(self.runtime.ident)
            if isinstance(self.runtime, threading.Thread):
                res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(SystemExit))
                if res == 0:
                    raise SaturninError("Service termination failed due to invalid thread ID.")
                if res != 1:
                    # if it returns a number greater than one, you're in trouble,
                    # and you should call it again with exc=NULL to revert the effect
                    ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
                    raise SaturninError("Service termination failed due to "\
                                        "PyThreadState_SetAsyncExc failure")
            elif isinstance(self.runtime, multiprocessing.Process):
                self.runtime.terminate()
            else:
                raise SaturninError("Service termination failed - invalid runtime.")
    get_key = lambda self: self._peer_uid
    uid: uuid.UUID = property(fget=lambda self: self._peer_uid, doc="Instance (peer) ID")
    agent_uid: uuid.UUID = property(fget=lambda self: self.descriptor.agent.uid,
                                    doc="Agent ID")
    agent_name: str = property(fget=lambda self: self.descriptor.agent.name,
                               doc="Agent name")
    endpoints: ZMQAddressList = property(lambda self: getattr(self, '_endpoints', None),
                                          doc="Service endpoints")
