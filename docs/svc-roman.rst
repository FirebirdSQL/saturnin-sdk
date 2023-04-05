
ROMAN service
=============

Metadata
--------

name:
  saturnin.example.roman

description:
  Sample ROMAN service

classification:
  example/service

OID:
  None

OID name:
  None

UUID:
  413f76e8-4662-11e9-aa0d-5404a6a1fd6e

facilities:
  None

API:
  d0e35134-44af-11e9-b5b8-5404a6a1fd6e

Description
-----------

This example demostrates Butler service API definition and handling of API requests.

The service returns text data frames with arabic numbers replaced with Roman numbers.

Supported requests:

ROMAN (1):
  REPLY with altered REQUEST data frames.

Configuration
-------------

agent:
  `.UUID`: Agent identification (service UUID)

logging_id:
  `str`: Logging ID for this component instance, see `Context-based logging`_ for details.

endpoints:
  `List[ZMQAddress]`: List of service endpoints. REQUIRED options.


.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
