#########
Changelog
#########

Version 0.10.0
==============

- Minimal Python version raised to 3.11
- Type hints adjusted to Python 3.11 standards
- Improved documentation.
- Dependencies updated to saturnin == 0.10.0
- Minor bugfixes.

Version 0.9.0
=============

- Build system changed from setuptools to hatch
- Update dependency to saturnin >=0.9.0
- Package version is now defined in `saturnin.sdk.__about__.py` (`__version__`)

Version 0.8.0
=============

* Milestone 5.

  Saturnin SDK is an optional add-on package for Saturnin, that contains extensions
  related to development of Butler services for Saturnin. Currently it provides only
  one extension command for Saturnin console: `create standalone`.

  This command takes a Saturnin recipe and creates Python script that serves as
  standalone container to run services used by recipe. This script could be compiled
  by `Nuitka`_ Python compiler.

  .. note:: This script currently does not support Saturnin applications.

Version 0.7.0
=============

* Milestone 4.

Version 0.5.0
=============

* Milestone 3.

Version 0.4.0
=============

* Milestone 2.

Version 0.1.0
=============

Initial release.

.. _saturnin: https://pypi.org/project/firebird-lib/
.. _releases: https://github.com/FirebirdSQL/python3-driver/releases
.. _Dash: https://kapeli.com/dash
.. _Zeal: https://zealdocs.org/
.. _Nuitka: https://nuitka.net/
