
DUMMY microservice
==================

Metadata
--------

name:
  saturnin.micro.dummy

description:
  Test dummy microservice

classification:
  test/dummy

OID:
  1.3.6.1.4.1.53446.1.2.0.3.0

OID name:
  iso.org.dod.internet.private.enterprise.firebird.butler.platform.saturnin.micro.dummy

UUID:
  94e3b9e2-5acf-528b-8922-f7d1ccd39cdd

facilities:
  None

API:
  None

Description
-----------

This example demostrates basics of Butler micro services mechanics.

This microservice does nothing, and is intended for testing of service management machinery.

It's possible to configure the service to fail (raise an exception) during `initialize()`,
`aquire_resources()`, `release_resources()`, `start_activities()` or `stop_activities()`.

The service can run indefinitely or stop after a specified delay.

Configuration
-------------

agent:
  `.UUID`: Agent identification (service UUID)

logging_id:
  `str`: Logging ID for this component instance, see `Context-based logging`_ for details.

fail_on:
  `FailOn`: Stage when dummy should raise an exception. Accepted values are:
   - NEVER
   - INIT
   - RESOURCE_AQUISITION
   - RESOURCE_RELEASE
   - ACTIVITY_START
   - ACTIVITY_STOP

stop_after:
  `int`: Stop service after specified number of ms

.. _Context-based logging: https://firebird-base.readthedocs.io/en/latest/logging.html
