#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           saturnin/micro/textio/service.py
# DESCRIPTION:    Sample TEXTIO microservice (classic version)
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

"""Saturnin SDK examples - Sample TEXTIO microservice (classic version)

The TEXTIO microservice transfers data between a file and a Data Pipe.
"""

import logging
import typing as t
import os
from saturnin.core.types import SocketMode, ZMQAddress, ServiceFacilities, \
     ServiceDescriptor, StopError
from saturnin.core.base import DealerChannel
from saturnin.core.config import MIMEOption
from saturnin.core.protocol.fbdp import PipeSocket, BaseFBDPHandler, PipeClientHandler, \
     PipeServerHandler, Session, ErrorCode, MsgType, Message
from saturnin.core.service import MicroserviceImpl, BaseService
from .api import FileOpenMode, TextIOConfig
from time import sleep

# Logger

log = logging.getLogger(__name__)

# Functions

# Classes

class TextIOServiceImpl(MicroserviceImpl):
    """Implementation of TEXTIO microservice."""
    SYSIO = ('stdin', 'stdout', 'stderr')
    def __init__(self, descriptor: ServiceDescriptor, stop_event: t.Any):
        super().__init__(descriptor, stop_event)
        self.pipe_chn: DealerChannel = None
        self.stop_on_close = True
        self.data_pipe: str = None
        self.pipe_mode: SocketMode = None
        self.pipe_address: ZMQAddress = None
        self.pipe_socket: PipeSocket = None
        self.pipe_format: str = None
        self.pipe_mime_format: str = None
        self.pipe_format_params: t.Dict[str, str] = None
        self.file: t.IO = None
        self.filename: str = None
        self.file_mode: FileOpenMode = None
        self.file_format: str = None
        self.file_mime_type: str = None
        self.file_format_params: t.Dict[str, str] = None
        self.is_reader: bool = None
    def _open_file(self):
        """Open the input file."""
        self._close_file()
        log.debug('%s._open_file(%s:%s)', self.__class__.__name__, self.file_mode.name,
                  self.filename)
        if self.filename.lower() in self.SYSIO:
            fspec = self.SYSIO.index(self.filename.lower())
            log.debug('%s._open_file(fspec:%s)', self.__class__.__name__, fspec)
        else:
            fspec = self.filename
        if self.file_mode == FileOpenMode.READ:
            file_mode = 'r'
        elif self.file_mode == FileOpenMode.CREATE:
            file_mode = 'x'
        elif self.file_mode == FileOpenMode.WRITE:
            file_mode = 'w'
        elif self.file_mode == FileOpenMode.RENAME:
            file_mode = 'w'
            if isinstance(fspec, str) and os.path.isfile(self.filename):
                i = 1
                dest = '%s.%s' % (self.filename, i)
                while os.path.isfile(dest):
                    i += 1
                    dest = '%s.%s' % (self.filename, i)
                try:
                    os.rename(self.filename, dest)
                except Exception as exc:
                    raise StopError("File rename failed") from exc
        elif self.file_mode == FileOpenMode.APPEND:
            file_mode = 'a'
        charset = self.file_format_params.get('charset', 'ascii')
        errors = self.file_format_params.get('errors', 'strict')
        try:
            self.file = open(fspec, mode=file_mode, encoding=charset, errors=errors,
                                   closefd=self.filename.lower() not in self.SYSIO)
        except Exception as exc:
            raise StopError(f"Failed to open file [mode:{self.file_mode.name}]",
                            code = ErrorCode.ERROR) from exc
    def _close_file(self) -> None:
        """Close the input file if necessary"""
        if self.file:
            log.debug('%s._close_file(%s)', self.__class__.__name__, self.filename)
            self.file.close()
            self.file = None
    def _open_pipe(self) -> None:
        """Open the data pipe in CONNECT mode."""
        log.debug('%s._open_pipe()', self.__class__.__name__)
        session = self.pipe_chn.handler.open(self.pipe_address, self.data_pipe,
                                             self.pipe_socket, self.pipe_format)
        session.charset = self.pipe_format_params.get('charset', 'ascii')
        session.errors = self.pipe_format_params.get('errors', 'strict')
    def _on_accept_client(self, handler: BaseFBDPHandler, session: Session,
                          data_pipe: str, pipe_stream: PipeSocket, data_format: str) -> int:
        """SERVER callback. Validates and processes client connection request."""
        log.debug('%s._on_accept_client(%s,%s,%s)', self.__class__.__name__, data_pipe,
                  pipe_stream, data_format)
        if data_pipe != self.data_pipe:
            raise StopError(f"Unknown data pipe '{data_pipe}'",
                            code = ErrorCode.PIPE_ENDPOINT_UNAVAILABLE)
        elif pipe_stream != self.pipe_socket:
            raise StopError(f"'{pipe_stream.name}' stream not available",
                            code = ErrorCode.PIPE_ENDPOINT_UNAVAILABLE)
        mime = MIMEOption('data_format', '')
        try:
            mime.set_value(data_format)
        except:
            StopError("Only MIME data formats supported",
                      code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        session.output_mime_type = mime.mime_type
        if session.output_mime_type != 'text/plain':
            raise StopError("Only 'text/plain' format supported",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        session.output_format_params = dict(mime.mime_params)
        session.charset = session.output_format_params.get('charset', 'ascii')
        session.errors = session.output_format_params.get('errors', 'strict')
        # Ready to open the file
        self._open_file()
        return session.batch_size
    def _on_batch_start(self, handler: BaseFBDPHandler, session: Session) -> None:
        """PRODUCER callback. Sends a batch of DATA messages, each containing a line of text
from the input file."""
        log.debug('%s._on_batch_start()', self.__class__.__name__)
        if self.file is None:
            self._open_file()
        line = None
        while session.transmit > 0:
            try:
                line: str = self.file.readline()
            except Exception as exc:
                handler.send_close(session, ErrorCode.INVALID_DATA, exc=exc)
                return
            log.debug("Transmit[%s]:%s", session.transmit, line.rstrip('\n'))
            if line:
                msg = handler.protocol.create_message_for(MsgType.DATA)
                try:
                    msg.data_frame = line.encode(encoding=session.charset, errors=session.errors)
                except Exception as exc:
                    handler.send_close(session, ErrorCode.INVALID_DATA, exc=exc)
                    return
                else:
                    session.transmit -= 1
                    handler.send(msg, session)
            else:
                handler.send_close(session, ErrorCode.OK)
                return
        if self.pipe_mode == SocketMode.BIND and session.transmit == 0:
            handler.send_ready(session, handler.batch_size)
    def _on_accept_data(self, handler: BaseFBDPHandler, session: Session,
                        data: bytes) -> t.Optional[int]:
        """CONSUMER callback that writes data to the output file."""
        log.debug('%s._on_accept_data(%s)', self.__class__.__name__, data)
        if self.file is None:
            self._open_file()
        try:
            self.file.write(data.decode(encoding=session.charset, errors=session.errors))
        except UnicodeError:
            return ErrorCode.INVALID_DATA
        except Exception:
            log.exception("Unexpected error while processing data from pipe")
            return ErrorCode.INTERNAL_ERROR
    def _deferred_shutdown(self, *args) -> None:
        """Shut down the service on idle. This is a workaround to problem found in ZMQ,
where pending messages are not delivered via TCP transport to the peer before context in
shut down despite infinite linger.
"""
        self.stop_event.set()
    def on_pipe_closed(self, handler: BaseFBDPHandler, session: Session,
                       msg: Message) -> None:
        """General callback that logs info(OK) or error, and closes the input file."""
        log.debug('%s.on_pipe_closed[%s:%s]', self.__class__.__name__, session, self.stop_on_close)
        self._close_file()
        if self.stop_on_close:
            self.mngr.defer(self._deferred_shutdown)
    def initialize(self, svc: BaseService):
        super().initialize(svc)
        self.pipe_chn = DealerChannel(b'%s-out' % self.instance_id.hex().encode('ascii'),
                                      sock_opts=self.get('sock_opts', None))
        self.mngr.add(self.pipe_chn)
    def configure(self, svc: BaseService, config: TextIOConfig) -> None:
        """Service configuration."""
        config.validate() # Fail early
        #
        self.stop_on_close = config.stop_on_close.value
        self.data_pipe = config.data_pipe.value
        self.pipe_mode = config.pipe_mode.value
        self.pipe_address = config.pipe_address.value
        self.pipe_format = config.pipe_format.value
        self.pipe_mime_format = config.pipe_format.mime_type
        self.pipe_format_params = dict(config.pipe_format.mime_params)
        self.filename = config.file.value
        self.file_mode = config.file_mode.value
        self.is_reader = self.file_mode in [FileOpenMode.READ, FileOpenMode.APPEND]
        self.file_format = config.file_format.value
        self.file_mime_type = config.file_format.mime_type
        self.file_format_params = dict(config.file_format.mime_params)
        #
        if config.pipe_mode.value == SocketMode.BIND:
            if self.is_reader:
                # Readers BIND to OUTPUT
                self.pipe_socket = PipeSocket.OUTPUT
                self.facilities = ServiceFacilities.OUTPUT_AS_SERVER
            else:
                # Writers BIND to INPUT
                self.pipe_socket = PipeSocket.INPUT
                self.facilities = ServiceFacilities.INPUT_AS_SERVER
            handler = PipeServerHandler(config.pipe_batch_size.value)
            handler.on_accept_client = self._on_accept_client
        else:
            if self.is_reader:
                # Readers CONNECT to INPUT
                self.pipe_socket = PipeSocket.INPUT
                self.facilities = ServiceFacilities.OUTPUT_AS_CLIENT
            else:
                # Writers CONNECT to OUTPUT
                self.pipe_socket = PipeSocket.OUTPUT
                self.facilities = ServiceFacilities.INPUT_AS_CLIENT
            handler = PipeClientHandler(config.pipe_batch_size.value)
        handler.on_batch_start = self._on_batch_start
        handler.on_accept_data = self._on_accept_data
        handler.on_pipe_closed = self.on_pipe_closed
        self.pipe_chn.set_handler(handler)
        if config.pipe_mode.value == SocketMode.BIND:
            log.info("Pipe BIND [%s:%s]", self.pipe_socket.name, self.data_pipe)
            self.pipe_chn.bind(self.pipe_address)
        else:
            self.mngr.defer(self._open_pipe)
    def validate(self) -> None:
        """"""
        if self.file_mime_type != 'text/plain':
            raise StopError("Only 'text/plain' MIME type supported")
    def finalize(self, svc: BaseService) -> None:
        """Service finalization.

Base implementation only calls shutdown() on service ChannelManager. If `shutdown_linger`
is not defined, uses linger 1 for forced shutdown.
"""
        self.pipe_chn.handler.close()
        super().finalize(svc)
        self._close_file()
