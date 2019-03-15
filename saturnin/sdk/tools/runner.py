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
from uuid import UUID
from argparse import ArgumentParser
from threading import Thread, Event
from time import sleep
from pkg_resources import iter_entry_points
import zmq
from saturnin.sdk.classic import SimpleService, SimpleServiceImpl

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
    def __init__(self, name: str, endpoints: List[str], service_class: SimpleServiceImpl):
        super().__init__()
        self.name = name
        self.endpoints = endpoints
        self.service_class = service_class
        self.stop_event = Event()
        self.remotes: Dict[str, str] = {}
    def run(self):
        svc = SimpleService(self.service_class(self.stop_event, self.endpoints, self.remotes))
        svc.start()

class Runner: # pylint: disable=R0902
    """Service and test runner"""
    def __init__(self):
        self.services: Dict[str, Service] = {}
        self.port = 5000
        self.service_registry = dict((entry.name, entry) for entry
                                     in iter_entry_points('saturnin.service'))
        self.service_uids = dict((entry.load(), entry.name) for entry
                                 in iter_entry_points('saturnin.service.uid'))
        self.test_registry = dict((entry.name, entry) for entry
                                  in iter_entry_points('saturnin.test'))
        self.remotes: Dict[str, List] = {}
        self.test = None
        self.ctx = zmq.Context.instance()
    def get_service_name(self, service_uid: UUID) -> str:
        """Returns name of service with specified UID or None."""
        return self.service_uids.get(service_uid)
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
    def load_services(self, services: List): # pylint: disable=R0912
        "Prepare services for running."
        for service_spec in services:
            service_name = service_spec.pop(0)
            endpoints = []
            if service_name not in self.service_registry:
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
            try:
                service_class = self.service_registry[service_name].load()
            except Exception as exc:
                raise Exception(f"Can't load service '{service_name}'") from exc
            service = Service(service_name, endpoints, service_class)
            self.services[service.name] = service
        # Check prerequisites
        for service in self.services.values():
            for requires in service.service_class.REQUIRES:
                svc_name = self.get_service_name(requires)
                if requires in self.services:
                    remote_service = self.services[self.get_service_name(requires)]
                    service.remotes[requires] = get_best_endpoint(remote_service.endpoints)
                elif requires not in self.remotes:
                    remote_endpoints = self.remotes[requires]
                    service.remotes[requires] = get_best_endpoint(remote_endpoints)
                else:
                    raise Exception(f"Service '{service.name}' requires unavailable service '{requires}'")
            for optional in service.service_class.OPTIONAL:
                svc_name = self.get_service_name(optional)
                if svc_name in self.services:
                    service.remotes[optional] = get_best_endpoint(self.services[svc_name].endpoints)
                elif svc_name in self.remotes:
                    remote_endpoints = self.remotes[svc_name]
                    service.remotes[optional] = get_best_endpoint(remote_endpoints)
    def load_test(self, test_on: str):
        "Prepare tests."
        test_service = self.services.get(test_on)
        if not test_service:
            raise Exception(f"Test service '{test_on}' not specified by -s or -r option")
        if test_on not in self.test_registry:
            raise Exception(f"Tests for service '{test_on}' not registered")
        try:
            test_class = self.test_registry[test_on].load()
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
        test_service = self.services.get(service_name)
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
    except Exception as exc: # pylint: disable=W0703
        print(exc)
    print('Done.')

if __name__ == '__main__':
    main()
