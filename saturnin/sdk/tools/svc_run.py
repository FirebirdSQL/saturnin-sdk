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
import typing as t
from logging.config import fileConfig
import sys
import os
import uuid
from argparse import ArgumentParser, Action, ArgumentDefaultsHelpFormatter, FileType, \
     Namespace
from configparser import ConfigParser, ExtendedInterpolation, DEFAULTSECT
from time import sleep
from pkg_resources import iter_entry_points
import zmq
from ..types import  AddressDomain, ZMQAddress, ZMQAddressList, \
     ServiceTestType, ExecutionMode, ServiceDescriptor, SaturninError, StopError
from ..collections import Registry
from ..config import UUIDOption, MicroserviceConfig, ServiceConfig
from ..service import load
from ..classic import ServiceExecutor
from ..test.fbsp import BaseTestRunner

__VERSION__ = '0.1'

SECTION_LOCAL_ADDRESS = 'local_address'
SECTION_NODE_ADDRESS = 'node_address'
SECTION_NET_ADDRESS = 'net_address'
SECTION_SERVICE_UID = 'service_uid'
SECTION_PEER_UID = 'peer_uid'

# Functions

def title(text: str, size: int=80, char: str='='):
    "Returns centered title surrounded by char."
    return f"  {text}  ".center(size, char)

#  Classes

class UpperAction(Action):
    "Converts argument to uppercase."
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.upper())

class ServiceInfo:
    """Service information record.
"""
    def __init__(self, section_name: str, descriptor: ServiceDescriptor, peer_uid: uuid.UUID):
        self.section_name: str = section_name
        self.descriptor: ServiceDescriptor = descriptor
        self.config: MicroserviceConfig = descriptor.config()
        self.executor: ServiceExecutor = ServiceExecutor(descriptor, peer_uid, section_name)
        self.test: BaseTestRunner = None
        self.test_type: ServiceTestType = ServiceTestType.CLIENT
        self.test_endpoint: ZMQAddress = None
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
        if not self.descriptor.tests:
            raise StopError("Service %s:%s does not have tests" % (self.descriptor.agent.uid,
                                                                     self.descriptor.agent.name))
        self.test = load(self.descriptor.tests)(zmq.Context.instance())
        if isinstance(self.config, ServiceConfig):
            if self.config.execution_mode.value == ExecutionMode.THREAD:
                for endpoint in self.config.endpoints.value:
                    if endpoint.domain == AddressDomain.LOCAL:
                        self.test_endpoint = endpoint
                        break
            if self.test_endpoint is None or self.config.execution_mode.value == ExecutionMode.PROCESS:
                for endpoint in self.config.endpoints.value:
                    if endpoint.domain in [AddressDomain.NODE, AddressDomain.NETWORK]:
                        self.test_endpoint = endpoint
                        break
            if self.test_endpoint is None:
                raise StopError("Missing suitable service endpoint to run test for '%s'" %
                                self.section_name)
        else:
            raise StopError("Can't test microservices.")
    def run_test(self) -> None:
        "Run test on service."
        if self.test_type == ServiceTestType.CLIENT:
            self.test.run_client_tests(self.test_endpoint)
        else:
            self.test.run_raw_tests(self.test_endpoint)

    name: str = property(lambda self: self.descriptor.agent.name, doc="Service name")
    uid: uuid.UUID = property(lambda self: self.executor.uid, doc="Service Peer ID")
    endpoints: ZMQAddressList = property(lambda self: self.executor.endpoints,
                                          doc="Service endpoints")

class Runner:
    """Service runner.
"""
    def __init__(self):
        self.parser: ArgumentParser = \
            ArgumentParser(prog='svc_run',
                           formatter_class=ArgumentDefaultsHelpFormatter,
                           description="Saturnin service runner (classic version)")
        self.parser.add_argument('--version', action='version', version='%(prog)s '+__VERSION__)
        #
        group = self.parser.add_argument_group("run arguments")
        group.add_argument('-j', '--job', nargs='*', help="Job name")
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
        group.add_argument('--trace', action='store_true',
                           help="Log unexpected errors with stack trace")
        self.parser.set_defaults(log_level='WARNING', job=['services'],
                                 config='svc_run.cfg', output_dir='${here}')
        #
        self.conf: ConfigParser = ConfigParser(interpolation=ExtendedInterpolation())
        self.opt_svc_uid: UUIDOption = UUIDOption('service_uid',
                                                  "Service UID (agent.uid in the Service Descriptor)",
                                                  required=True)
        self.args: Namespace = None
        self.config_filename: str = None
        self.log: logging.Logger = None
        self.service_registry: Registry = Registry()
        self.services: t.List[ServiceInfo] = []
        self.test_service: ServiceInfo = None
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
        self.conf[SECTION_PEER_UID] = {}
        #
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
            logging.basicConfig(format='%(asctime)s %(processName)s:'\
                                '%(threadName)s:%(name)s %(levelname)s: %(message)s')
        logging.getLogger().setLevel(self.args.log_level)
        # Script output configuration
        self.log = logging.getLogger('svc_run')
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
        "Prepare list of services to run."
        try:
            # Load descriptors for registered services
            self.service_registry.extend(entry.load() for entry in
                                         iter_entry_points('saturnin.service'))
            self.conf[SECTION_SERVICE_UID] = dict((sd.agent.name, sd.agent.uid.hex) for sd
                                                  in self.service_registry)
            # Create list of service sections
            sections = []
            for job_name in self.args.job:
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
            # Assign Peer IDs to service sections (instances)
            self.conf[SECTION_PEER_UID] = dict((svc_section, uuid.uuid1().hex) for
                                               svc_section in sections)
            # Validate configuration of services
            for svc_section in sections:
                if not self.conf.has_option(svc_section, self.opt_svc_uid.name):
                    raise StopError("Missing '%s' option in section '%s'" % (self.opt_svc_uid.name,
                                                                             svc_section))
                self.opt_svc_uid.load_from(self.conf, svc_section)
                svc_uid = self.opt_svc_uid.value
                if not svc_uid in self.service_registry:
                    raise StopError("Unknown service '%s'" % svc_uid)
                svc_info = ServiceInfo(svc_section, self.service_registry[svc_uid],
                                       uuid.UUID(self.conf[SECTION_PEER_UID][svc_section]))
                try:
                    svc_info.configure(self.conf)
                    svc_info.config.validate()
                except (SaturninError, TypeError, ValueError) as exc:
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
                    raise StopError("Section '%s' is not related to active service" % test_section)
                if len(self.args.test) > 1:
                    value = self.args.test[1].upper()
                    if value in ServiceTestType.get_member_map():
                        self.test_service.test_type = ServiceTestType.get_member_map()[value]
                    else:
                        raise StopError("Illegal value '%s' for enum type '%s'"
                                        % (value, ServiceTestType.__name__))
                self.test_service.prepare_test()
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.services.clear()
            self.terminate()
        except Exception as exc:
            if self.args.trace:
                self.log.exception('Unexpected error: %s', str(exc))
            else:
                self.log.error('Unexpected error: %s', str(exc))
            self.services.clear()
            self.terminate()
    def run(self) -> None:
        "Run prepared services."
        try:
            for svc in self.services:
                # print configuration
                self.verbose(title("Task '%s'" % svc.section_name, char='-'))
                self.verbose("service_uid = %s [%s]" % (svc.uid, svc.name))
                for option in svc.config.options.values():
                    self.verbose("%s" % option.get_printout())
            if self.test_service is not None:
                self.verbose(title("Test on task '%s'" % self.test_service.section_name,
                                   char='-'))
                self.verbose("service_uid = %s [%s]" % (self.test_service.uid,
                                                        self.test_service.name))
                self.verbose("test_type = %s" % self.test_service.test_type.name)
                self.verbose("test_endpoint = %s" % self.test_service.test_endpoint)
            if not self.args.dry_run:
                self.verbose(title("Starting services"))
                for svc in self.services:
                    # refresh configuration to fetch actual addresses
                    self.log.info("Starting service '%s', task '%s'", svc.name,
                                  svc.section_name)
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
                    self.verbose(title("Running test", char='-'))
                    self.test_service.run_test()
                else:
                    self.verbose(title("Running", char='-'))
                    try:
                        self.log.info("Press ^C to stop running services...")
                        while self.services:
                            sleep(1)
                            running = [svc for svc in self.services
                                       if svc.executor.is_running()]
                            if len(running) != len(self.services):
                                self.services = running
                                for svc in set(self.services).difference(set(running)):
                                    self.log.info("Task '%s' (%s) finished",
                                                  svc.section_name, svc.name)
                    except KeyboardInterrupt:
                        self.log.info("Terminating on user request...")
                    else:
                        self.log.info("All services terminated.")
                self.verbose(title("Shutdown", char='-'))
            #
        except StopError as exc:
            self.log.error(str(exc))
            self.terminate()
        except Exception as exc:
            if self.args.trace:
                self.log.error('Unexpected error: %s', exc)
            else:
                self.log.error('Unexpected error: %s', exc)
            self.terminate()
    def shutdown(self) -> None:
        "Shut down the runner."
        l = self.services.copy()
        l.reverse()
        for svc in l:
            if svc.executor.is_running():
                self.log.info("Stopping service '%s' %s, task '%s'", svc.name,
                              svc.executor.mode.name.lower(), svc.section_name)
                svc.stop()
            elif not self.args.dry_run:
                self.log.info("Service '%s', task '%s' stopped already", svc.name,
                              svc.section_name)

        logging.debug("Terminating ZMQ context")
        # zmq.Context.instance().term()
        logging.shutdown()
    def terminate(self) -> t.NoReturn:
        "Terminate execution with exit code 1."
        try:
            self.shutdown()
        finally:
            sys.exit(1)

def main():
    "Main function"
    runner: Runner = Runner()
    runner.initialize()
    runner.prepare()
    runner.run()
    runner.shutdown()
