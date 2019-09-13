#coding:utf-8
#
#PROGRAM/MODULE: saturnin-sdk
# FILE:           saturnin/sdk/config.py
# DESCRIPTION:    Classes for configuration definitions
# CREATED:        27.8.2019
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

"Saturnin SDK - Classes for configuration definitions"

from typing import Dict, List, Any, Optional
from collections import OrderedDict
import configparser
from .types import SaturninError, TConfig, TConfigList, TStringList, TZMQAddress, TEnum, \
     TZMQAddressList, ZMQAddress, ExecutionMode

# Classes

class Option:
    """Configuration option (with string value).

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [default: None].
    :description: Option description. Can span multiple lines [default: empty str].
    :required:    True if option must have a value [default: False].
    :default:     Default value [default: None].
    :proposal:    Text with proposed configuration entry value (if it's different from default)
                  [default: None].
    :value:       Current option value.

Abstract methods:
    :load_from:     Update option value from ConfigParser.
    :_format_value: Return value formatted for option printout.
"""
    def __init__(self, name: str, datatype: Any = None, description: str = "",
                 required: bool = False, default: Any = None, proposal: Optional[str] = None):
        assert datatype is not None, "datatype required"
        self.name = name
        self.datatype = datatype
        self.description = description
        self.required = required
        self.default = default
        self.proposal = proposal
        self.value = default
    def _format_value(self, value: Any) -> str:
        """Return value formatted for option printout.

Arguments:
   :value: Value that is not None and has option datatype.
"""
        raise NotImplementedError
    def get_as_str(self):
        """Returns value as string suitable for reading."""
        return '<UNDEFINED>' if self.value is None else self._format_value(self.value)
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        raise NotImplementedError
    def validate(self) -> None:
        """Checks whether required option has value other than None.

Raises:
    :SaturninError: When required option does not have a value.
"""
        if self.required and self.value is None:
            raise SaturninError("The configuration does not define a value for the required option '%s'"
                                % (self.name))
    def get_printout(self) -> str:
        "Return option printout in 'name = value' format."
        return '%s = %s' % (self.name, self.get_as_str())

class StrOption(Option):
    """Configuration option with string value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [str].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: Optional[str] = None, proposal: Optional[str] = None):
        super().__init__(name, str, description, required, default, proposal)
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        result = value
        if '\n' in result:
            lines = []
            for line in result.splitlines(True):
                if lines:
                    lines.append('  ' + line)
                else:
                    lines.append(line)
            result = ''.join(lines)
        return result
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars, fallback=None)
        if value is not None:
            self.value = value

class IntOption(Option):
    """Configuration option with integer value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [int]
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: Optional[int] = None, proposal: Optional[str] = None):
        super().__init__(name, int, description, required, default, proposal)
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return str(value)
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.getint(section, self.name, vars=vars, fallback=None)
        if isinstance(value, int):
            self.value = value

class FloatOption(Option):
    """Configuration option with float value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [float].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: Optional[float] = None, proposal: Optional[str] = None):
        super().__init__(name, float, description, required, default, proposal)
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return str(value)
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.getfloat(section, self.name, vars=vars, fallback=None)
        if isinstance(value, float):
            self.value = value

class BoolOption(Option):
    """Configuration option with boolean value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [bool].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: Optional[bool] = None, proposal: Optional[str] = None):
        super().__init__(name, bool, description, required, default, proposal)
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return 'yes' if value else 'no'
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.getboolean(section, self.name, vars=vars, fallback=None)
        if isinstance(value, bool):
            self.value = value

class StrListOption(Option):
    """Configuration option with list of strings value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [List[str]].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: list, description: str, required: bool = False,
                 default: Optional[List[str]] = None, proposal: Optional[str] = None):
        super().__init__(name, TStringList, description, required, default, proposal)
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return ', '.join(value)
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars, fallback=None)
        if isinstance(value, str):
            self.value = [value.strip() for value in value.split(',')]
        elif value is not None:
            self.value = value

class ZMQAddressOption(Option):
    """Configuration option with ZMQAddress value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [TZMQAddress].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: list, description: str, required: bool = False,
                 default: Optional[TZMQAddress] = None, proposal: Optional[str] = None):
        super().__init__(name, TZMQAddress, description, required, default, proposal)
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return value
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars, fallback=None)
        if isinstance(value, str):
            self.value = ZMQAddress(value)
        elif value is not None:
            self.value = value

class ZMQAddressListOption(Option):
    """Configuration option with list of ZMQAddresses value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [TZMQAddressList].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: list, description: str, required: bool = False,
                 default: Optional[TZMQAddressList] = None, proposal: Optional[str] = None):
        super().__init__(name, TZMQAddressList, description, required, default, proposal)
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return ', '.join(value)
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars, fallback=None)
        if isinstance(value, str):
            self.value = [ZMQAddress(value.strip()) for value in value.split(',')]
        elif value is not None:
            self.value = value

class EnumOption(Option):
    """Configuration option with enum value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [int]
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: str, enum_class: TEnum, description: str, required: bool = False,
                 default: Optional[TEnum] = None, proposal: Optional[str] = None):
        super().__init__(name, int, description, required, default, proposal)
        self.enum_class = enum_class
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return value.name
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars, fallback=None)
        if isinstance(value, str):
            if value.isdigit():
                value = int(value)
                if value in self.enum_class._value2member_map_:
                    self.value = self.enum_class._value2member_map_[value]
                else:
                    raise ValueError("Illegal value '%s' for enum type '%s'" % (value,
                                                                                self.enum_class.__name__))
            else:
                value = value.upper()
                if value in self.enum_class._member_map_:
                    self.value = self.enum_class._member_map_[value]
                else:
                    raise ValueError("Illegal value '%s' for enum type '%s'" % (value,
                                                                                self.enum_class.__name__))
        elif value is not None:
            self.value = value

class ConfigOption(Option):
    """Configuration option with TConfig value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [TConfig].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
    :cfg_class:   Configuration class (TClass descendant).
"""
    def __init__(self, name: list, config_class: TConfig, description: str,
                 required: bool = False, default: Optional[TConfig] = None,
                 proposal: Optional[str] = None):
        super().__init__(name, TConfig, description, required, default, proposal)
        self.cfg_class = config_class
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return value.name
    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        section_name = config.get(section, self.name, vars=vars, fallback=None)
        if isinstance(section_name, str):
            self.value = self.cfg_class(section_name)
            self.value.load_from(config, section_name, vars)
        elif section_name is not None:
            self.value = section_name
    def validate(self) -> None:
        """Checks whether required option has value other than None. Also validates Config
options.

Raises:
    :SaturninError: When required option does not have a value.
"""
        super().validate()
        if self.value is not None:
            self.value.validate()

class ConfigListOption(Option):
    """Configuration option with list of TConfig value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [TConfigList].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
    :cfg_class:   Configuration class (TClass descendant).
"""
    def __init__(self, name: list, config_class: TConfig, description: str,
                 required: bool = False, default: Optional[TConfigList] = None,
                 proposal: Optional[str] = None):
        super().__init__(name, TConfigList, description, required, default, proposal)
        self.cfg_class = config_class
    def _format_value(self, value: Any) -> str:
        "Return value formatted for option printout."
        return ', '.join(cfg.name for cfg in value)

    def load_from(self, config: configparser.ConfigParser, section: str, vars: Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        section_names = config.get(section, self.name, vars=vars, fallback=None)
        if isinstance(section_names, str):
            self.value = []
            for section_name in (value.strip() for value in section_names.split(',')):
                cfg = self.cfg_class(section_name)
                cfg.load_from(config, section_name, vars)
                self.value.append(cfg)
        elif section_names is not None:
            self.value = section_names
    def validate(self) -> None:
        """Checks whether required option has value other than None. Also validates options
of all defined Configs.

Raises:
    :SaturninError: When required option does not have a value.
"""
        super().validate()
        if self.value is not None:
            for cfg in self.value:
                cfg.validate()

class Config:
    """Collection of configuration options.

Attributes:
    :name: Name associated with Collection (default section name).
    :description: Configuration description. Can span multiple lines.
"""
    def __init__(self, name: str, description: str):
        self.name: str = name
        self.description: str = description
        self.__options: Dict[str, ConfigOption] = OrderedDict()
    def __getattr__(self, name) -> Any:
        "Maps options to attributes."
        if name in self.__options:
            return self.__options[name].value
        raise AttributeError("Option '%s' not found." % name)
    def _add_option(self, option: ConfigOption) -> None:
        "Add configuration option."
        if option.name in self.options:
            raise SaturninError("Option '%s' already defined" % option.name)
        self.__options[option.name] = option
    def get_option(self, name: str) -> Option:
        """Returns Option with specified name.

Raises:
    :KeyError: If Config does not have option with specified name.
"""
        return self.__options[name]
    def load_from(self, config: configparser.ConfigParser, section: str) -> None:
        """Update configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
"""
        for option in self.__options.values():
            option.load_from(config, section)
    def validate(self) -> None:
        """Checks whether all required options have value other than None.

Raises:
    :Error: When required option does not have a value.
"""
        for option in self.__options.values():
            option.validate()
    def get_printout(self) -> List[str]:
        "Return list of text lines with printout of current configuration"
        lines = [option.get_printout() for option in self.options.values()]
        if self.name != 'main':
            lines.insert(0, "Configuration [%s]:" % self.name)
        return lines
    options = property(lambda self: self.__options,
                       doc="Options dictionary (name, ConfigOption).")

class MicroserviceConfig(Config):
    """Base Task (microservice) configuration.

Attributes:
    :name: Name associated with Collection [default: 'main'].

Configuration options:
    :execution_mode: Task execution mode.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self._add_option(EnumOption('execution_mode', ExecutionMode,
                                    "Task execution mode", default=ExecutionMode.THREAD))

class ServiceConfig(MicroserviceConfig):
    """Base Service configuration.

Attributes:
    :name: Name associated with Collection [default: 'main'].

Configuration options:
    :endpoints: Service endpoints.
    :execution_mode: Service execution mode.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self._add_option(ZMQAddressListOption('endpoints', "Service endpoints",
                                              required=True))

def get_config_lines(option: Option) -> List:
    """Returns list containing text lines suitable for use in configuration file processed
with ConfigParser.

Text lines with configuration start with comment marker ; and end with newline.
"""
    lines = ['; %s\n' % option.name,
             '; %s\n' % ('-' * len(option.name)),
             ';\n',
             '; data type: %s\n' % option.datatype.__name__,
             ';\n']
    if option.required:
        description = '[REQUIRED] ' + option.description
    else:
        description = '[optional] ' + option.description
    for line in description.split('\n'):
        lines.append("; %s\n" % line)
    lines.append(';\n')
    if option.proposal:
        lines.append(";%s = <UNDEFINED>, proposed value: %s\n" % (option.name, option.proposal))
    else:
        default = option._format_value(option.default) if option.default is not None else '<UNDEFINED>'
        lines.append(";%s = %s\n" % (option.name, default))
    return lines
