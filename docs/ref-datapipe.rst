=====================
saturnin.sdk.datapipe
=====================

.. module:: saturnin.sdk.datapipe
   :synopsis: Butler Data Pipes

.. automodule:: saturnin.sdk.datapipe
   :noindex:

Constants
=========

.. autodata:: END_OF_DATA

Enums
=====

PipeState
---------
.. autoclass:: PipeState
   :members:

Types for annotations
=====================

.. autodata:: TOnPipeClosed
.. autodata:: TOnAcceptClient
.. autodata:: TOnServerReady
.. autodata:: TOnAcceptData
.. autodata:: TOnProduceData

Loggers
=======

.. autodata:: log

Classes
=======

DataPipe
--------
.. autoclass:: DataPipe
   :members:
   :member-order: groupwise

InputPipe
---------
.. autoclass:: InputPipe
   :members:
   :member-order: groupwise

OutputPipe
----------
.. autoclass:: OutputPipe
   :members:
   :member-order: groupwise
