============
saturnin-sdk
============

This repository contains SDK for Saturnin, and example services and applications.

The `saturnin-sdk` package (released on PyPI) contains the SDK itself, without examples.

To work with the SDK, it's necessary to install and properly initialize the `saturnin`
(see `saturnin`_ documentation for details).

Examples are not distributed via PyPI. You can either download the ZIP package from
`gihub releases`_ and unpack it into directory of your choice, or checkout the "examples"
directory directly.

You may also checkout the whole `saturnin-sdk` repository, and install the SDK into your
Saturnin site directly using `saturnin install package -e .`.

To register (example and your own) services and application for use with Saturnin in
"development" mode, use `saturnin install package -e .` from root directory of service
package. For example to register `TextIO` sample service:

1. CD to `examples/textio`
2. Run `saturnin install package -e .`

.. important::

   Your services can't be registered without proper `pyproject.toml`.


.. _saturnin: https://saturnin.rtfd.io/
.. _gihub releases: https://github.com/FirebirdSQL/saturnin-sdk/releases
