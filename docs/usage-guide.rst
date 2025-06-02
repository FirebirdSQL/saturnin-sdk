
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
a separation by generating a Python script and its associated configuration file.

Based on the specified recipe, this command generates a Python script that serves as
a container, directly importing only the necessary service components and protobuf
definitions required by that recipe. Alongside the script, it also copies the recipe's
configuration file.

The generated Python script is hardcoded to load its configuration from a file
named identically to the **original recipe's filename**. For example, if you generate
a standalone script from `my_original_recipe.cfg`, the generated Python script will
expect to find and load `my_original_recipe.cfg`.

The command creates two files:
  - `<output_base_name>.py`: The standalone Python script.
  - `<output_base_name>.cfg`: A copy of the original recipe's configuration.

If the `--output` option is used to specify an `<output_base_name>` that differs
from the original recipe's filename stem, you will need to rename the generated
`<output_base_name>.cfg` to match the original recipe's filename for the script to use it,
or ensure a configuration file with the original recipe's name is present.

This generated script is no longer dependent on dynamic component importing from a full
Saturnin environment and can therefore be compiled by the Nuitka_ Python compiler.

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

 create standalone [OPTIONS] RECIPE_NAME [--section TEXT] [--output PATH]

 Creates standalone runner (container) for recipe, suitable for compilation with Nuitka.

 ╭─ Arguments ───────────────────────────────────────────────────────────────────────────╮
 │ *  RECIPE_NAME      TEXT  The name of the installed Saturnin recipe to use.           │
 │                           (required)                                                  │
 ╰───────────────────────────────────────────────────────────────────────────────────────╯
 ╭─ Options ─────────────────────────────────────────────────────────────────────────────╮
 │ --section        TEXT  Optional name of the configuration section to use from the     │
 │                        recipe file.                                                   │
 │                        If not provided, defaults to 'bundle' for bundle-type recipes  │
 │                        and 'service' for service-type recipes.                        │
 │                        [default: None]                                                │
 │ --output         PATH  Optional base path and name for the output files (script and   │
 │                        configuration).                                                │
 │                        If not provided, it defaults to the original recipe's filename │
 │                        (e.g., `my_recipe`) in the current working directory,          │
 │                        resulting in `my_recipe.py` and `my_recipe.cfg`.               │
 │                        The script will be saved as `<output>.py` and the              │
 │                        configuration as `<output>.cfg`.                               │
 │                        [default: None]                                                │
 ╰───────────────────────────────────────────────────────────────────────────────────────╯

.. note::

   The generated script internally uses the filename of the original recipe (e.g., `original_recipe.cfg`)
   to load its configuration. If you use the `--output` option to specify a different name (e.g., `standalone_app`),
   the command will create `standalone_app.py` and `standalone_app.cfg`. You must then ensure
   that either `standalone_app.cfg` is renamed to `original_recipe.cfg`, or a file named
   `original_recipe.cfg` (with the correct content) is available in the directory where
   `standalone_app.py` is run.

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
