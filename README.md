# saturnin-sdk

[![PyPI - Version](https://img.shields.io/pypi/v/saturnin-sdk.svg)](https://pypi.org/project/saturnin-sdk)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/saturnin-sdk.svg)](https://pypi.org/project/saturnin-sdk)
[![Hatch project](https://img.shields.io/badge/%F0%9F%A5%9A-Hatch-4051b5.svg)](https://github.com/pypa/hatch)

This repository contains SDK for Saturnin, and example services and applications.

-----

**Table of Contents**

- [License](#license)
- [Installation](#installation)
- [Documentation](#documentation)

## License

`saturnin` and `saturnin-sdk` are distributed under the terms of the [MIT](https://spdx.org/licenses/MIT.html) license.

## Installation

The `saturnin-sdk` package (released on PyPI) contains the SDK itself, without examples.

To work with the SDK, it's necessary to install and properly initialize the `saturnin`
(see [Saturnin](https://saturnin.rtfd.io/) documentation for details).

Examples are not distributed via PyPI. You can either download the ZIP package from
[gihub releases](https://github.com/FirebirdSQL/saturnin-sdk/releases) and unpack it into
directory of your choice, or checkout the "examples" directory directly.

You may also checkout the whole `saturnin-sdk` repository, and install the SDK into your
Saturnin site directly using:

```console
saturnin install package -e .
```

To register (example and your own) services and application for use with Saturnin in
"development" mode, use `saturnin install package -e .` from root directory of service
package. For example to register `TextIO` sample service:

1. CD to `examples/textio`
2. Run `saturnin install package -e .`

## Documentation

Documentation related to Saturnin:

- [Firebird Butler](https://firebird-butler.rtfd.io/)
- [Saturnin](https://saturnin.rtfd.io/)
- [Saturnin CORE](https://saturnin-core.rtfd.io/) services
- [Saturnin SDK](https://saturnin-sdk.rtfd.io/)
