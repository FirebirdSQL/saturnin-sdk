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


"""

from __future__ import annotations
from typing import List
from pathlib import Path
from importlib.metadata import entry_points
from configparser import ConfigParser, ExtendedInterpolation
import typer
from saturnin.base import SECTION_BUNDLE, SECTION_SERVICE
from saturnin.component.recipe import (recipe_registry, RecipeInfo, SaturninRecipe, RecipeType)
from saturnin.component.registry import service_registry, ServiceInfo
from saturnin.lib.console import console
from saturnin.component.bundle import ServiceBundleConfig
from saturnin.component.controller import ServiceExecConfig
from saturnin._scripts.completers import recipe_completer

app = typer.Typer(rich_markup_mode="rich", help="Saturnin recipes.")

@app.command('standalone')
def create_standalone(recipe_name: str=typer.Argument(..., help="Recipe name",
                                                      autocompletion=recipe_completer),
                      section: str=typer.Option(None,
                                                help="Configuration section name"),
                      output: Path=typer.Option(None, help="Output file")):
    """Creates standalone runner (container) for recipe, suitable for compilation with Nuitka.
    """
    recipe: RecipeInfo = recipe_registry.get(recipe_name)
    if recipe is None:
        console.print_error(f"Recipe '{recipe_name}' not installed")
        return
    #
    if output is None:
        output = Path.cwd() / recipe.filename.name
    proto_groups: List[str] = ['firebird.base.protobuf', 'firebird.butler.protobuf']
    svc_names: List[str] = []
    svc_api: List[str] = []
    svc_factory: List[str] = []
    svc_registration: List[str] = []
    proto_import: List[str] = []
    proto_registration: List[str] = []
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

{'CRLF'.join([item for sublist in zip(svc_api, svc_factory) for item in sublist])}

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
