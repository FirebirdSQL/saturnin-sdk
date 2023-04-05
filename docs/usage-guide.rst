
===========
Usage Guide
===========

Extensions for Saturnin console
===============================

Command "create standalone"
---------------------------

Saturnin containers in which services and applications are run use the component registry
to load the respective components according to the specified recipe. Because Saturnin works
with dynamic component registration and loading, recipes and containers cannot be separated
from a particular Saturnin environment. The `create standalone` command enables just such
a separation.

Based on the specified recipe, this command generates a Python script that serves as
a container that directly imports the necessary components. This script still needs to be
passed the appropriate recipe as a parameter (as when starting the container), but it is
no longer dependent on dynamically importing the required components, and can therefore
be compiled by the Nuitka_ Python compiler.

Although this script can be run directly as a replacement for running the appropriate
container, the main purpose of this command is to enable compilation to native code.
The resulting executable contains all dependencies and can therefore be distributed
independently, **without the need to install Python and Saturnin on the target system**.

Alternatively, the translated container can be used directly within the Saturnin
installation to speed up / optimize selected recipes, as the recipe can specify an
`executor` (container). Even multiple recipes can use the same compiled container. However,
the condition for running such a recipe is that it refers only to the components for which
the standalone container was generated.

The usage of the create standalone command is as follows::

 create standalone [OPTIONS] RECIPE_NAME

 Creates standalone runner (container) for recipe, suitable for compilation with Nuitka.

 ╭─ Arguments ───────────────────────────────────────────────────────────────────────────╮
 │ *    recipe_name      TEXT  Recipe name                                               │
 │                             [default: None]                                           │
 │                             [required]                                                │
 ╰───────────────────────────────────────────────────────────────────────────────────────╯
 ╭─ Options ─────────────────────────────────────────────────────────────────────────────╮
 │ --section        TEXT  Configuration section name                                     │
 │                        [default: None]                                                │
 │ --output         PATH  Output file                                                    │
 │                        [default: None]                                                │
 ╰───────────────────────────────────────────────────────────────────────────────────────╯

.. important:: This command currently does not support recipes that use Saturnin applications.

.. _setuptools: https://pypi.org/project/setuptools/
.. _ctypes: http://docs.python.org/library/ctypes.html
.. _PYPI: https://pypi.org/
.. _pip: https://pypi.org/project/pip/
.. _pipx: https://pypa.github.io/pipx/
.. _firebird-base: https://firebird-base.rtfd.io
.. _firebird-driver: https://pypi.org/project/firebird-driver/
.. _introduction to Firebird Butler: https://firebird-butler.readthedocs.io/en/latest/introduction.html
.. _saturnin-core: https://github.com/FirebirdSQL/saturnin-core
.. _Saturnin CORE: https://saturnin-core.rtfd.io/
.. _Saturnin SDK: https://saturnin-sdk.rtfd.io/
.. _saturnin-sdk: https://github.com/FirebirdSQL/saturnin-sdk
.. _FBSP: https://firebird-butler.readthedocs.io/en/latest/rfc/4/FBSP.html
.. _FBDP: https://firebird-butler.readthedocs.io/en/latest/rfc/9/FBDP.html
.. _Firebird Butler services: https://firebird-butler.readthedocs.io/en/latest/rfc/3/FBSD.html
.. _firebird-uuid: https://github.com/FirebirdSQL/firebird-uuid
.. _Nuitka: https://nuitka.net/
