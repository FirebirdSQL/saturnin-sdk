# SPDX-FileCopyrightText: 2023-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: saturnin
# FILE:           saturnin/sdk/commands/recipes.py
# DESCRIPTION:    Saturnin SDK recipe commands
# CREATED:        21.02.2023
#
# The contents of this file are subject to the MIT License
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#
# Copyright (c) 2021 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________
# pylint: disable=R0912, R0913, R0914, R0915

"""Saturnin SDK recipe commands

This module focuses on operations related to Saturnin recipes, primarily
the creation of standalone, Nuitka-compatible Python scripts. These scripts
bundle a specific recipe and its necessary service dependencies, allowing them
to be compiled into single-file executables or run as self-contained
applications.
"""

from __future__ import annotations

from configparser import ConfigParser, ExtendedInterpolation
from importlib.metadata import entry_points
from pathlib import Path
from typing import Annotated

import typer
from saturnin._scripts.completers import recipe_completer
from saturnin.base import SECTION_BUNDLE, SECTION_SERVICE
from saturnin.component.bundle import ServiceBundleConfig
from saturnin.component.controller import ServiceExecConfig
from saturnin.component.recipe import RecipeInfo, RecipeType, SaturninRecipe, recipe_registry
from saturnin.component.registry import ServiceInfo, service_registry
from saturnin.lib.console import console

app = typer.Typer(rich_markup_mode="rich", help="Saturnin recipes.")

HLP_RECIPE = "The name of the installed Saturnin recipe to use."
HLP_SECTION = """Optional name of the configuration section to use from the recipe file.
If not provided, defaults to 'bundle' for bundle-type recipes and 'service' for service-type recipes."""
HLP_OUTPUT = """Optional base path and name for the output files (script and configuration).
If not provided, it defaults to the original recipe's filename (e.g., `my_recipe`) in the current working directory, resulting in `my_recipe.py` and `my_recipe.cfg`. The script will be saved as `<output>.py` and the configuration as `<output>.cfg`."""

@app.command('standalone')
def create_standalone(recipe_name: Annotated[str, typer.Argument(..., help=HLP_RECIPE,
                                                                 autocompletion=recipe_completer)],
                      section: Annotated[str| None, typer.Option(help=HLP_SECTION)]=None,
                      output: Annotated[Path | None, typer.Option(help=HLP_OUTPUT)]=None):
    """Creates standalone runner (container) for recipe, suitable for compilation with Nuitka.

    This command generates a Python script (.py) that embeds the necessary
    service definitions and protobuf registrations for a given recipe. It also
    copies the recipe's configuration file (.cfg). The generated Python script
    is designed to be suitable for compilation into a single executable using
    Nuitka.

    The standalone runner will include only the services required by the specified
    recipe, making it a minimal, self-contained application.
    """
    recipe: RecipeInfo | None = recipe_registry.get(recipe_name)
    if recipe is None:
        console.print_error(f"Recipe '{recipe_name}' not installed")
        return
    #
    if output is None:
        output = Path.cwd() / recipe.filename.name
    proto_groups: list[str] = ['firebird.base.protobuf', 'firebird.butler.protobuf']
    svc_names: list[str] = []
    svc_api: list[str] = []
    svc_factory: list[str] = []
    svc_registration: list[str] = []
    proto_import: list[str] = []
    proto_registration: list[str] = []
    # protobuf
    for group in proto_groups:
        for entry in entry_points().get(group, []):
            module, item = entry.value.split(':')
            proto_import.append(f'from {module} import {item} as proto_{len(proto_import) + 1}')
            proto_registration.append(f'register_decriptor(proto_{len(proto_import)})')
    # services
    config: ConfigParser = ConfigParser(interpolation=ExtendedInterpolation())
    config.read(recipe.filename)
    recipe_config = SaturninRecipe()
    recipe_config.load_config(config)
    recipe_config.validate()
    #
    if recipe_config.recipe_type.value is RecipeType.BUNDLE:
        if section is None:
            section = SECTION_BUNDLE
        exe_import = 'from saturnin._scripts.bundlerun import main'
        description = 'Saturnin script to run bundle of services.'
        bundle_cfg: ServiceBundleConfig = ServiceBundleConfig(section)
        bundle_cfg.load_config(config)
        bundle_cfg.validate()
        for agent_config in bundle_cfg.agents.value:
            svc: ServiceInfo = service_registry[agent_config.agent.value]
            svc_names.append(svc.name)
            module, item = svc.descriptor.split(':')
            svc_api.append(f'from {module} import {item} as desc_{len(svc_api) + 1}')
            module, item = svc.factory.split(':')
            svc_factory.append(f'from {module} import {item}')
            svc_registration.append(
                f'service_registry.add(desc_{len(svc_api)}, {item}, "{svc.distribution}")'
            )
    else:
        if section is None:
            section = SECTION_SERVICE
        description = ('Saturnin script to run one service, either unmanaged in main thread, '
                       'or managed in separate thread.')
        exe_import = 'from saturnin._scripts.svcrun import main'
        svc_cfg: ServiceExecConfig = ServiceExecConfig(section)
        svc_cfg.load_config(config)
        svc_cfg.validate()
        svc: ServiceInfo = service_registry[svc_cfg.agent.value]
        svc_names.append(svc.name)
        module, item = svc.descriptor.split(':')
        svc_api.append(f'from {module} import {item} as desc_{len(svc_api) + 1}')
        module, item = svc.factory.split(':')
        svc_factory.append(f'from {module} import {item}')
        svc_registration.append(
            f'service_registry.add(desc_{len(svc_api)}, {item}, "{svc.distribution}")'
        )
    script = f'''
"""{description}

This is a standalone executable that can run only predefined services:

{',CRLF'.join(svc_names)}
"""

from __future__ import annotations

# Set SATURNIN_HOME to directory where this script is located
# It's important to do it here before saturnin.base.directory_scheme is initialized
import os

if 'SATURNIN_HOME' not in os.environ:
        os.environ['SATURNIN_HOME'] = os.path.dirname(__file__)

{exe_import}
from firebird.base.protobuf import register_decriptor
from saturnin.component.registry import service_registry

{'CRLF'.join(proto_import)}
{'CRLF'.join([item for sublist in zip(svc_api, svc_factory, strict=True) for item in sublist])}

{'CRLF'.join(proto_registration)}
service_registry.clear()
{'CRLF'.join(svc_registration)}

if __name__ == '__main__':
        main(__doc__, '{recipe.filename.name}')
'''
    #
    script = script.replace('CRLF', '\n')
    #
    script_file: Path = output.with_suffix('.py')
    script_file.write_text(script)
    cfg_file: Path = output.with_suffix('.cfg')
    cfg_file.write_text(recipe.filename.read_text())
    console.print("Standalone runner created.")
