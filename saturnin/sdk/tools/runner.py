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

from typing import Dict, List, Optional
from uuid import UUID, uuid1
from os import getpid
from argparse import ArgumentParser
from threading import Thread, Event
from time import sleep
from pkg_resources import iter_entry_points
import zmq
from saturnin.sdk.types import PeerDescriptor, ServiceDescriptor, DependencyType
from saturnin.sdk.base import load
#from saturnin.sdk.classic import SimpleService, SimpleServiceImpl

__VERSION__ = '0.1'

def protocol_name(address: str) -> str:
    "Returns protocol name from address."
    return address.split(':', 1)[0].lower()

def get_best_endpoint(endpoints) -> Optional[str]:
    "Returns endpoint that uses the best protocol from available options."
    inproc = [x for x in endpoints if protocol_name(x) == 'inproc']
    if inproc:
        return inproc[0]
    ipc = [x for x in endpoints if protocol_name(x) == 'ipc']
    if ipc:
        return ipc[0]
    tcp = [x for x in endpoints if protocol_name(x) == 'tcp']
    return tcp[0]

class Service(Thread):
    "Classic Simple Butler Service executed in its own thread."
    def __init__(self, name: str, endpoints: List[str], svc_descriptor: ServiceDescriptor):
        super().__init__()
        self.uid = svc_descriptor.agent.uid
        self.name = name
        self.endpoints = endpoints
        self.svc_descriptor = svc_descriptor
        self.svc_implementation = load(svc_descriptor.implementation)
        self.svc_class = load(svc_descriptor.container)
        self.stop_event = Event()
        self.remotes: Dict[str, str] = {}
    def run(self):
        svc_impl = self.svc_implementation()
        svc_impl.endpoints = self.endpoints
        svc_impl.peer = PeerDescriptor(uuid1(), getpid(), 'localhost')
        svc = self.svc_class(svc_impl, self.stop_event)
        svc.start()

class Runner:
    """Service and test runner"""
    def __init__(self):
        self.services: Dict[UUID, Service] = {}
        self.port = 5000
        service_descriptors = (entry.load() for entry in iter_entry_points('saturnin.service'))
        self.service_registry = dict((sd.agent.uid, sd) for sd in service_descriptors)
        self.name_map = dict((sd.agent.name, sd) for sd in self.service_registry.values())
        self.remotes: Dict[str, List] = {}
        self.test = None
        self.ctx = zmq.Context.instance()
    def get_service_by_name(self, name: str) -> Service:
        """Returns service with specified name or None."""
        return self.services.get(self.name_map[name].agent.uid)
    def get_interface_provider(self, interface_uid: UUID) -> Optional[ServiceDescriptor]:
        """Returns descriptor of service that provides specified interface or None."""
        for svc_desc in self.service_registry.values():
            for intf in svc_desc.api:
                if intf == interface_uid:
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
                    endpoints.append(f'inproc://{service_name}')
                elif endpoint.lower() == 'ipc':
                    endpoints.append(f'ipc://{service_name}')
                elif endpoint.lower() == 'tcp':
                    endpoints.append(f'tcp://127.0.0.1:{self.port}')
                    self.port += 1
                else:
                    endpoints.append(endpoint)
            if not endpoints:
                endpoints.append(f'inproc://{service_name}')
            self.remotes[service_name] = endpoints
    def load_services(self, services: List):
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
                    endpoints.append(f'inproc://{service_name}')
                elif endpoint.lower() == 'ipc':
                    endpoints.append(f'ipc://{service_name}')
                elif endpoint.lower() == 'tcp':
                    endpoints.append(f'tcp://127.0.0.1:{self.port}')
                    self.port += 1
                else:
                    endpoints.append(endpoint)
            if not endpoints:
                endpoints.append(f'inproc://{service_name}')
            service = Service(service_name, endpoints, self.name_map[service_name])
            self.services[service.uid] = service
        # Check prerequisites
        for service in self.services.values():
            for dependency_type, interface_uid in service.svc_descriptor.dependencies:
                provider_desciptor = self.get_interface_provider(interface_uid)
                if provider_desciptor.agent.uid in self.services:
                    remote_service = self.services[provider_desciptor.agent.uid]
                    service.remotes[interface_uid] = get_best_endpoint(remote_service.endpoints)
                elif provider_desciptor.agent.name in self.remotes:
                    remote_endpoints = self.remotes[provider_desciptor.agent.name]
                    service.remotes[interface_uid] = get_best_endpoint(remote_endpoints)
                if (provider_desciptor is None and
                    dependency_type == DependencyType.REQUIRED):
                    raise Exception(f"Service '{service.name}' requires interface " \
                                    f"{interface_uid} that is not provided by any registered service.")
    def load_test(self, test_on: str):
        "Prepare tests."
        test_service = self.get_service_by_name(test_on)
        if not test_service:
            raise Exception(f"Test service '{test_on}' not specified by -s or -r option")
        try:
            test_class = load(test_service.svc_descriptor.tests)
        except Exception as exc:
            raise Exception(f"Can't load test runner for service '{test_on}'") from exc
        self.test = test_class(self.ctx)
    def start_services(self):
        """Start services."""
        for service in self.services.values():
            print(f"Starting '{service.name}' service...", end='')
            service.start()
            print("done.")
    def stop_services(self):
        """Stop services."""
        for service in self.services.values():
            print(f"Stopping '{service.name}' service...", end='')
            service.stop_event.set()
        #for service in self.services.values():
            service.join()
            print("done.")
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
        if raw:
            self.test.run_raw_tests(get_best_endpoint(test_service.endpoints))
        else:
            self.test.run_client_tests(get_best_endpoint(test_service.endpoints))



def main():
    "Main function"

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
    parser.set_defaults(raw=False)

    try:
        args = parser.parse_args()
        print(f"Saturnin Service/Test runner (classic version) v{__VERSION__}\n")
        if args.remote:
            runner.load_remote_services(args.remote)
        if args.service:
            runner.load_services(args.service)
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
    except Exception as exc:
        print(exc)
    print('Done.')

if __name__ == '__main__':
    main()
