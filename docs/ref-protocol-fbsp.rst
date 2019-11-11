==========================
saturnin.sdk.protocol.fbsp
==========================

.. module:: saturnin.sdk.protocol.fbsp
   :synopsis: Reference implementation of Firebird Butler Service Protocol
      
.. automodule:: saturnin.sdk.protocol.fbsp
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
.. autodata:: ERROR_TYPE_MASK

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

Functions
=========

.. autofunction:: validate_vendor_id_pb
.. autofunction:: validate_platform_id_pb
.. autofunction:: validate_agent_id_pb
.. autofunction:: validate_peer_id_pb
.. autofunction:: validate_error_desc_pb
.. autofunction:: validate_interface_spec_pb
.. autofunction:: validate_cancel_pb
.. autofunction:: validate_hello_pb
.. autofunction:: validate_welcome_pb
.. autofunction:: bb2h
.. autofunction:: uid2uuid
.. autofunction:: exception_for
.. autofunction:: note_exception

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

HandshakeMessage
----------------
.. autoclass:: HandshakeMessage
   :member-order: groupwise

HelloMessage
------------
.. autoclass:: HelloMessage
   :member-order: groupwise

WelcomeMessage
--------------
.. autoclass:: WelcomeMessage
   :member-order: groupwise

NoopMessage
-----------
.. autoclass:: NoopMessage
   :member-order: groupwise

APIMessage
----------
.. autoclass:: APIMessage
   :members: interface_id, api_code, request_code
   :member-order: groupwise

RequestMessage
--------------
.. autoclass:: RequestMessage
   :member-order: groupwise

ReplyMessage
------------
.. autoclass:: ReplyMessage
   :member-order: groupwise

DataMessage
-----------
.. autoclass:: DataMessage
   :member-order: groupwise

CancelMessage
-------------
.. autoclass:: CancelMessage
   :member-order: groupwise

StateMessage
------------
.. autoclass:: StateMessage
   :members: state
   :member-order: groupwise

CloseMessage
------------
.. autoclass:: CloseMessage
   :member-order: groupwise

ErrorMessage
------------
.. autoclass:: ErrorMessage
   :members: add_error, error_code, relates_to
   :member-order: groupwise

Session
-------
.. autoclass:: Session
   :members:
   :member-order: groupwise

Protocol
--------
.. autoclass:: Protocol
   :members:
   :member-order: groupwise

BaseFBSPHandler
---------------
.. autoclass:: BaseFBSPHandler
   :members:
   :member-order: groupwise

ServiceMessagelHandler
----------------------
.. autoclass:: ServiceMessagelHandler
   :members:
   :member-order: groupwise

ClientMessageHandler
--------------------
.. autoclass:: ClientMessageHandler
   :members:
   :member-order: groupwise

