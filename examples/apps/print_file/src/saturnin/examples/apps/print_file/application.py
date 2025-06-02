# SPDX-FileCopyrightText: 2023-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin examples
# FILE:           saturnin/examples/apps/print_file/application.py
# DESCRIPTION:    Print text file application
# CREATED:        24.2.2023
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
# Copyright (c) 2023 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin examples - Implementation of the Print Text File application.

This module provides the `print_file` command-line application, which prints a specified
text file to the console, optionally applying syntax highlighting using Pygments.
It demonstrates the use of Saturnin recipes and bundles to achieve its functionality.
"""

from __future__ import annotations

import subprocess
from configparser import ConfigParser, ExtendedInterpolation
from contextlib import suppress
from pathlib import Path
from typing import Annotated
from uuid import uuid4

import typer
from pygments.lexers import get_all_lexers, get_lexer_for_filename
from rich.syntax import Syntax
from saturnin._scripts.completers import path_completer
from saturnin.base import directory_scheme
from saturnin.component.recipe import RecipeInfo, recipe_registry
from saturnin.lib.console import console


def lexer_completer(ctx, args, incomplete) -> list:
    """Click completer for Pygment lexer.
    """
    return list(sum((aliases for longname, aliases, patterns, mimetypes in get_all_lexers()),
                    ()))

app = typer.Typer(rich_markup_mode="markdown", help="Saturnin applications.")

app.command()
def print_file(ctx: typer.Context,
               filename: Annotated[Path, typer.Argument(..., help="File to be printed",
                                                        autocompletion=path_completer)],
               encoding: Annotated[str, typer.Option(help="File encoding")]='utf-8',
               lexer: Annotated[str| None, typer.Option(help="Syntax lexer",
                                                  autocompletion=lexer_completer)]=None) -> None:
    """Sample application that prints a text file on screen with optional syntax highlight.
    """
    # The command name is the recipe name
    recipe_name = ctx.command.name
    recipe: RecipeInfo = recipe_registry.get(recipe_name)
    if recipe is None:
        console.print_error(f"Recipe '{recipe_name}' not installed")
        return
    #
    config: ConfigParser = ConfigParser(interpolation=ExtendedInterpolation())
    config.read(recipe.filename)
    config['args']['filename'] = str(filename)
    config['args']['charset'] = encoding
    cfg_file: Path = directory_scheme.tmp / uuid4().hex
    with cfg_file.open(mode='w') as f:
        config.write(f)
    cmd = ['saturnin-bundle' if recipe.executor is None else str(recipe.executor),
           str(cfg_file)]
    #
    if lexer is None:
        with suppress(Exception):
            lexer = get_lexer_for_filename(filename).aliases[0]
    #
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        console.print(Syntax(result.stdout, lexer=lexer))
        if result.returncode != 0:
            console.print_error('Recipe execution failed')
    finally:
        cfg_file.unlink(missing_ok=True)

def create_recipe() -> str:
    """Returns Saturnin recipe for print_file application.
    """
    return """[saturnin.recipe]
recipe_type = bundle
execution_mode = normal
description = Prints a text file on screen with optional syntax highlight.
application = 826ecaca-d3b6-11ed-97b5-5c879cc92822

[bundle]
agents = reader, writer

[args]
filename = stdin
charset = utf-8

[reader]
agent = 936d2670-93d8-5c45-84a7-b8dbc799ad97
pipe = pipe-1
pipe_address = inproc://${pipe}
pipe_mode = bind
pipe_format = text/plain;charset=utf-8
filename = ${args:filename}
file_format = text/plain;charset=${args:charset}

[writer]
agent = 4e606fdf-3fa9-5d18-a714-9448a8085aab
pipe = pipe-1
pipe_address = inproc://${pipe}
pipe_mode = connect
pipe_format = text/plain;charset=utf-8
filename = stdout
file_format = text/plain;charset=utf-8
file_mode = write
"""
