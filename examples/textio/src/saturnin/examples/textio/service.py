# SPDX-FileCopyrightText: 2019-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           textio/service.py
# DESCRIPTION:    Sample TEXTIO microservice
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

"""Saturnin SDK examples - Sample TEXTIO microservice

This microservice transfers text between a file and a Data Pipe.

It can:

- operate in both ways, i.e. store data from pipe input to file, or read from file to pipe
  output.
- work as data pipe server (bind) or client (connect)
- operate on regular files or stdin, stdout and stderr
- convert text between character sets (using MIME text/plain `charset` and `error` parameters)
- open output files in create (fails if file exists), write, append or rename (renames
  existing files).

The transfer unit is single text line, which is quite simple but very ineffective.
For real use it would be better to transfer text in larger chunks (see Saturnin text reader
and writer microservices).
"""

from __future__ import annotations

import os
from typing import IO, cast

from saturnin.base import (
    MIME,
    Channel,
    DealerChannel,
    Direction,
    Message,
    Outcome,
    PipeSocket,
    Session,
    SocketMode,
    StopError,
    ZMQAddress,
)
from saturnin.component.micro import MicroService
from saturnin.protocol.fbdp import ErrorCode, FBDPClient, FBDPMessage, FBDPServer, FBDPSession

from firebird.base.logging import get_logger

from .api import FileOpenMode, TextIOConfig

PIPE_CHN = 'pipe'

class _Session(FBDPSession):
    """Extended FBDP session for the TEXTIO microservice.

    This session stores the character set (`charset`) and error handling strategy (`errors`)
    to be used for text encoding and decoding during data transfer.
    """
    def __init__(self):
        super().__init__()
        self.charset: str = None
        self.errors: str = None
        # This overrides FBDPSession.data_format (str | None) to allow storing MIME object
        self.data_format: MIME | str | None = None

class MicroTextIOSvc(MicroService):
    """Implementation of TEXTIO microservice."""
    SYSIO = ('stdin', 'stdout', 'stderr')
    pipe_socket: PipeSocket | None = None
    file: IO | None = None
    def _open_file(self):
        """Opens the configured file based on `filename`, `file_mode`, and `file_format`.

        Handles special filenames like 'stdin', 'stdout', 'stderr', and file renaming
        if `file_mode` is `FileOpenMode.RENAME` and the file exists.
        Sets `self.file` to the opened file stream.
        """
        self._close_file()
        if self.filename.lower() in self.SYSIO:
            fspec = self.SYSIO.index(self.filename.lower())
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
                dest = f'{self.filename}.{i}'
                while os.path.isfile(dest):
                    i += 1
                    dest = f'{self.filename}.{i}'
                try:
                    os.rename(self.filename, dest)
                except Exception as exc:
                    raise StopError("File rename failed") from exc
        elif self.file_mode == FileOpenMode.APPEND:
            file_mode = 'a'
        charset = self.file_format.params.get('charset', 'ascii')
        errors = self.file_format.params.get('errors', 'strict')
        try:
            self.file = open(fspec, mode=file_mode, encoding=charset, errors=errors,
                             closefd=self.filename.lower() not in self.SYSIO)
        except Exception as exc:
            raise StopError(f"Failed to open file [mode:{self.file_mode.name}]",
                            code = ErrorCode.ERROR) from exc
    def _close_file(self) -> None:
        """Closes the currently open file stream (`self.file`) if it exists.
        """
        if self.file:
            self.file.close()
            self.file = None
    def initialize(self, config: TextIOConfig) -> None:
        """Initializes the service, verifies configuration, and sets up communication channels.

        Reads settings from `TextIOConfig`, determines if the service acts as a reader or writer,
        configures the FBDP protocol (client or server based on `pipe_mode`), and creates
        the necessary ZMQ channel for the data pipe.
        """
        super().initialize(config)
        get_logger(self).info("Initialization...")
        self.log_context = 'main'
        # Configuration
        self.stop_on_close = config.stop_on_close.value
        get_logger(self).debug('{stop_on_close=}', stop_on_close=self.stop_on_close)
        self.data_pipe: str = config.data_pipe.value
        get_logger(self).debug('{data_pipe=}', data_pipe=self.data_pipe)
        self.pipe_mode: SocketMode = config.pipe_mode.value
        get_logger(self).debug('{pipe_mode=}', pipe_mode=self.pipe_mode)
        self.pipe_address: ZMQAddress = config.pipe_address.value
        get_logger(self).debug('{pipe_address=}', pipe_address=self.pipe_address)
        self.pipe_format: MIME = config.pipe_format.value
        get_logger(self).debug('{pipe_format=}', pipe_format=self.pipe_format)
        self.pipe_batch_size: int = config.pipe_batch_size.value
        get_logger(self).debug('{pipe_batch_size=}', pipe_batch_size=self.pipe_batch_size)
        self.filename: str = config.filename.value
        get_logger(self).debug('{filename=}', filename=self.filename)
        self.file_mode: FileOpenMode = config.file_mode.value
        get_logger(self).debug('{file_mode=}', file_mode=self.file_mode)
        self.file_format: MIME = config.file_format.value
        get_logger(self).debug('{file_format=}', file_format=self.file_format)
        if self.file_format.mime_type != 'text/plain':
            raise StopError("Only 'text/plain' MIME type supported")
        #
        self.is_reader: bool = self.file_mode in (FileOpenMode.READ, FileOpenMode.APPEND)
        get_logger(self).debug('{is_reader=}', is_reader=self.is_reader)
        self.pipe_socket: PipeSocket = None
        if self.pipe_mode == SocketMode.BIND:
            if self.is_reader:
                # Readers BIND to OUTPUT
                self.pipe_socket = PipeSocket.OUTPUT
            else:
                # Writers BIND to INPUT
                self.pipe_socket = PipeSocket.INPUT
            protocol = FBDPServer(session_type=_Session)
            protocol.on_exception = self.handle_exception
            protocol.on_accept_client = self.handle_accept_client
            protocol.on_get_ready = self.handle_get_ready
            protocol.on_schedule_ready = self.handle_schedule_ready
            # We have an endpoint to bind
            self.endpoints[PIPE_CHN] = [self.pipe_address]
        else:
            if self.is_reader:
                # Readers CONNECT to INPUT
                self.pipe_socket = PipeSocket.INPUT
            else:
                # Writers CONNECT to OUTPUT
                self.pipe_socket = PipeSocket.OUTPUT
            protocol = FBDPClient(session_type=_Session)
            protocol.on_server_ready = self.handle_server_ready
        protocol.batch_size = self.pipe_batch_size
        protocol.on_pipe_closed = self.handle_pipe_closed
        # We assign event handlers unconditionally, but it's also possible to assign only
        # really used handlers
        protocol.on_accept_data = self.handle_accept_data
        protocol.on_produce_data = self.handle_produce_data
        protocol.on_data_confirmed = self.handle_data_confirmed
        get_logger(self).debug('{pipe_socket=}', pipe_socket=self.pipe_socket)
        # Example high water mark optimization
        if self.pipe_socket is PipeSocket.OUTPUT:
            rcvhwm = 5
            sndhwm = self.pipe_batch_size + 5
        else:
            rcvhwm = self.pipe_batch_size + 5
            sndhwm = 5
        self.file: IO = None
        # Create pipe channel
        chn: Channel = self.mngr.create_channel(DealerChannel, PIPE_CHN, protocol,
                                                wait_for=Direction.IN,
                                                sock_opts={'rcvhwm': rcvhwm,
                                                           'sndhwm': sndhwm,})
    def aquire_resources(self) -> None:
        """Aquire resources required by component (open files, connect to other services etc.).

        If configured as a data pipe client (`SocketMode.CONNECT`), this method connects
        to the pipe server, sends an OPEN request, and initializes session attributes.
        It then calls `_open_file()` to open the configured local file.
        """
        get_logger(self).info("Aquiring resources...")
        # Connect to the data pipe
        if self.pipe_mode == SocketMode.CONNECT:
            chn: Channel = self.mngr.channels[PIPE_CHN]
            session = chn.connect(self.pipe_address)
            # Type hint for session was added in previous response
            # OPEN the data pipe connection, this also fills session attributes
            cast(FBDPClient, chn.protocol).send_open(chn, session, self.data_pipe,
                                                     self.pipe_socket, self.file_format)
            # We work with MIME formats, so we'll convert the format specification to MIME
            session.data_format = MIME(session.data_format) # type: ignore[attr-defined]
            session.charset = session.data_format.params.get('charset', 'ascii')
            session.errors = session.data_format.params.get('errors', 'strict')
            self._open_file()
    def release_resources(self) -> None:
        """Release resources aquired by component (close files, disconnect from other services etc.)
        """
        get_logger(self).info("Releasing resources...")
        # Note: File closing is primarily handled by _close_file(), which is called
        # by handle_pipe_closed() or when the service stops.
        # This method focuses on closing active data pipe sessions.
        # CLOSE all active data pipe sessions
        chn: Channel = self.mngr.channels[PIPE_CHN]
        # send_close() will discard session, so we can't iterate over sessions.values() directly
        for session in list(chn.sessions.values()):
            # We have to report error here, because normal is to close pipes before
            # shutdown is commenced. Mind that service shutdown could be also caused by error!
            cast(FBDPServer, chn.protocol).send_close(chn, session, ErrorCode.ERROR)
    def start_activities(self) -> None:
        """Start normal component activities.

        Must raise an exception when start fails.
        """
        get_logger(self).info("Starting activities...")
    def stop_activities(self) -> None:
        """Stop component activities.
        """
        get_logger(self).info("Stopping activities...")
    # Type hint for session was added in previous response
    def handle_exception(self, channel: Channel, session: Session, msg: Message, exc: Exception) -> None:
        """Event handler called by FBDP protocol on an unhandled exception in a message handler.

        Sets the service outcome to `Outcome.ERROR` and stores the exception details.
        """
        self.outcome = Outcome.ERROR
        self.details = exc
    # FBDP server only
    def handle_accept_client(self, channel: Channel, session: FBDPSession) -> None:
        """Handler is executed when client connects to the data pipe via OPEN message.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The session attributes `data_pipe`, `pipe_socket`, `data_format` and `params`
        contain information sent by client, and the event handler validates the request.

        If request should be rejected, it raises the `StopError` exception with `code`
        attribute containing the `ErrorCode` to be returned in CLOSE message.
        """
        if session.pipe != self.data_pipe:
            raise StopError(f"Unknown data pipe '{session.pipe}'",
                            code = ErrorCode.PIPE_ENDPOINT_UNAVAILABLE)
        if session.socket != self.pipe_socket:
            raise StopError(f"'{session.socket}' socket not available",
                            code = ErrorCode.PIPE_ENDPOINT_UNAVAILABLE)
        # We work with MIME formats, so we'll convert the format specification to MIME
        session.data_format: MIME = MIME(session.data_format)
        if session.data_format.mime_type != 'text/plain':
            raise StopError("Only 'text/plain' format supported",
                            code = ErrorCode.DATA_FORMAT_NOT_SUPPORTED)
        session.charset = session.data_format.params.get('charset', 'ascii')
        session.errors = session.data_format.params.get('errors', 'strict')
        # Client reqeast is ok, we'll open the file we are configured to work with.
        self._open_file()
    def handle_get_ready(self, channel: Channel, session: FBDPSession) -> int:
        """Handler is executed to obtain the transmission batch size for the client.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        Returns:
           Number of messages that could be transmitted (batch size):
           * 0 = Not ready to transmit yet
           * n = Ready to transmit 1..<n> messages.
           * -1 = Ready to transmit 1..<protocol batch size> messages.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            In this example we are always ready and work with preconfigured batch size,
            so this handler always returns -1.
        """
        return -1
    def handle_schedule_ready(self, channel: Channel, session: FBDPSession) -> None:
        """The handler is executed in order to send the READY message to the client later.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            This handler should NEVER be called in this example, because we never return 0
            from `on_get_ready` event handler. So we raise an error uncoditionally here.
        """
        raise StopError("'on_schedule_ready' should never be called", code=ErrorCode.INTERNAL_ERROR)
    # FBDP client only
    def handle_server_ready(self, channel: Channel, session: FBDPSession, batch_size: int) -> int:
        """Handler is executed to negotiate the transmission batch size with server.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with server.
            batch_size: Max. batch size accepted by server. It's always greater than zero.

        Returns:
           Number of messages that could be transmitted (batch size):
           * 0 = Not ready to transmit yet
           * n = Ready to transmit 1..<n> messages.
           * -1 = Ready to transmit 1..<protocol batch size> messages.

        Important:
            The returned value will be used ONLY when it's smaller than `batch_size`.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            The default implementation for this handler provided by FBDP always returns -1,
            which is mostly desirable action if you work with preconfigured batch sizes.

            However, sometimes you want to do something else or special, so here is an example.
            The `batch_size` argument is provided as a hint that could be used for
            computation of our answer. As demostration, we raise an exception (to close
            the pipe) if value proposed by server is greater than 10000.
        """
        if batch_size > 10000:
            raise StopError("Batch size exceeds 10000", code=ErrorCode.ERROR)
        return -1
    # FBDP common
    def handle_accept_data(self, channel: Channel, session: FBDPSession, data: bytes) -> None:
        """Handler is executed for CONSUMER when DATA message is received for PIPE_INPUT.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            data: Data received from client.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            The ACK-REQUEST in received DATA message is handled automatically by protocol.

        Note:
            Exceptions are handled by protocol, but only StopError is checked for protocol
            ErrorCode. As we want to report INVALID_DATA properly, we have to convert
            UnicodeError into StopError.
        """
        try:
            self.file.write(data.decode(encoding=session.charset, errors=session.errors))
            self.file.flush()
        except UnicodeError as exc:
            raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
    def handle_produce_data(self, channel: Channel, session: FBDPSession, msg: FBDPMessage) -> None:
        """Handler is executed for PRODUCER when DATA message should be sent to PIPE_OUTPUT.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with client.
            msg: DATA message that will be sent to client.

        The event handler must store the data in `msg.data_frame` attribute. It may also
        set ACK-REQUEST flag and `type_data` attribute.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            To indicate end of data, raise StopError with ErrorCode.OK code.

        Note:
            Exceptions are handled by protocol, but only StopError is checked for protocol
            ErrorCode. As we want to report INVALID_DATA properly, we have to convert
            UnicodeError into StopError.
        """
        try:
            line: str = self.file.readline()
        except UnicodeError as exc:
            raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
        if line:
            try:
                msg.data_frame = line.encode(encoding=session.charset, errors=session.errors)
            except UnicodeError as exc:
                raise StopError("UnicodeError", code=ErrorCode.INVALID_DATA) from exc
        else:
            raise StopError('OK', code=ErrorCode.OK)
    def handle_data_confirmed(self, channel: Channel, session: FBDPSession, type_data: int) -> None:
        """Handler is executed for PRODUCER when ACK_REPLY on sent DATA is received.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with peer.
            type_data: Content of `type_data` field from received DATA message confirmation.

        The event handler may cancel the transmission by raising the `StopError` exception
        with `code` attribute containing the `ErrorCode` to be returned in CLOSE message.

        Note:
            This handler should NEVER be called in this example, because we never set
            ACK_REQ on DATA messages. So we raise an error uncoditionally here.
        """
        raise StopError("'on_data_confirmed' should never be called", code=ErrorCode.INTERNAL_ERROR)
    def handle_pipe_closed(self, channel: Channel, session: FBDPSession, msg: FBDPMessage,
                           exc: Exception | None=None) -> None:
        """Called when CLOSE message is received or sent.

        This handler ensures the associated local file (`self.file`) is closed.
        If an exception `exc` is provided (indicating an error leading to the pipe closure),
        it updates the service's outcome to `Outcome.ERROR`.
        If `stop_on_close` is configured, it signals the service to stop.

        Arguments:
            channel: Channel associated with data pipe.
            session: Session associated with peer.
            msg: Received/sent CLOSE message.
            exc: Exception that caused the error.
        """
        self._close_file()
        # FDBP converts exceptions raised in our event handler to CLOSE messages, so
        # here is the central place to handle errors in data pip processing.
        # Note problem in service execution outcome
        if exc is not None:
            self.outcome = Outcome.ERROR
            self.details = exc
        #
        if self.stop_on_close:
            self.stop.set()
