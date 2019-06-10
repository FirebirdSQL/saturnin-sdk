#!/usr/bin/python
#coding:utf-8
#
# PROGRAM/MODULE: Saturnin SDK examples
# FILE:           runner.py
# DESCRIPTION:    Saturnin service and test runner (classic version)
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

"""Saturnin service and test runner (classic version)

"""

from traceback import print_exc
import logging
from typing import Dict, List, Optional
from uuid import UUID, uuid1
from os import getpid
from socket import getfqdn
import platform
from argparse import ArgumentParser, Action
import multiprocessing
import threading
from time import sleep
from pkg_resources import iter_entry_points
import zmq
from saturnin.sdk.types import PeerDescriptor, ServiceDescriptor, DependencyType, \
     ExecutionMode, AddressDomain, ZMQAddress
from saturnin.sdk.base import load

__VERSION__ = '0.1'

# Functions

def protocol_name(address: str) -> str:
    "Returns protocol name from address."
    return address.split(':', 1)[0].lower()

def get_best_endpoint(endpoints: List[ZMQAddress], client_mode=ExecutionMode.PROCESS,
                      service_mode=ExecutionMode.PROCESS) -> Optional[ZMQAddress]:
    "Returns endpoint that uses the best protocol from available options."
    local_addr = [x for x in endpoints if x.domain == AddressDomain.LOCAL]
    if (local_addr and client_mode == ExecutionMode.THREAD and service_mode == ExecutionMode.THREAD):
        return local_addr[0]
    node_addr = [x for x in endpoints if x.domain == AddressDomain.NODE]
    if node_addr:
        return node_addr[0]
    net_addr = [x for x in endpoints if x.domain == AddressDomain.NETWORK]
    return net_addr[0]

def service_run(endpoints, svc_descriptor, ready_event, stop_event, remotes):
    "Process or thread target code to run the service."
    svc_implementation = load(svc_descriptor.implementation)
    svc_class = load(svc_descriptor.container)
    svc_impl = svc_implementation(stop_event)
    svc_impl.endpoints = endpoints
    svc_impl.peer = PeerDescriptor(uuid1(), getpid(), getfqdn())
    svc = svc_class(svc_impl)
    svc.remotes = remotes.copy()
    #svc.remotes = dict((key, ZMQAddress(e)) for key, e in remotes.items())
    svc.initialize()
    ready_event.set()
    svc.start()

#  Classes

class UpperAction(Action):
    "Converts argument to uppercase."
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.upper())

class Service:
    "Service handler."
    def __init__(self, name: str, endpoints: List[str], svc_descriptor: ServiceDescriptor,
                 mode: ExecutionMode = ExecutionMode.ANY):
        self.uid = svc_descriptor.agent.uid
        self.name = name
        self.endpoints = endpoints
        self.svc_descriptor = svc_descriptor
        if mode != ExecutionMode.ANY:
            self.mode = mode
        elif svc_descriptor.execution_mode != ExecutionMode.ANY:
            self.mode = svc_descriptor.execution_mode
        else:
            self.mode = ExecutionMode.THREAD
        self.remotes: Dict[bytes, ZMQAddress] = {}
        if self.mode in (ExecutionMode.ANY, ExecutionMode.THREAD):
            self.ready_event = threading.Event()
            self.stop_event = threading.Event()
            self.runtime = threading.Thread(target=service_run, name=name,
                                            args=(endpoints, svc_descriptor,
                                                  self.ready_event, self.stop_event,
                                                  self.remotes))
        else:
            self.ready_event = multiprocessing.Event()
            self.stop_event = multiprocessing.Event()
            self.runtime = multiprocessing.Process(target=service_run, name=name,
                                                   args=(endpoints, svc_descriptor,
                                                         self.ready_event, self.stop_event,
                                                         self.remotes))

class Runner:
    """Service and test runner"""
    def __init__(self):
        self.services: Dict[UUID, Service] = {}
        self.port = 5000
        service_descriptors = (entry.load() for entry in iter_entry_points('saturnin.service'))
        self.service_registry = dict((sd.agent.uid, sd) for sd in service_descriptors)
        self.name_map = dict((sd.agent.name, sd) for sd in self.service_registry.values())
        self.remote_services: Dict[str, List] = {}
        self.test = None
        self.ctx = zmq.Context.instance()
    def get_service_by_name(self, name: str) -> Service:
        """Returns service with specified name or None."""
        return self.services.get(self.name_map[name].agent.uid)
    def get_interface_provider(self, interface_uid: UUID) -> Optional[ServiceDescriptor]:
        """Returns descriptor of service that provides specified interface or None."""
        for svc_desc in self.service_registry.values():
            for intf in svc_desc.api:
                if intf.uid == interface_uid:
                    return svc_desc
        return None
    def load_remote_services(self, remote_services: List):
        "Prepare remote services."
        for service_spec in remote_services:
            service_name = service_spec.pop(0)
            endpoints = []
            for endpoint in service_spec:
                if protocol_name(endpoint) not in ['inproc', 'ipc', 'tcp']:
                    raise Exception(f"Unsupported protocol, endpoint '{endpoint}'")
                if endpoint.lower() == 'inproc':
                    endpoints.append(ZMQAddress(f'inproc://{service_name}'))
                elif endpoint.lower() == 'ipc':
                    endpoints.append(ZMQAddress(f'ipc://{service_name}'))
                elif endpoint.lower() == 'tcp':
                    endpoints.append(ZMQAddress(f'tcp://127.0.0.1:{self.port}'))
                    self.port += 1
                else:
                    endpoints.append(ZMQAddress(endpoint))
            if not endpoints:
                endpoints.append(ZMQAddress(f'inproc://{service_name}'))
            self.remote_services[service_name] = endpoints
    def load_services(self, services: List, in_thread: Optional[List],
                      in_process: Optional[List]):
        "Prepare services for running."
        for service_spec in services:
            service_name = service_spec.pop(0)
            endpoints = []
            if service_name not in self.name_map:
                raise Exception(f"Service '{service_name}' not registered")
            for endpoint in service_spec:
                if protocol_name(endpoint) not in ['inproc', 'ipc', 'tcp']:
                    raise Exception(f"Unsupported protocol, endpoint '{endpoint}'")
                if endpoint.lower() == 'inproc':
                    endpoints.append(ZMQAddress(f'inproc://{service_name}'))
                elif endpoint.lower() == 'ipc':
                    endpoints.append(ZMQAddress(f'ipc://@{service_name}'))
                elif endpoint.lower() == 'tcp':
                    endpoints.append(ZMQAddress(f'tcp://127.0.0.1:{self.port}'))
                    self.port += 1
                else:
                    endpoints.append(ZMQAddress(endpoint))
            if not endpoints:
                endpoints.append(ZMQAddress(f'inproc://{service_name}'))
                if platform.system() == 'Linux':
                    endpoints.append(ZMQAddress(f'ipc://@{service_name}'))
                endpoints.append(ZMQAddress(f'tcp://127.0.0.1:{self.port}'))
                self.port += 1
            mode = ExecutionMode.ANY
            if in_thread is not None:
                if not in_thread or service_name in in_thread:
                    mode = ExecutionMode.THREAD
            if in_process is not None:
                if not in_process or service_name in in_process:
                    mode = ExecutionMode.PROCESS
            service = Service(service_name, endpoints, self.name_map[service_name], mode)
            self.services[service.uid] = service
        # Check prerequisites
        for service in self.services.values():
            for dependency_type, interface_uid in service.svc_descriptor.dependencies:
                provider_desciptor = self.get_interface_provider(interface_uid)
                if provider_desciptor is not None:
                    if provider_desciptor.agent.uid in self.services:
                        remote_service = self.services[provider_desciptor.agent.uid]
                        service.remotes[interface_uid.bytes] = \
                            get_best_endpoint(remote_service.endpoints, service.mode,
                                              remote_service.mode)
                    elif provider_desciptor.agent.name in self.remote_services:
                        remote_endpoints = self.remote_services[provider_desciptor.agent.name]
                        service.remotes[interface_uid.bytes] = get_best_endpoint(remote_endpoints)
                if (provider_desciptor is None and dependency_type == DependencyType.REQUIRED):
                    raise Exception(f"Service '{service.name}' requires interface " \
                                    f"{interface_uid} that is not provided by any service.")
    def load_test(self, test_on: str):
        "Prepare tests."
        service_descriptor = None
        test_service = self.get_service_by_name(test_on)
        if test_service:
            service_descriptor = test_service.svc_descriptor
        else:
            if test_on in self.remote_services:
                service_descriptor = self.name_map[test_on]
        if not service_descriptor:
            raise Exception(f"Test service '{test_on}' not specified by -s or -r option")
        try:
            test_class = load(service_descriptor.tests)
        except Exception as exc:
            raise Exception(f"Can't load test runner for service '{test_on}'") from exc
        self.test = test_class(self.ctx)
    def start_services(self):
        """Start services."""
        for service in self.services.values():
            print("Starting '%s' service %s with endpoints: %s" % (service.name,
                                                                   service.mode.name.lower(),
                                                                   ', '.join(str(e) for e
                                                                             in service.endpoints)))
            service.runtime.start()
            if not service.ready_event.wait(5):
                raise Exception(f"The service {service.name} did not start in time.")
    def stop_services(self):
        """Stop services."""
        for service in self.services.values():
            print(f"Stopping '{service.name}' service {service.mode.name.lower()}.")
            service.stop_event.set()
        for service in self.services.values():
            if service.runtime.is_alive():
                service.runtime.join()
    def shutdown(self):
        "Stops the runner."
        self.stop_services()
        self.ctx.term()
        print("Shutdown complete.")
    def run_test(self, service_name: str, raw: bool):
        "Run tests."
        test_type = 'raw' if raw else 'client'
        print(f"Running {test_type} tests on '{service_name}' service")
        test_service = self.get_service_by_name(service_name)
        if test_service:
            endpoint = get_best_endpoint(test_service.endpoints, ExecutionMode.THREAD,
                                         test_service.mode)
        else:
            endpoint = get_best_endpoint(self.remote_services[service_name])
        if raw:
            self.test.run_raw_tests(endpoint)
        else:
            self.test.run_client_tests(endpoint)

def main():
    "Main function"

    logging.basicConfig(format='%(levelname)s:%(threadName)s:%(name)s:%(message)s')
    #logging.basicConfig()

    multiprocessing.set_start_method('spawn')

    runner = Runner()

    description = """Saturnin service and test runner"""
    parser = ArgumentParser(description=description)
    parser.add_argument('-s', '--service', nargs='+', action='append', type=str,
                        help="Service specification. Could be repeated.")
    parser.add_argument('-r', '--remote', nargs='+', action='append', type=str,
                        help="Remote service specification. Could be repeated.")
    parser.add_argument('-t', '--test', type=str,
                        help="Name of service to be tested.")
    parser.add_argument('--raw', action='store_true',
                        help="Execute raw ZMQ test.")
    parser.add_argument('--thread', nargs='*', metavar='SERVICE_NAME',
                        help="Execute all (or listed) services in separate threads.")
    parser.add_argument('--process', nargs='*', metavar='SERVICE_NAME',
                        help="Execute all (or listed) services in separate process.")
    parser.add_argument('-l', '--log-level', action=UpperAction,
                        choices=[x.lower() for x in logging._nameToLevel
                                 if isinstance(x, str)],
                        help="Logging level")
    parser.set_defaults(raw=False, log_level='ERROR', thread=None, process=None)

    try:
        args = parser.parse_args()
        print(f"Saturnin Service/Test runner (classic version) v{__VERSION__}\n")
        logger = logging.getLogger()
        logger.setLevel(args.log_level)
        if args.remote:
            runner.load_remote_services(args.remote)
        if args.service:
            runner.load_services(args.service, args.thread, args.process)
        if args.test:
            runner.load_test(args.test)
        try:
            runner.start_services()
            if args.test:
                runner.run_test(args.test, args.raw)
            else:
                print("Press ^C to stop running services...")
                while True:
                    sleep(1)
        except KeyboardInterrupt:
            print("\nTerminating on user request...")
        finally:
            runner.shutdown()
    except Exception:
        print_exc()
    logging.shutdown()
    print('Done.')

if __name__ == '__main__':
    main()
