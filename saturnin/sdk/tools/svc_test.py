#!/usr/bin/python
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
from logging.config import fileConfig
from typing import Dict, List
import sys
import os
from enum import IntEnum
from argparse import ArgumentParser, Action, ArgumentDefaultsHelpFormatter, FileType, \
     Namespace
from configparser import ConfigParser, ExtendedInterpolation, DEFAULTSECT
from pkg_resources import iter_entry_points
from zmq import Context
from saturnin.sdk.types import SaturninError, ServiceTestType
from saturnin.sdk.config import Config, StrOption, ZMQAddressOption, EnumOption
from saturnin.sdk.base import load


__VERSION__ = '0.1'

SECTION_SERVICE_UID = 'service_uid'

# Exceptions

class Error(SaturninError):
    "Base exception for this module."

class StopError(Error):
    "Error that should stop furter processing."

#  Classes

class UpperAction(Action):
    "Converts argument to uppercase."
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.upper())

class TestInfo:
    """Service test information record.
"""
    def __init__(self, section_name, descriptor, endpoint, test_type):
        self.section_name = section_name
        self.descriptor = descriptor
        self.tests = load(descriptor.tests)(Context.instance())
        self.endpoint = endpoint
        self.test_type = test_type
    def run(self) -> None:
        "Run test"
        if self.test_type == ServiceTestType.CLIENT:
            self.tests.run_client_tests(self.endpoint)
        else:
            self.tests.run_raw_tests(self.endpoint)
    name = property(lambda self: self.descriptor.agent.name, doc="Service name")

class Tester:
    """Service tester.
"""
    def __init__(self):
        self.parser = ArgumentParser(prog='svc_test',
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
        group.add_argument('-t','--test-type', action=UpperAction,
                           choices=['client', 'raw'],
                           help="Force test type.")
        group.add_argument('--dry-run', action='store_true',
                           help="Prepare execution but do not run any service")
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
        self.parser.set_defaults(log_level='WARNING', job_name=['tests'],
                                 config='svc_test.cfg', raw=False)
        #
        self.conf = ConfigParser(interpolation=ExtendedInterpolation())
        self.test_conf = Config('svc_test', "Service test configuration")
        self.test_conf._add_option(StrOption('service_name',
                                             "Service name (as specified in the Service Descriptor)",
                                             required=True))
        self.test_conf._add_option(ZMQAddressOption('endpoint', "Service endpoint address",
                                                    required=True))
        self.test_conf._add_option(EnumOption('test_type', ServiceTestType,
                                              "Service endpoint address",
                                              default=ServiceTestType.CLIENT))
        self.args: Namespace = None
        self.config_filename: str = None
        self.log: logging.Logger = None
        self.service_registry: Dict = None
        self.name_map: Dict = None
        self.tests: List = []
    def verbose(self, *args, **kwargs) -> None:
        "Log verbose output, not propagated to upper loggers."
        if self.args.verbose:
            self.log.debug(*args, **kwargs)
    def initialize(self):
        "Initialize tester from command line arguments and configuration file."
        # Command-line arguments
        self.args = self.parser.parse_args()
        self.config_filename = self.args.config.name
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
            logging.basicConfig(format='%(asctime)s %(processName)s:%(threadName)s:%(name)s %(levelname)s: %(message)s')
        logging.getLogger().setLevel(self.args.log_level)
        # Script output configuration
        self.log = logging.getLogger('svc_test')
        self.log.setLevel(logging.DEBUG)
        self.log.propagate = False
        if not self.args.log_only:
            output = logging.StreamHandler(sys.stdout)
            output.setFormatter(logging.Formatter())
            lvl = logging.INFO
            if self.args.verbose:
                lvl = logging.DEBUG
            elif self.args.quiet:
                lvl = logging.ERROR
            output.setLevel(lvl)
            self.log.addHandler(output)
        self.args.config.close()
    def prepare(self):
        "Prepare list of tests to run."
        try:
            # Load descriptors for registered services
            service_descriptors = (entry.load() for entry in iter_entry_points('saturnin.service'))
            self.service_registry = dict((sd.agent.uid, sd) for sd in service_descriptors)
            self.name_map = dict((sd.agent.name, sd) for sd in self.service_registry.values())
            self.conf[SECTION_SERVICE_UID] = dict((sd.agent.name, sd.agent.uid.hex) for sd
                                                  in self.service_registry.values())
            # Create list of test sections
            sections = []
            for job_name in self.args.job_name:
                job_section = 'run_%s' % job_name
                if self.conf.has_section(job_name):
                    sections.append(job_name)
                elif self.conf.has_section(job_section):
                    if not self.conf.has_option(job_section, 'services'):
                        raise StopError("Missing 'services' option in section '%s'" %
                                        job_section)
                    for name in (value.strip() for value in self.conf.get(job_section,
                                                                          'services').split(',')):
                        if not self.conf.has_section(name):
                            raise StopError("Configuration does not have section '%s'" % name)
                        sections.append(name)
                else:
                    raise StopError("Configuration does not have section '%s' or '%s'" %
                                    (job_name, job_section))
            # Validate configuration of services
            for test_section in sections:
                self.test_conf.load_from(self.conf, test_section)
                try:
                    self.test_conf.validate()
                except SaturninError as exc:
                    raise StopError("Error in configuration section '%s'\n%s" % \
                                    (test_section, str(exc)))
                svc_name = self.test_conf.service_name
                if not svc_name in self.name_map:
                    raise StopError("Unknown service '%s'" % svc_name)
                test_type = self.test_conf.test_type
                if self.args.test_type:
                    test_type = ServiceTestType._member_map_[self.args.test_type]
                test_info = TestInfo(test_section, self.name_map[svc_name],
                                     self.test_conf.endpoint, test_type)
                self.tests.append(test_info)
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.terminate()
        except Exception as exc:
            self.log.exception('Unexpected error: %s', str(exc))
            self.terminate()
    def run(self):
        "Run prepared services."
        try:
            for test in self.tests:
                # print configuration
                self.verbose("Prepared to run tests '%s':" % test.section_name)
                self.verbose("  service_name = '%s'" % test.name)
                self.verbose("  endpoint = '%s'" % test.endpoint)
            if not self.args.dry_run:
                for test in self.tests:
                    try:
                        self.log.info("Runing %s tests '%s':", test.test_type.name, test.section_name)
                        test.run()
                    except Exception as exc:
                        self.log.info("\nTest failed with exception: %s", str(exc))
                        logging.exception("Test '%s' failed with exception: %s",
                                          test.section_name, str(exc))
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.terminate()
        except Exception as exc:
            self.log.exception('Unexpected error: %s', str(exc))
            self.terminate()
    def shutdown(self):
        "Shut down the tester."
        logging.debug("Terminating ZMQ context")
        Context.instance().term()
        logging.shutdown()
    def terminate(self):
        "Terminate execution with exit code 1."
        try:
            self.shutdown()
        finally:
            sys.exit(1)

def main():
    "Main function"
    tester = Tester()
    tester.initialize()
    tester.prepare()
    tester.run()
    tester.shutdown()

if __name__ == '__main__':
    main()