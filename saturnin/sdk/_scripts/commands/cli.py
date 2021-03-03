#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/_scripts/commands/cli.py
# DESCRIPTION:    Saturnin SDK console commands
# CREATED:        19.1.2021
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

"""Saturnin SDK console commands


"""

from __future__ import annotations
#from typing import Dict
import toml
import uuid
from pathlib import Path
from site import getsitepackages
from argparse import ArgumentParser, Namespace
from saturnin.base import Error, site, load, ServiceDescriptor
from saturnin.lib.command import Command, CommandManager, format_exception_only
from saturnin.lib.pyproject import PyProjectTOML
from saturnin.sdk.site import site

def find(*, uid: str=None, name: str=None, directory: str=None) -> int:
    result = 0
    for svc in site.svc_registry:
        if uid is not None:
            if svc['uid'] == uid:
                return result
        elif name is not None:
            if svc['name'] == name:
                return result
        elif directory is not None:
            if svc['directory'] == directory:
                return result
        result += 1
    return -1

class SiteCommand(Command):
    """SITE Saturnin SDK console command.
    """
    def __init__(self):
        super().__init__('site', "Manage directories linked to site-packages.")
        self.pth: Path = Path(getsitepackages()[0]) / 'saturnin.pth'
    def on_error(self, exc: Exception):
        """Called when exception is raised in `.run()`.
        """
        self.out("ERROR\n")
    def set_arguments(self, manager: CommandManager, parser: ArgumentParser) -> None:
        """Set command arguments.
        """
        gr = parser.add_mutually_exclusive_group()
        gr.add_argument('-a', '--add', metavar='PATH',
                        help="Link directory to site-packages")
        gr.add_argument('-r', '--remove', metavar='PATH',
                        help="Remove directory link to site-packages")
        gr.add_argument('-l', '--list', action='store_true', default=False,
                        help="List directories linked to site-packages")
    def run(self, args: Namespace) -> None:
        """Command execution.

        Arguments:
            args: Collected argument values.
        """
        paths: List[str] = []
        if self.pth.is_file():
            paths.extend(Path(x) for x in self.pth.read_text().splitlines())
        if args.add is not None:
            path: Path = Path(args.add).absolute()
            if path in paths:
                raise Error(f"Path '{path}' already linked to site-packages")
            self.out(f"Linking '{path}' to site-packages ... ")
            paths.append(path)
            self.pth.write_text(''.join(f'{str(x)}\n' for x in paths))
            self.out("OK\n")
        elif args.remove is not None:
            path: Path = Path(args.remove).absolute()
            if path not in paths:
                raise Error(f"Path '{path}' is not linked to site-packages")
            self.out(f"Unlinking '{path}' from site-packages ... ")
            paths.remove(path)
            self.pth.write_text(''.join(f'{str(x)}\n' for x in paths))
            self.out("OK\n")
            # Remove registration of services from removed directory
            write_svc = False
            while (i := find(directory=str(path))) >= 0:
                self.out(f"Removing registration of {path} ... ")
                site.svc_registry.pop(i)
                write_svc = True
                self.out('OK\n')
            if write_svc:
                self.out("Saving service registry ... ")
                site.save_svc_registry()
                self.out("OK\n")
        elif args.list:
            if paths:
                self.out("Directories linked to site-packages:\n")
                for path in paths:
                    self.out(f"  {path}\n")
            else:
                self.out("No directories are linked to site-packages.\n")

class ServiceCommand(Command):
    """SERVICE Saturnin SDK console command.
    """
    def __init__(self):
        super().__init__('service', "Manage services in directories linked to site-packages.")
        self.pth: Path = Path(getsitepackages()[0]) / 'saturnin.pth'
        self.site_dirs = []
        if self.pth.is_file():
            self.site_dirs.extend(Path(x) for x in self.pth.read_text().splitlines())
    def on_error(self, exc: Exception):
        """Called when exception is raised in `.run()`.
        """
        self.out("ERROR\n")
    def process_toml(self, toml_file: Path, site_dir: Path) -> bool:
        self.out(f"  Loading {toml_file} ... ")
        toml_data = toml.load(toml_file)
        try:
            toml_data['tool']['saturnin']['metadata']
        except:
            self.out('SKIPPED - missing [tool.saturnin.metadata]\n')
            return False
        try:
            svc_toml: PyProjectTOML = PyProjectTOML(toml_data)
        except Exception as exc:
            msg = ''.join(format_exception_only(type(exc), exc))
            self.out(f"SKIPPED - TOML error: {msg}\n")
            return False
        if svc_toml.component_type != 'service':
            self.out('SKIPPED - not a service\n')
            return False
        package = '.'.join(toml_file.relative_to(site_dir).parts[:-1])
        svc = {'uid': svc_toml.uid,
               'name': svc_toml.original_name,
               'version': svc_toml.version,
               'description': svc_toml.description,
               'descriptor': f"{package}.{svc_toml.descriptor}",
               'directory': str(site_dir),
               'top-level': package,
               }
        if find(uid=svc['uid']) >= 0:
            self.out("SKIPPED - service already registered\n")
            return False
        site.svc_registry.append(svc)
        self.out("OK\n")
        self.out(f"    name: {svc['name']}\n")
        self.out(f"    version: {svc['version']}\n")
        self.out(f"    uid: {svc['uid']}\n")
        return True
    def set_arguments(self, manager: CommandManager, parser: ArgumentParser) -> None:
        """Set command arguments.
        """
        gr = parser.add_mutually_exclusive_group()
        gr.add_argument('-r', '--register', metavar='PACKAGE',
                        help="Register service(s). "
                        "PACKAGE is top level package name from SDK site directory. "
                        "Use 'ALL' to register all services "
                        "from all SDK site directories.")
        gr.add_argument('-u', '--unregister', metavar='SERVICE',
                        help="Unregister service(s). "
                        "SERVICE could be either service GUID or name. "
                        "Use 'ALL' to unregister all registered services.")
        gr.add_argument('-l', '--list', action='store_true', default=False,
                        help="List registered services.")
        gr.add_argument('-i', '--info', metavar='SERVICE',
                        help="Show information about registered service. "
                        "SERVICE could be either service GUID or name.")
    def run(self, args: Namespace) -> None:
        """Command execution.

        Arguments:
            args: Collected argument values.
        """
        write = False
        # LIST
        if args.list:
            i = 1
            for svc in site.svc_registry:
                self.out(f"{i:2}: name:    {svc['name']}\n")
                self.out(f"    version: {svc['version']}\n")
                self.out(f"    uid:     {svc['uid']}\n")
                i += 1
        # INFO
        elif args.info is not None:
            try:
                uuid.UUID(args.info)
                i = find(uid=args.info)
            except ValueError:
                i = find(name=args.info)
            if i >= 0:
                svc = site.svc_registry[i]
                self.out("Loading service descriptor ... ")
                desc: ServiceDescriptor = load(svc['descriptor'])
                self.out("OK\n")
                self.out(f"name:           {svc['name']}\n")
                self.out(f"uid:            {svc['uid']}\n")
                if desc.api:
                    self.out(f"type:           service\n")
                else:
                    self.out(f"type:           micro-service\n")
                self.out(f"version:        {svc['version']}\n")
                self.out(f"description:    {svc['description']}\n")
                self.out(f"classification: {desc.agent.classification}\n")
                self.out(f"vendor:         {desc.agent.vendor_uid}\n")
                self.out(f"path:           {svc['directory']}\n")
                self.out(f"top-level:      {desc.package}\n")
                if desc.api:
                    self.out("API:\n")
                    ai = 1
                    for api in desc.api:
                        self.out(f"{ai:2}: uid:        {api.get_uid()}\n")
                        self.out(f"    name:       {api.__name__}\n")
                        self.out("    Members:\n")
                        for value in api.__members__.values():
                            self.out(f"              {value.value:3}: {value.name}\n")
            else:
                raise ValueError(f"Service {args.info} not registered.")
        # REGISTER
        elif args.register is not None:
            if args.register.upper() == 'ALL':
                if not self.site_dirs:
                    raise ValueError("No directories are linked to site-packages.")
                site.svc_registry.clear()
                for site_dir in self.site_dirs:
                    self.out(f"Scanning {site_dir}...\n")
                    for toml_file in site_dir.rglob('pyproject.toml'):
                        write |= self.process_toml(toml_file, site_dir)
            else:
                for site_dir in self.site_dirs:
                    target: Path = site_dir / args.register
                    if target.is_dir():
                        toml_file = target / 'pyproject.toml'
                        if toml_file.is_file():
                            write |= self.process_toml(toml_file, site_dir)
        # UNREGISTER
        elif args.unregister is not None:
            if site.svc_registry:
                if args.unregister.upper() == 'ALL':
                    self.out(f"Removing registration of ALL services ... ")
                    site.svc_registry.clear()
                    write = True
                    self.out("OK\n")
                else:
                    try:
                        uuid.UUID(args.info)
                        svc = find(uid=args.unregister)
                    except ValueError:
                        svc = find(name=args.unregister)
                    if svc >= 0:
                        self.out(f"Removing registration of {args.unregister} ... ")
                        site.svc_registry.pop(svc)
                        write = True
                        self.out('OK\n')
                    else:
                        raise ValueError(f"Service {args.unregister} not registered.")
            else:
                self.out("No services are registered.\n")
        #
        if write:
            self.out("Saving service registry ... ")
            site.save_svc_registry()
            self.out("OK\n")
