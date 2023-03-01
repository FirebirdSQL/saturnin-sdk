============
saturnin-sdk
============

This repository contains SDK for Saturnin, and example services.

The `saturnin-sdk` package (released on PyPI) contains the SDK itself, without examples.

To work with the SDK, it's necessary to properly initialize the `saturnin` deployment
(see documentation for `saturnin`).

Examples are not distributed via PyPI. You can either download the ZIP package from
`gihub releases`_ and unpack it into directory of your choice, or checkout the "examples"
directory directly.

You may also checkout the whole `saturnin-sdk` repository, and install the SDK into your
Saturnin site directly using `saturnin install -e .`.

To register (example and your own) services for use with Saturnin in "development" mode,
use `saturnin install -e .` from root directory of service package. For example to register
`TextIO` sample service:

1. CD to `examples/txtio`
2. Run `saturnin install -e .`

.. important::

   Your services can't be registered without proper `pyproject.toml`.


.. _gihub releases: https://github.com/FirebirdSQL/saturnin-sdk/releases
