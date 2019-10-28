#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/datapipe.py
# DESCRIPTION:    Butler Data Pipes
# CREATED:        22.10.2019
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

"""Saturnin SDK - Butler Data Pipes
"""

import logging
import typing as t
from saturnin.sdk.types import Enum, SocketMode, ZMQAddress, StopError
from saturnin.sdk.base import DealerChannel
from saturnin.sdk.config import MIMEOption
from saturnin.sdk.protocol.fbdp import PipeSocket, BaseFBDPHandler, PipeClientHandler, \
     PipeServerHandler, Session, ErrorCode, MsgType, Message

# Logger

log = logging.getLogger(__name__)

END_OF_DATA = object()

# Enums

class PipeState(Enum):
    "Data Pipe state"
    UNKNOWN = 0
    OPEN = 1
    READY = 2
    TRANSMITTING = 3
    CLOSED = 4

# Types

TOnPipeClosed = t.Callable[['DataPipe', Session, Message], None]
TOnAcceptClient = t.Callable[['DataPipe', Session, MIMEOption], int]
TOnServerReady = t.Callable[['DataPipe', Session, int], int]
TOnAcceptData = t.Callable[['DataPipe', Session, bytes], int]
TOnProduceData = t.Callable[['DataPipe', Session], t.Any]

# Classes

class DataPipe:
    """Data pipe descriptor.

Attributes:
    :state:       Pipe state
    :pipe_id:     Pipe identification
    :mode:        Pipe mode
    :address:     Pipe ZMQ address
    :socket:      Pipe socket
    :data_format: Data format
    :mime_type:   MIME type
    :mime_params: MIME type parameters
    :chn:         Pipe channel

Abstract methods:
    :on_pipe_closed:   General callback called when pipe is closed.
    :on_accept_client: SERVER callback. Validates and processes client connection request.
    :on_server_ready:  CLIENT callback executed when non-zero READY is received from server.
    :on_accept_data:   CONSUMER callback that process DATA from producer.
    :on_produce_data:  PRODUCER callback that returns DATA for consumer.
"""
    def __init__(self, on_close: TOnPipeClosed = None):
        self.state = PipeState.UNKNOWN
        self.chn: DealerChannel = None
        self.hnd: BaseFBDPHandler = None
        self.pipe_id: str = None
        self.mode: SocketMode = None
        self.address: ZMQAddress = None
        self.socket: PipeSocket = None
        self.batch_size: int = 50
        self.data_format: str = ''
        self.mime_type: str = None
        self.mime_params: t.Dict[str, str] = None
        self.active: bool = False
        #
        self.on_pipe_closed: TOnPipeClosed = on_close
        self.on_accept_client: TOnAcceptClient = None
        self.on_server_ready: TOnServerReady = None
        self.on_accept_data: TOnAcceptData = None
        self.on_produce_data: TOnProduceData = None
    def __on_accept_client(self, handler: BaseFBDPHandler, session: Session,
                         data_pipe: str, pipe_stream: PipeSocket, data_format: str) -> int:
        "SERVER callback. Validates and processes client connection request."
        if __debug__:
            log.debug('%s._on_accept_client(%s,%s,%s) [%s]', self.__class__.__name__,
                      data_pipe, pipe_stream, data_format, self.pipe_id)
        if data_pipe != self.pipe_id:
            raise StopError("Unknown data pipe '%s'" % data_pipe,
                            code = ErrorCode.PIPE_ENDPOINT_UNAVAILABLE)
        elif pipe_stream != self.socket:
            raise StopError("'%s' stream not available" % pipe_stream.name,
                            code = ErrorCode.PIPE_ENDPOINT_UNAVAILABLE)
        mime = MIMEOption('data_format', '')
        try:
            mime.set_value(data_format)
        except:
            StopError("Only MIME data formats supported",
                      code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        result = session.batch_size
        if self.on_accept_client:
            result = self.on_accept_client(self, session, mime)
        self.active = True
        return result
    def __on_server_ready(self, handler: PipeClientHandler, session: Session, batch_size: int) -> int:
        self.active = True
        if self.on_server_ready:
            return self.on_server_ready(self, session, batch_size)
        return min(batch_size, session.batch_size)
    def __on_batch_start(self, handler: BaseFBDPHandler, session: Session) -> None:
        while session.transmit > 0:
            try:
                data: t.Any = self.on_produce_data(self, session)
            except StopError:
                handler.send_close(session, ErrorCode.OK)
                return
            except Exception as exc:
                handler.send_close(session, ErrorCode.INVALID_DATA, exc=exc)
                return
            if data is None:
                # Data are not available at this time, schedule for later
                self.chn.manager.defer(self.__on_batch_start, handler, session)
                return
            msg = handler.protocol.create_message_for(MsgType.DATA)
            msg.data_frame = data
            session.transmit -= 1
            handler.send(msg, session)
        if self.mode == SocketMode.BIND and session.transmit == 0:
            try:
                self.hnd.send_ready(session, handler.batch_size)
            except Exception as exc:
                exc.__traceback__ = None
                log.error("Pipe READY send failed [SRV:%s:%s]", session.pipe_stream,
                          session.data_pipe, exc_info=exc)
    def __on_accept_data(self, handler: BaseFBDPHandler, session: Session, data: t.Any) -> int:
        assert self.on_accept_data
        return self.on_accept_data(self, session, data)
    def __on_pipe_closed(self, handler: BaseFBDPHandler, session: Session, msg: Message) -> None:
        if __debug__:
            log.debug('%s.__on_pipe_closed() [%s]', self.__class__.__name__, self.pipe_id)
        self.active = False
        if self.on_pipe_closed:
            self.on_pipe_closed(self, session, msg)
    def set_channel(self, channel: DealerChannel) -> None:
        "Assign transmission channel for data pipe."
        self.chn = channel
    def set_mode(self, mode: SocketMode) -> None:
        assert self.chn is not None
        self.mode = mode
        if mode == SocketMode.BIND:
            self.hnd = PipeServerHandler(self.batch_size)
            self.hnd.on_accept_client = self.__on_accept_client
        else:
            self.hnd = PipeClientHandler(self.batch_size)
            self.hnd.on_server_ready = self.__on_server_ready
        self.hnd.on_batch_start = self.__on_batch_start
        self.hnd.on_accept_data = self.__on_accept_data
        self.hnd.on_pipe_closed = self.__on_pipe_closed
        self.chn.set_handler(self.hnd)
    def set_format(self, mime: MIMEOption, default: str = None) -> None:
        "Set MIME data format"
        fmt = mime
        if mime.value is None and default:
            fmt = MIMEOption('', '')
            fmt.set_value(default)
        if fmt.value is None:
            raise ValueError("MIME format not specified")
        self.data_format = fmt.value
        self.mime_type = fmt.mime_type
        self.mime_params = dict(fmt.mime_params)
    def close(self) -> None:
        "Close the data pipe"
        self.hnd.close()
    def open(self) -> None:
        "Open the data pipe"
        assert self.chn is not None
        assert self.hnd is not None
        assert self.pipe_id is not None
        assert self.mode is not None
        assert self.address is not None
        assert self.socket is not None
        if self.mode == SocketMode.CONNECT:
            self.hnd.open(self.address, self.pipe_id, self.socket, self.data_format)
        else:
            self.chn.bind(self.address)

class InputPipe(DataPipe):
    "INPUT data pipe"
    def open(self) -> None:
        "Open the data pipe"
        assert self.chn is not None
        assert self.hnd is not None
        assert self.pipe_id is not None
        assert self.mode is not None
        assert self.address is not None
        if self.mode == SocketMode.CONNECT:
            self.socket = PipeSocket.OUTPUT
            self.hnd.open(self.address, self.pipe_id, self.socket, self.data_format)
        else:
            self.socket = PipeSocket.INPUT
            log.info("Pipe BIND [%s:%s]", t.cast(PipeSocket, self.socket).name, self.pipe_id)
            self.chn.bind(self.address)

class OutputPipe(DataPipe):
    "OUTPUT data pipe"
    def open(self) -> None:
        "Open the data pipe"
        assert self.chn is not None
        assert self.hnd is not None
        assert self.pipe_id is not None
        assert self.mode is not None
        assert self.address is not None
        if self.mode == SocketMode.CONNECT:
            self.socket = PipeSocket.INPUT
            self.hnd.open(self.address, self.pipe_id, self.socket, self.data_format)
        else:
            self.socket = PipeSocket.OUTPUT
            log.info("Pipe BIND [%s:%s]", t.cast(PipeSocket, self.socket).name, self.pipe_id)
            self.chn.bind(self.address)

