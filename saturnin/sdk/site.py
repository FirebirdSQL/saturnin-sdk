#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/site.py
# DESCRIPTION:    Saturnin SDK site management
# CREATED:        10.2.2021
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

"""Saturnin SDK site management


"""

from __future__ import annotations
from typing import List, Dict
import os
import toml
from uuid import UUID
from pathlib import Path
from configparser import ConfigParser, ExtendedInterpolation
from firebird.base.config import Config, StrOption
from firebird.base.logging import LoggingIdMixin
from saturnin.base import ServiceDescriptor, load
from saturnin.base.site import SaturninScheme

class SDKConfig(Config):
    """Saturnin SDK configuration.
    """
    def __init__(self):
        super().__init__('saturnin-sdk')
        self.editor: StrOption = StrOption('editor', "External editor",
                                           default=os.getenv('EDITOR'))

class ServiceRegistryEntry:
    """Saturnin SDK service registry entry.
    """
    def __init__(self, svc: Dict):
        self._uid: UUID = UUID(svc['uid'])
        self._name: str = svc['name']
        self._desc: str = svc['descriptor']
    def load(self) -> ServiceDescriptor:
        return load(self._desc)
    def from_str(self, value: str) -> None:
        n, d = value.split('=')
        self._name = n.strip()
        self._desc = d.strip()
    def as_str(self) -> str:
        return f'{self._name} = {self._desc}'
    def get_key(self) -> str:
        return self._name
    @property
    def name(self) -> str:
        """Service registration name.
        """
        return self._name
    @property
    def descriptor(self) -> str:
        """Service descriptor locator string.
        """
        return self._desc

class SDKSiteManager(LoggingIdMixin):
    """Saturnin SDK site manager.
    """
    def __init__(self):
        #: Saturnin directory scheme
        self.scheme: SaturninScheme = SaturninScheme()
        #: Saturnin configuration
        self.config: SDKConfig = SDKConfig()
        #: Used configuration files
        self.used_config_files: List[Path] = []
        #: SDK HOME
        self.home = self.scheme.data / 'sdk'
        #: Service registry file
        self.service_reg_file: Path = self.home / 'services.toml'
        #: Registered services
        self.svc_registry: List = []
    def load_configuration(self) -> None:
        """Loads the configuration from configuration files.
        """
        parser: ConfigParser = ConfigParser(interpolation=ExtendedInterpolation())
        for f in parser.read([self.scheme.site_conf,
                              self.scheme.user_conf]):
            self.used_config_files.append(Path(f))
        if parser.has_section('saturnin-sdk'):
            self.config.load_config(parser)
    def initialize(self) -> None:
        """Saturnin site initialization.
        """
        self.load_configuration()
        if self.service_reg_file.is_file():
            self.svc_registry.extend(toml.load(self.service_reg_file)['services'])
    def save_svc_registry(self) -> None:
        """
        """
        if not self.home.exists():
            self.home.mkdir(parents=True)
        if self.svc_registry:
            self.service_reg_file.write_text(toml.dumps({'services': self.svc_registry}))
        elif self.service_reg_file.is_file():
            self.service_reg_file.unlink()
    def iter_registered_services(self, uid: str) -> ServiceRegistryEntry:
        """Iterator over services registered in Saturnin service repository.
        """
        for svc in self.svc_registry:
            if uid is None or uid == svc['uid']:
                yield ServiceRegistryEntry(svc)

#: SDK site manager
site: SDKSiteManager = SDKSiteManager()
site.initialize()
