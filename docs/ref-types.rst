==================
saturnin.sdk.types
==================

.. module:: saturnin.sdk.types
   :synopsis: Saturnin SDK data types

.. automodule:: saturnin.sdk.types
   :noindex:

Types for annotations
=====================

.. autodata:: TStringList
.. autodata:: TSupplement
.. autodata:: Token
.. autodata:: RoutingID

Exceptions
==========

.. autoexception:: SaturninError
   :no-inherited-members:

.. autoexception:: InvalidMessageError
   :no-inherited-members:

.. autoexception:: ChannelError
   :no-inherited-members:

.. autoexception:: ServiceError
   :no-inherited-members:

.. autoexception:: ClientError
   :no-inherited-members:

.. autoexception:: StopError
   :no-inherited-members:


Enums and flags
===============

Enum
----
.. autoclass:: Enum

   .. automethod:: auto
   .. automethod:: get_member_map
   .. automethod:: get_value_map 

Flag
----
.. autoclass:: Flag
   :members:
   
Origin
------
.. autoclass:: Origin
   :members:

SocketMode
----------
.. autoclass:: SocketMode
   :members:

Direction
---------
.. autoclass:: Direction
   :members:

DependencyType
--------------
.. autoclass:: DependencyType
   :members:

ExecutionMode
-------------
.. autoclass:: ExecutionMode
   :members:

AddressDomain
-------------
.. autoclass:: AddressDomain
   :members:

TransportProtocol
-----------------
.. autoclass:: TransportProtocol
   :members:

SocketType
----------
.. autoclass:: SocketType
   :members:

SocketUse
---------
.. autoclass:: SocketUse
   :members:

ServiceType
-----------
.. autoclass:: ServiceType
   :members:

ServiceFacilities
-----------------
.. autoclass:: ServiceFacilities
   :members:

ServiceTestType
---------------
.. autoclass:: ServiceTestType
   :members:

State
-----
.. autoclass:: State
   :members:

PipeSocket
----------
.. autoclass:: PipeSocket
   :members:

Data classes
============

Distinct
--------
.. autoclass:: Distinct
   :members:

InterfaceDescriptor
-------------------
.. autoclass:: InterfaceDescriptor
   :members:

AgentDescriptor
---------------
.. autoclass:: AgentDescriptor
   :members:

PeerDescriptor
--------------
.. autoclass:: PeerDescriptor
   :members:

ServiceDescriptor
-----------------
.. autoclass:: ServiceDescriptor
   :members:

Classes
=======

ZMQAddress
----------
.. autoclass:: ZMQAddress
   :members:

LateBindingProperty
-------------------
.. autoclass:: LateBindingProperty
   :members:

