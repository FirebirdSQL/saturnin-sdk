#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/tools/svc_test.py
# DESCRIPTION:    Saturnin service tester (classic version)
# CREATED:        12.9.2019
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
# Copyright (c) 2019 Firebird Project (www.firebirdsql.org)
# All Rights Reserved.
#
# Contributor(s): Pavel Císař (original code)
#                 ______________________________________.

"""Saturnin service tester (classic version)

"""

import logging
import typing as t
from logging.config import fileConfig
import sys
import os
import uuid
from argparse import ArgumentParser, Action, ArgumentDefaultsHelpFormatter, FileType, \
     Namespace
from configparser import ConfigParser, ExtendedInterpolation, DEFAULTSECT
from pkg_resources import iter_entry_points
import zmq
from saturnin.core.types import ZMQAddress, ServiceTestType, ServiceDescriptor, \
     SaturninError, StopError
from saturnin.core.collections import Registry
from saturnin.core.config import Config, UUIDOption, ZMQAddressOption, EnumOption
from saturnin.core.service import load
from saturnin.sdk.test.fbsp import BaseTestRunner


__VERSION__ = '0.1'
"""Service test runner version"""

SECTION_SERVICE_UID = 'service_uid'
"""Configuration section name for service UIDs"""

# Functions

def title(text: str, size: int=80, char: str='='):
    """Returns centered title surrounded by char."""
    return f"  {text}  ".center(size, char)

#  Classes

class UpperAction(Action):
    """Converts argument to uppercase."""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.upper())

class TestConfig(Config):
    """Test configuration"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        #self.test_conf: Config = Config('svc_test', "Service test configuration")
        self.service_uid: UUIDOption = \
            self.add_option(UUIDOption('service_uid',
                                       "Service UID (agent.uid in the Service Descriptor)",
                                       required=True))
        self.endpoint: ZMQAddressOption = \
            self.add_option(ZMQAddressOption('endpoint', "Service endpoint address",
                                             required=True))
        self.test_type: EnumOption = \
            self.add_option(EnumOption('test_type', ServiceTestType,
                                       "Service endpoint address",
                                       default=ServiceTestType.CLIENT))

class TestInfo:
    """Service test information record.
"""
    def __init__(self, section_name: str, descriptor: ServiceDescriptor,
                 endpoint: ZMQAddress, test_type: ServiceTestType):
        self.section_name: str = section_name
        self.descriptor: ServiceDescriptor = descriptor
        self.tests: BaseTestRunner = load(descriptor.tests)(zmq.Context.instance())
        self.endpoint: ZMQAddress = endpoint
        self.test_type: ServiceTestType = test_type
    def run(self) -> None:
        """Run test"""
        if self.test_type == ServiceTestType.CLIENT:
            self.tests.run_client_tests(self.endpoint)
        else:
            self.tests.run_raw_tests(self.endpoint)
    uid: uuid.UUID = property(lambda self: self.descriptor.agent.uid, doc="Service ID")
    name: str = property(lambda self: self.descriptor.agent.name, doc="Service name")

class Tester:
    """Service tester.

.. program:: svc_test

usage::

    svc_test [-h] [--version] [-c FILE] [-o DIR] [-t {client,raw}]
                [--dry-run] [-v] [-q] [--log-only]
                [-l {critical,fatal,error,warn,warning,info,debug,notset}]
                [--trace]
                [job_name [job_name ...]]

**optional arguments:**

.. option::  -h, --help

   show this help message and exit

.. option::  --version

   show program's version number and exit

**positional arguments:**

.. option::  job_name

    Job name (default: ['tests'])

**run arguments:**

.. option::  -c FILE, --config FILE

    Configuration file (default: svc_run.cfg)

.. option::  -o DIR, --output-dir DIR

    Force directory for log files and other output (default: ${here})

.. option::  -t {client,raw}, --test-type {client,raw}

    Force test type. (default: None)

.. option::  --dry-run

    Prepare execution but do not run any test (default: False)

**output arguments:**

.. option::  -v, --verbose

    Verbose output (default: False)

.. option::  -q, --quiet

    No screen output (default: False)

.. option::  --log-only

    Suppress all screen output including error messages (default: False)

.. option::  -l {critical,fatal,error,warn,warning,info,debug,notset}, --log-level {critical,fatal,error,warn,warning,info,debug,notset}

    Logging level (default: WARNING)

.. option::  --trace

    Log unexpected errors with stack trace (default: False)
"""
    def __init__(self):
        self.parser: ArgumentParser = \
            ArgumentParser(prog='svc_test',
                           formatter_class=ArgumentDefaultsHelpFormatter,
                           description="Saturnin service tester (classic version)")
        self.parser.add_argument('--version', action='version', version='%(prog)s '+__VERSION__)
        #
        group = self.parser.add_argument_group("positional arguments")
        group.add_argument('job_name', nargs='*', help="Job name")
        #
        group = self.parser.add_argument_group("run arguments")
        group.add_argument('-c', '--config', metavar='FILE',
                           type=FileType(mode='r', encoding='utf8'),
                           help="Configuration file")
        group.add_argument('-o', '--output-dir', metavar='DIR',
                           help="Force directory for log files and other output")
        group.add_argument('-t', '--test-type', action=UpperAction,
                           choices=['client', 'raw'],
                           help="Force test type.")
        group.add_argument('--dry-run', action='store_true',
                           help="Prepare execution but do not run any test")
        #
        group = self.parser.add_argument_group("output arguments")
        group.add_argument('-v', '--verbose', action='store_true', help="Verbose output")
        group.add_argument('-q', '--quiet', action='store_true', help="No screen output")
        group.add_argument('--log-only', action='store_true',
                           help="Suppress all screen output including error messages")
        group.add_argument('-l', '--log-level', action=UpperAction,
                           choices=[x.lower() for x in logging._nameToLevel
                                    if isinstance(x, str)],
                           help="Logging level")
        group.add_argument('--trace', action='store_true',
                           help="Log unexpected errors with stack trace")
        self.parser.set_defaults(log_level='WARNING', job_name=['tests'],
                                 config='svc_test.cfg')
        #
        self.conf: ConfigParser = ConfigParser(interpolation=ExtendedInterpolation())
        self.test_conf: TestConfig = TestConfig('svc_test', "Service test configuration")
        self.args: Namespace = None
        self.config_filename: str = None
        self.log: logging.Logger = None
        self.service_registry: Registry = Registry()
        self.tests: t.List[BaseTestRunner] = []
    def verbose(self, *args, **kwargs) -> None:
        """Log verbose output, not propagated to upper loggers."""
        if self.args.verbose:
            self.log.debug(*args, **kwargs)
    def initialize(self) -> None:
        """Initialize tester from command line arguments and configuration file."""
        # Command-line arguments
        self.args: Namespace = self.parser.parse_args()
        self.config_filename: str = self.args.config.name
        # Configuration
        self.conf.read_file(self.args.config)
        # Defaults
        self.conf[DEFAULTSECT]['here'] = os.getcwd()
        if self.args.output_dir is None:
            self.conf[DEFAULTSECT]['output_dir'] = os.getcwd()
        else:
            self.conf[DEFAULTSECT]['output_dir'] = self.args.output_dir
        # Logging configuration
        if self.conf.has_section('loggers'):
            self.args.config.seek(0)
            fileConfig(self.args.config)
        else:
            logging.basicConfig(format='%(asctime)s %(processName)s:%(threadName)s:'\
                                '%(name)s %(levelname)s: %(message)s')
        logging.getLogger().setLevel(self.args.log_level)
        # Script output configuration
        self.log = logging.getLogger('svc_test')
        self.log.setLevel(logging.DEBUG)
        self.log.propagate = False
        if not self.args.log_only:
            output: logging.StreamHandler = logging.StreamHandler(sys.stdout)
            output.setFormatter(logging.Formatter())
            lvl = logging.INFO
            if self.args.verbose:
                lvl = logging.DEBUG
            elif self.args.quiet:
                lvl = logging.ERROR
            output.setLevel(lvl)
            self.log.addHandler(output)
        self.args.config.close()
    def prepare(self) -> None:
        """Prepare list of tests to run."""
        try:
            # Load descriptors for registered services
            self.service_registry.extend(entry.load() for entry in
                                         iter_entry_points('saturnin.service'))
            self.conf[SECTION_SERVICE_UID] = dict((sd.agent.name, sd.agent.uid.hex) for sd
                                                  in self.service_registry)
            # Create list of test sections
            sections = []
            for job_name in self.args.job_name:
                job_section = f'run_{job_name}'
                if self.conf.has_section(job_name):
                    sections.append(job_name)
                elif self.conf.has_section(job_section):
                    if not self.conf.has_option(job_section, 'services'):
                        raise StopError(f"Missing 'services' option in section '{job_section}'")
                    for name in (value.strip() for value in self.conf.get(job_section,
                                                                          'services').split(',')):
                        if not self.conf.has_section(name):
                            raise StopError(f"Configuration does not have section '{name}'")
                        sections.append(name)
                else:
                    raise StopError(f"Configuration does not have section "
                                    f"'{job_name}' or '{job_section}'")
            # Validate configuration of services
            for test_section in sections:
                self.test_conf.load_from(self.conf, test_section)
                try:
                    self.test_conf.validate()
                except SaturninError as exc:
                    raise StopError(f"Error in configuration section 'test_section'\n{exc}")
                svc_uid = self.test_conf.service_uid.value
                if not svc_uid in self.service_registry:
                    raise StopError(f"Unknown service '{svc_uid}'")
                test_type = self.test_conf.test_type.value
                if self.args.test_type:
                    test_type = ServiceTestType.get_member_map()[self.args.test_type]
                test_info: TestInfo = TestInfo(test_section, self.service_registry[svc_uid],
                                               self.test_conf.endpoint.value, test_type)
                self.tests.append(test_info)
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.terminate()
        except Exception as exc:
            if self.args.trace:
                self.log.exception('Unexpected error: %s', str(exc))
            else:
                self.log.error('Unexpected error: %s', str(exc))
            self.terminate()
    def run(self) -> None:
        """Run prepared service tests."""
        try:
            for test in self.tests:
                # print configuration
                self.verbose(title(f"Test '{test.section_name}'"))
                self.verbose(f"service_uid = {test.uid} [{test.name}]")
                self.verbose(f"endpoint = {test.endpoint}")
                self.verbose(f"test type = {test.test_type.name}")
            if not self.args.dry_run:
                self.verbose(title("Running tests", char='*'))
                for test in self.tests:
                    try:
                        self.log.info("Runing %s test '%s':", test.test_type.name,
                                      test.section_name)
                        test.run()
                    except Exception as exc:
                        self.log.info("\nTest failed with exception: %s", str(exc))
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.terminate()
        except Exception as exc:
            if self.args.trace:
                self.log.exception('Unexpected error: %s', str(exc))
            else:
                self.log.error('Unexpected error: %s', str(exc))
            self.terminate()
    def shutdown(self) -> None:
        """Shut down the tester."""
        logging.debug("Terminating ZMQ context")
        zmq.Context.instance().term()
        logging.shutdown()
    def terminate(self) -> t.NoReturn:
        """Terminate execution with exit code 1."""
        try:
            self.shutdown()
        finally:
            sys.exit(1)

def main():
    """Main function"""
    tester: Tester = Tester()
    tester.initialize()
    tester.prepare()
    tester.run()
    tester.shutdown()
