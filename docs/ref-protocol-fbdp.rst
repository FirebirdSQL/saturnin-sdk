==========================
saturnin.sdk.protocol.fbdp
==========================

.. module:: saturnin.sdk.protocol.fbdp
   :synopsis: Reference implementation of Firebird Butler Data Pipe Protocol
      
.. automodule:: saturnin.sdk.protocol.fbdp
   :noindex:

Constants
=========

.. autodata:: PROTOCOL_OID
.. autodata:: PROTOCOL_UID
.. autodata:: PROTOCOL_REVISION
.. autodata:: HEADER_FMT_FULL
.. autodata:: HEADER_FMT
.. autodata:: FOURCC
.. autodata:: VERSION_MASK
.. autodata:: DATA_BATCH_SIZE
.. autodata:: READY_PROBE_INTERVAL
.. autodata:: READY_PROBE_COUNT

Types for annotations
=====================

.. autodata:: TPipeHandler
.. autodata:: TPipeClientHandler
.. autodata:: TPipeServerHandler
.. autodata:: TOnPipeClosed
.. autodata:: TOnBatchStart
.. autodata:: TOnDataConfirmed
.. autodata:: TOnAcceptData
.. autodata:: TOnAcceptClient
.. autodata:: TOnBatchEnd
.. autodata:: TOnServerReady

Enums and flags
===============

MsgType
-------
.. autoclass:: MsgType
   :members:

MsgFlag
-------
.. autoclass:: MsgFlag
   :members:

ErrorCode
---------
.. autoclass:: ErrorCode
   :members:

Loggers
=======

.. autodata:: log

Classes
=======

Message
-------
.. autoclass:: Message
   :members:
   :inherited-members:
   :member-order: groupwise

Session
-------
.. autoclass:: Session
   :members:
   :member-order: groupwise

ServerSession
-------------
.. autoclass:: ServerSession
   :members:
   :member-order: groupwise

Protocol
--------
.. autoclass:: Protocol
   :members:
   :member-order: groupwise

BaseFBDPHandler
---------------
.. autoclass:: BaseFBDPHandler
   :members:
   :member-order: groupwise

PipeServerHandler
-----------------
.. autoclass:: PipeServerHandler
   :members:
   :member-order: groupwise

PipeClientHandler
-----------------
.. autoclass:: PipeClientHandler
   :members:
   :member-order: groupwise
