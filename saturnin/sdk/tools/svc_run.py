#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/tools/svc_run.py
# DESCRIPTION:    Saturnin service runner (classic version)
# CREATED:        13.3.2019
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

"""Saturnin service runner (classic version)

"""

import logging
from logging.config import fileConfig
from typing import Dict, List
import sys
import os
from argparse import ArgumentParser, Action, ArgumentDefaultsHelpFormatter, FileType, \
     Namespace
from configparser import ConfigParser, ExtendedInterpolation, DEFAULTSECT
from time import sleep
from pkg_resources import iter_entry_points
from zmq import Context
from saturnin.sdk.types import AddressDomain, SaturninError, ServiceTestType, ExecutionMode
from saturnin.sdk.config import StrOption
from saturnin.sdk.base import load
from saturnin.sdk.classic import ServiceExecutor

__VERSION__ = '0.1'

SECTION_LOCAL_ADDRESS = 'local_address'
SECTION_NODE_ADDRESS = 'node_address'
SECTION_NET_ADDRESS = 'net_address'
SECTION_SERVICE_UID = 'service_uid'

# Exceptions

class Error(Exception):
    "Base exception for this module."

class StopError(Error):
    "Error that should stop furter processing."


#  Classes

class UpperAction(Action):
    "Converts argument to uppercase."
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.upper())

class ServiceInfo:
    """Service information record.
"""
    def __init__(self, section_name, descriptor):
        self.section_name = section_name
        self.descriptor = descriptor
        self.config = load(descriptor.config)()
        self.executor = ServiceExecutor(section_name, descriptor)
        self.test = None
        self.test_type = ServiceTestType.CLIENT
        self.test_endpoint = None
    def configure(self, conf) -> None:
        "Load configuration from ConfigParser."
        self.config.load_from(conf, self.section_name)
    def start(self) -> None:
        "Start service"
        self.executor.start(self.config)
    def stop(self) -> None:
        "Stop service."
        try:
            self.executor.stop()
        except TimeoutError:
            self.executor.terminate()
    def prepare_test(self) -> None:
        "Prepare service test for execution."
        self.test = load(self.descriptor.tests)(Context.instance())
        if self.config.execution_mode == ExecutionMode.THREAD:
            for endpoint in self.config.endpoints:
                if endpoint.domain == AddressDomain.LOCAL:
                    self.test_endpoint = endpoint
                    break
        if self.test_endpoint is None or self.config.execution_mode == ExecutionMode.PROCESS:
            for endpoint in self.config.endpoints:
                if endpoint.domain in [AddressDomain.NODE, AddressDomain.NETWORK]:
                    self.test_endpoint = endpoint
                    break
        if self.test_endpoint is None:
            raise StopError("Missing suitable service endpoint to run test for '%s'" %
                            self.section_name)
    def run_test(self) -> None:
        "Run test on service."
        if self.test_type == ServiceTestType.CLIENT:
            self.test.run_client_tests(self.test_endpoint)
        else:
            self.test.run_raw_tests(self.test_endpoint)

    name = property(lambda self: self.descriptor.agent.name, doc="Service name")
    endpoints = property(lambda self: self.executor.endpoints, doc="Service endpoints")


class Runner:
    """Service runner.
"""
    def __init__(self):
        self.parser = ArgumentParser(prog='svc_run',
                                     formatter_class=ArgumentDefaultsHelpFormatter,
                                     description="Saturnin service runner (classic version)")
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
        group.add_argument('-t', '--test', nargs='+', type=str,
                           help="Run test on service. First item is section name, " \
                           "second optional item is test type ('client' or 'raw') " \
                           "[default: client]")
        group.add_argument('--dry-run', action='store_true',
                           help="Prepare execution but do not run any service or test")
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
        self.parser.set_defaults(log_level='WARNING', job_name=['services'],
                                 config='svc_run.cfg', output_dir='${here}')
        #
        self.conf = ConfigParser(interpolation=ExtendedInterpolation())
        self.opt_svc_name = StrOption('service_name',
                                      "Service name (as specified in the Service Descriptor)",
                                      required=True)
        self.args: Namespace = None
        self.config_filename: str = None
        self.log: logging.Logger = None
        self.service_registry: Dict = None
        self.name_map: Dict = None
        self.services: List = []
        self.test_service = None
    def verbose(self, *args, **kwargs) -> None:
        "Log verbose output, not propagated to upper loggers."
        if self.args.verbose:
            self.log.debug(*args, **kwargs)
    def initialize(self) -> None:
        "Initialize runner from command line arguments and configuration file."
        # Command-line arguments
        self.args = self.parser.parse_args()
        self.config_filename = self.args.config.name
        # Configuration
        # Address sections
        self.conf[SECTION_LOCAL_ADDRESS] = {}
        self.conf[SECTION_NODE_ADDRESS] = {}
        self.conf[SECTION_NET_ADDRESS] = {}
        self.conf[SECTION_SERVICE_UID] = {}
        #
        self.conf.read_file(self.args.config)
        # Defaults
        self.conf[DEFAULTSECT]['here'] = os.getcwd()
        #self.conf[DEFAULTSECT]['job_name'] = self.args.job_name
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
        self.log = logging.getLogger('svc_run')
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
        #self.test_logging()
        #
    def test_logging(self) -> None:
        for name in ('', 'svc_run', 'saturnin.sdk.base', 'saturnin.sdk.fbsp', 'saturnin.sdk.classic'):
            l = logging.getLogger(name)
            print("Logger(%s): %s, propagate(%s), parent(%s)" % (l.name, l.getEffectiveLevel(), l.propagate, l.parent.name if l.parent else ''))
            l.debug("(%s:%s) Test", name, 'debug')
            l.info("(%s:%s) Test", name, 'info')
            l.warning("(%s:%s) Test", name, 'warning')
            l.error("(%s:%s) Test", name, 'error')
            l.critical("(%s:%s) Test", name, 'critical')
            for h in l.handlers:
                print("Handler(%s:%s): %s" % (h.__class__.__name__, h.get_name(), h.level))
    def prepare(self) -> None:
        "Prepare list of services to run."
        try:
            # Load descriptors for registered services
            service_descriptors = (entry.load() for entry in iter_entry_points('saturnin.service'))
            self.service_registry = dict((sd.agent.uid, sd) for sd in service_descriptors)
            self.name_map = dict((sd.agent.name, sd) for sd in self.service_registry.values())
            self.conf[SECTION_SERVICE_UID] = dict((sd.agent.name, sd.agent.uid.hex) for sd
                                                  in self.service_registry.values())
            # Create list of service sections
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
            for svc_section in sections:
                if not self.conf.has_option(svc_section, self.opt_svc_name.name):
                    raise StopError("Missing '%s' option in section '%s'" % (self.opt_svc_name.name,
                                                                             svc_section))
                self.opt_svc_name.load_from(self.conf, svc_section)
                svc_name = self.opt_svc_name.value
                if not svc_name in self.name_map:
                    raise StopError("Unknown service '%s'" % svc_name)
                svc_info = ServiceInfo(svc_section, self.name_map[svc_name])
                svc_info.configure(self.conf)
                try:
                    svc_info.config.validate()
                except SaturninError as exc:
                    raise StopError("Error in configuration section '%s'\n%s" % \
                                    (svc_section, str(exc)))
                self.services.append(svc_info)
            # Prepare test run
            if self.args.test is not None:
                test_section = self.args.test[0]
                for svc in self.services:
                    if svc.section_name == test_section:
                        self.test_service = svc
                        break
                if self.test_service is None:
                    raise StopError("Configuration does not have section '%s'" % test_section)
                if len(self.args.test) > 1:
                    value = self.args.test[1].upper()
                    if value in ServiceTestType._member_map_:
                        self.test_service.test_type = ServiceTestType._member_map_[value]
                    else:
                        raise StopError("Illegal value '%s' for enum type '%s'" % (value,
                                                                                   ServiceTestType.__name__))
                self.test_service.prepare_test()
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.terminate()
        except Exception as exc:
            self.log.exception('Unexpected error: %s', str(exc))
            self.terminate()
    def run(self) -> None:
        "Run prepared services."
        try:
            for svc in self.services:
                # print configuration
                self.verbose("Prepared to run task '%s':" % svc.section_name)
                self.verbose("  service_name = %s" % svc.name)
                for option in svc.config.options.values():
                    self.verbose("  %s" % option.get_printout())
            if self.test_service is not None:
                self.verbose("Prepared to run test on task '%s':" %
                             self.test_service.section_name)
                self.verbose("  service_name = %s" % self.test_service.name)
                self.verbose("  test_type = %s" % self.test_service.test_type.name)
                self.verbose("  test_endpoint = %s" % self.test_service.test_endpoint)
            if not self.args.dry_run:
                for svc in self.services:
                    self.log.info("Starting service '%s', task '%s'" % (svc.name,
                                                                        svc.section_name))
                    # refresh configuration to fetch actual addresses
                    svc.configure(self.conf)
                    svc.start()
                    if svc.endpoints:
                        self.verbose("Started with endpoints: " + ', '.join(svc.endpoints))
                    # Update addresses
                    for endpoint in svc.endpoints:
                        if endpoint.domain == AddressDomain.LOCAL:
                            self.conf[SECTION_LOCAL_ADDRESS][svc.section_name] = endpoint
                        elif endpoint.domain == AddressDomain.NODE:
                            self.conf[SECTION_NODE_ADDRESS][svc.section_name] = endpoint
                        else:
                            self.conf[SECTION_NET_ADDRESS][svc.section_name] = endpoint
                if self.test_service is not None:
                    self.test_service.run_test()
                else:
                    try:
                        self.log.info("Press ^C to stop running services...")
                        while self.services:
                            sleep(1)
                            running = [svc for svc in self.services
                                       if svc.executor.is_running()]
                            if len(running) != len(self.services):
                                self.services = running
                                for svc in (set(self.services).difference(set(running))):
                                    self.log.info("Task '%s' (%s) finished" % (svc.section_name,
                                                                               svc.name))
                    except KeyboardInterrupt:
                        self.log.info("Terminating on user request...")
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.terminate()
        except Exception as exc:
            self.log.exception('Unexpected error: %s', str(exc))
            self.terminate()
    def shutdown(self):
        "Shut down the runner."
        l = self.services.copy()
        l.reverse()
        for svc in l:
            if svc.executor.is_running():
                self.log.info("Stopping service '%s', task '%s'" % (svc.name,
                                                                    svc.section_name))
                svc.stop()
            else:
                self.log.info("Service '%s', task '%s' stopped already" % (svc.name,
                                                                           svc.section_name))

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
    runner = Runner()
    runner.initialize()
    runner.prepare()
    runner.run()
    runner.shutdown()

if __name__ == '__main__':
    main()
