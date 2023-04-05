
########
Examples
########

.. note::

   Examples are not distributed via PyPI. You can either download the ZIP package from
   `gihub releases`_ and unpack it into directory of your choice, or checkout the "examples"
   directory directly from SDK repository_.

   To register (example and your own) services and applications for use with Saturnin in
   "development" mode, use `saturnin install package -e .` from root directory of service
   package.

   For example to register `TextIO` sample service:

   1. CD to `examples/textio`
   2. Run `saturnin install package -e .`

|

.. toctree::
   :caption: Available examples:
   :maxdepth: 1

   svc-dummy
   svc-textio
   svc-roman
   app-print-file

.. _gihub releases: https://github.com/FirebirdSQL/saturnin-sdk/releases
.. _repository: https://github.com/FirebirdSQL/saturnin-sdk
