# SPDX-FileCopyrightText: 2023-present The Firebird Project <www.firebirdsql.org>
#
# SPDX-License-Identifier: MIT
#
# PROGRAM/MODULE: Saturnin examples
# FILE:           saturnin/examples/apps/dummy/application.py
# DESCRIPTION:    Test dummy application
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

"""Saturnin examples - Implementation of the Test Dummy Application.

This module provides a simple command-line application (`dummy_app`) that demonstrates
basic Saturnin application structure, argument handling using Typer, and console output.
It's primarily intended for testing and example purposes.
"""

from __future__ import annotations

from enum import Enum
from time import sleep
from typing import Annotated

import typer
from saturnin.component.recipe import RecipeType, SaturninRecipe
from saturnin.lib.console import console

from .api import APP_DESCRIPTOR, APP_UID


class Visitor(Enum):
    """Represents different types of 'visitors' for the dummy application.

    Each visitor type triggers a distinct set of messages printed to the console.
    """
    CHUBB_CHUBBS = 'chubb_chubbs' # Chubb-chubbs are coming! To sing karaoke and ate your world...
    CATS = 'cats' # All your base are belong to us
    DUPLO = 'duplo' # We are from planet Duplo, and we came in peace to destroy your world


app = typer.Typer(rich_markup_mode="markdown", help="Saturnin applications.")

app.command()
def dummy_app(visitor: Annotated[Visitor, typer.Argument(..., help="Who came for visit?")]) -> None:
    """A dummy command-line application for testing Saturnin application features.

    Prints different messages to the console based on the selected `visitor` argument.
    """
    if visitor is Visitor.CHUBB_CHUBBS:
        console.print("[bold red]Chubb-chubbs[/] are coming!")
        sleep(3)
        console.print("To sing karaoke and ate your world...")
    elif visitor is Visitor.CATS:
        console.print("How are you gentlemen !!")
        console.print("[bold red]All your base are belong to us.")
        console.print("You are on the way to destruction.")
        sleep(1)
        console.print("You have no chance to survive make your time.")
        sleep(2)
        console.print("Ha Ha Ha Ha …")
    else:
        console.print("We are from planet Duplo, and we came in peace to destroy your world.")

def create_recipe() -> str:
    """Generates and returns a Saturnin recipe configuration string for the dummy application.
    """
    recipe = SaturninRecipe()
    recipe.recipe_type.value = RecipeType.SERVICE
    recipe.application.value = APP_UID
    recipe.description.value = APP_DESCRIPTOR.description
    return recipe.get_config()
