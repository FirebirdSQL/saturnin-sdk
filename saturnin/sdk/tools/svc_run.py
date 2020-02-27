#coding:utf-8
#
# PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/tools/svc_run.py
# DESCRIPTION:    Saturnin SDK service runner (classic version)
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

"""Saturnin SDK service runner (classic version)

"""

import logging
import typing as t
import sys
from logging.config import fileConfig
from time import sleep
from argparse import ArgumentParser, Action, ArgumentDefaultsHelpFormatter, FileType, \
     Namespace
from configparser import ConfigParser, ExtendedInterpolation
from pkg_resources import iter_entry_points
from saturnin.core.types import StopError
from saturnin.core.config import UUIDOption
from saturnin.core.classic import ServiceBundleExecutor, SECTION_BUNDLE

__VERSION__ = '0.1'
"""Service runner version"""

LOG_FORMAT = '%(levelname)s: %(processName)s:%(threadName)s:%(name)s: %(message)s'
"""Format for log messages"""

# Functions

def title(text: str, size: int=80, char: str='='):
    """Returns centered title surrounded by char."""
    return f"  {text}  ".center(size, char)

#  Classes

class UpperAction(Action):
    """Converts argument to uppercase."""
    def __call__(self, parser, namespace, values, option_string=None):
        setattr(namespace, self.dest, values.upper())

class Runner:
    """Service runner.

.. program:: svc_run

usage::

    svc_run [-h] [--version] [-j [JOB [JOB ...]]] [-c FILE] [-o DIR]
                   [-t TEST [TEST ...]] [--dry-run] [-v] [-q] [--log-only]
                   [-l {critical,fatal,error,warn,warning,info,debug,notset}]
                   [--trace]

**optional arguments:**

.. option::  -h, --help

   show this help message and exit

.. option::  --version

   show program's version number and exit

**run arguments:**

.. option::  -j [JOB [JOB ...]], --job [JOB [JOB ...]]

    Job name (default: None)

.. option::  -c FILE, --config FILE

    Configuration file (default: svc_run.cfg)

.. option::  -o DIR, --output-dir DIR

    Force directory for log files and other output (default: ${here})

.. option::  --dry-run

    Prepare execution but do not run any service or test (default: False)

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
            ArgumentParser(prog='svc_run',
                           formatter_class=ArgumentDefaultsHelpFormatter,
                           description="Saturnin SDK service runner (classic version)")
        self.parser.add_argument('--version', action='version', version='%(prog)s '+__VERSION__)
        #
        group = self.parser.add_argument_group("run arguments")
        group.add_argument('-j', '--job', nargs='*', help="Job name")
        group.add_argument('-c', '--config', metavar='FILE',
                           type=FileType(mode='r', encoding='utf8'),
                           help="Configuration file")
        group.add_argument('-o', '--output-dir', metavar='DIR',
                           help="Force directory for log files and other output")
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
        group.add_argument('--trace', action='store_true',
                           help="Log unexpected errors with stack trace")
        self.parser.set_defaults(log_level='WARNING', config='svc_run.cfg',
                                 output_dir='${here}')
        #
        self.conf: ConfigParser = ConfigParser(interpolation=ExtendedInterpolation())
        self.opt_svc_uid: UUIDOption = UUIDOption('service_uid',
                                                  "Service UID (agent.uid in the Service Descriptor)",
                                                  required=True)
        self.args: Namespace = None
        self.config_filename: str = None
        self.log: logging.Logger = None
        self.executor = ServiceBundleExecutor()
    def verbose(self, *args, **kwargs) -> None:
        """Log verbose output, not propagated to upper loggers."""
        if self.args.verbose:
            self.log.debug(*args, **kwargs)
    def initialize(self) -> None:
        """Initialize runner from command line arguments and configuration file."""
        try:
            # Command-line arguments
            self.args = self.parser.parse_args()
            self.config_filename = self.args.config.name
            # Configuration
            self.executor.config.read_file(self.args.config)
            # Logging configuration
            if self.executor.config.has_section('loggers'):
                self.args.config.seek(0)
                fileConfig(self.args.config)
            else:
                logging.basicConfig(format=LOG_FORMAT)
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
            # Determine list of services to run in bundle
            svc_sections = []
            if self.args.job:
                for name in self.args.job:
                    if self.executor.config.has_section(name):
                        svc_sections.append(name)
                    elif self.executor.config.has_section(f'bundle_{name}'):
                        svc_sections.extend(v.strip() for v in
                                            self.executor.config.get(f'bundle_{name}',
                                                                     'services').split(','))
                    else:
                        raise StopError(f"Configuration does not have section "
                                        f"'{name}' or 'bundle_{name}'")
                if not self.executor.config.has_section(SECTION_BUNDLE):
                    self.executor.config.add_section(SECTION_BUNDLE)
                self.executor.config[SECTION_BUNDLE]['services'] = ','.join(svc_sections)
            elif not self.executor.config.has_section(SECTION_BUNDLE):
                raise StopError(f"Configuration does not have section '{SECTION_BUNDLE}'")
            self.args.config.close()
            # Load descriptors for registered services
            self.executor.available_services.extend(entry.load() for entry in
                                                    iter_entry_points('saturnin.service'))
            self.executor.initialize()
        except StopError as exc:
            self.log.error(str(exc))
            sys.exit(1)
    def run(self) -> None:
        """Run prepared services."""
        try:
            for svc in self.executor.service_instances:
                # print configuration
                self.verbose(title(f"Task '{svc.name}'", char='-'))
                self.verbose(f"service_uid = {svc.uid} [{svc.agent_name}]")
                for option in svc.config.options:
                    self.verbose(option.get_printout())
            if not self.args.dry_run:
                self.verbose(title("Starting services"))
                self.executor.start(self.log)
                self.verbose(title("Running", char='-'))
                try:
                    self.log.info("Press ^C to stop running services...")
                    while self.executor.service_instances:
                        self.executor.remove_finished(self.log)
                        sleep(1)
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
                self.log.exception('Unexpected error: %s', exc)
            else:
                self.log.error('Unexpected error: %s', exc)
            self.terminate()
    def shutdown(self) -> None:
        """Shut down the runner."""
        self.executor.stop(self.log)
        #logging.debug("Terminating ZMQ context")
        #zmq.Context.instance().term()
        logging.shutdown()
    def terminate(self) -> t.NoReturn:
        """Terminate execution with exit code 1."""
        try:
            self.shutdown()
        finally:
            sys.exit(1)

def main():
    """Main function"""
    runner: Runner = Runner()
    runner.initialize()
    runner.run()
    runner.shutdown()

