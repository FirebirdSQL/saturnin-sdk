
TEXT I/O microservice
=====================

Metadata
--------

name:
  saturnin.example.textio

description:
  Sample TEXTIO microservice

classification:
  example/micro

OID:
  None

OID name:
  None

UUID:
  7fe7a9fe-d60b-11e9-ad9f-5404a6a1fd6e

facilities:
  None

API:
  None

Description
-----------

This example demostrates Butler micro service that uses a data pipe (using FBDP_ protocol).
It transfers text between a file and a data pipe.

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

.. note::

   This sample service is fundamentally different from the `saturnin.text.reader` and
   `saturnin.text.writer` services in that it can act as a provider or consumer as configured.
   Saturnin CORE services `saturnin.text.reader`, `saturnin.text.writer` and `saturnin.text.linefilter`
   are good examples of micro services that use data pipes in three different scenarios:
   `data producer`, `data consumer` and `data filter`.

.. important::

   The MIME type for the transmitted data must be defined in an appropriate way that
   guarantees the correct processing of the data by the receiving service.


Configuration
-------------

agent:
  `.UUID`: Agent identification (service UUID)

logging_id:
  `str`: Logging ID for this component instance, see `Context-based logging`_ for details.

stop_on_close:
  `bool`: Stop the service when pipe is closed. DEFAULT `True`.

data_pipe:
  `str`: Data Pipe Identification (name). REQUIRED option.

pipe_address:
  `~firebird.base.types.ZMQAddress`: Data Pipe endpoint address. REQUIRED option.

pipe_mode:
  `~saturnin.base.types.SocketMode`: Data Pipe Mode (bind/connect). REQUIRED option.

pipe_format:
  `~firebird.base.types.MIME`: Pipe data format specification. REQUIRED for CONNECT pipe mode.
  DEFAULT `text/plain;charset=utf-8`.

pipe_batch_size:
  `int`: Data batch size. See FBDP_ documentation for details. DEFAULT 50.

filename:
  `str`: File specification (path to file). REQUIRED option.

file_mode:
  `~saturnin.base.types.FileOpenMode`: File I/O mode.

file_format:
  `~firebird.base.types.MIME`: File data format specification. REQUIRED option.
  DEFAULT `text/plain;charset=utf-8`


.. important::

   STDOUT, STDERR and STDIN support only READ and WRITE modes.

.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html


