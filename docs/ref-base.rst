=================
saturnin.sdk.base
=================

.. module:: saturnin.sdk.base
   :synopsis: Saturnin SDK messaging base
      
.. automodule:: saturnin.sdk.base
   :noindex:

Constants
=========

.. autodata:: INTERNAL_ROUTE
.. autodata:: RESUME_TIMEOUT

Types for annotations
=====================

.. autodata:: TSession
.. autodata:: TMessageHandler
.. autodata:: TMessageFactory
.. autodata:: TCancelSessionCallback
.. autodata:: TSockOpts


Loggers
=======

.. autodata:: log_chnmgr
.. autodata:: log_chn
.. autodata:: log_msghnd
.. autodata:: log_ssn

Functions
=========

.. autofunction:: peer_role
.. autofunction:: get_unique_key
.. autofunction:: msg_bytes

Classes
=======

ChannelManager
--------------
.. autoclass:: ChannelManager
   :members:
   :member-order: groupwise

Message
-------
.. autoclass:: Message
   :members:
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

Channel
-------
.. autoclass:: Channel
   :members:
   :member-order: groupwise

MessageHandler
--------------
.. autoclass:: MessageHandler
   :members:
   :private-members:
   :member-order: groupwise

Channels for individual ZMQ socket types
========================================

DealerChannel
-------------
.. autoclass:: DealerChannel
   :members:
   :member-order: groupwise

RouterChannel
-------------
.. autoclass:: RouterChannel
   :members:
   :member-order: groupwise

PushChannel
-----------
.. autoclass:: PushChannel
   :members:
   :member-order: groupwise

PullChannel
-----------
.. autoclass:: PullChannel
   :members:
   :member-order: groupwise

PubChannel
----------
.. autoclass:: PubChannel
   :members:
   :member-order: groupwise

SubChannel
----------
.. autoclass:: SubChannel
   :members:
   :member-order: groupwise

XPubChannel
-----------
.. autoclass:: XPubChannel
   :members:
   :member-order: groupwise

XSubChannel
-----------
.. autoclass:: XSubChannel
   :members:
   :member-order: groupwise

PairChannel
-----------
.. autoclass:: PairChannel
   :members:
   :member-order: groupwise

