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

import typing as t
import uuid
from collections import OrderedDict
import configparser
from .types import Enum, ZMQAddress, ZMQAddressList, TStringList, ExecutionMode, \
     SaturninError
from google.protobuf.struct_pb2 import Struct, ListValue

# Types

TOnValidate = t.Callable[['Config'], None]

# Classes

class Option:
    """Configuration option (with string value).

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [Any].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value [default: False].
    :default:     Default value [default: None].
    :proposal:    Text with proposed configuration entry value (if it's different from default)
                  [default: None].
    :value:       Current option value.
"""
    def __init__(self, name: str, datatype: t.Type, description: str, required: bool = False,
                 default: t.Any = None, proposal: str = None):
        assert datatype is not None, "datatype required"
        assert default is None or isinstance(default, datatype)
        self.name: str = name
        self.datatype: t.Any = datatype
        self.description: str = description
        self.required: bool = required
        self.default: bool = default
        self.proposal: str = proposal
        self._value: t.Any = default
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    :value: New option value.

Raises:
    :TypeError: When the new value is of the wrong type.
"""
        if value is None:
            self.clear(False)
        else:
            if not isinstance(value, self.datatype):
                raise TypeError("Option '%s' value must be a '%s', not' %s'"
                                % (self.name, self.datatype.__name__, type(value).__name__))
            self._value = value
    def _format_value(self, value: t.Any) -> str:
        """Return value formatted for option printout. The default implemenetation returns
`str(value)`.

Arguments:
   :value: Value that is not None and has option datatype.
"""
        return str(value)
    def clear(self, to_default: bool = True) -> None:
        """Clears the option value.

Arguments:
    :to_default: If True, sets the option value to default value, else to None.
"""
        self._value = self.default if to_default else None
    def get_as_str(self):
        """Returns value as string suitable for reading."""
        return '<UNDEFINED>' if self.value is None else self._format_value(self.value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.set_value(value)
    def validate(self) -> None:
        """Validates option value.

Raises:
    :SaturninError: For incorrect option value.
"""
        if self.required and self.value is None:
            raise SaturninError("The configuration does not define a value for"\
                                " the required option '%s'" % self.name)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            self.set_value(proto[self.name])
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto[self.name] = self.value
    def get_printout(self) -> str:
        "Return option printout in 'name = value' format."
        return '%s = %s' % (self.name, self.get_as_str())
    value = property(lambda self: self._value, doc="Option value")

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
                 default: str = None, proposal: str = None):
        super().__init__(name, str, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
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
    value: str = property(lambda self: self._value, doc="Option value")

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
                 default: int = None, proposal: str = None):
        super().__init__(name, int, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return str(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        try:
            value = config.getint(section, self.name, vars=vars_, fallback=None)
        except ValueError as exc:
            raise TypeError("Option '%s' value must be a '%s'"
                            % (self.name, self.datatype.__name__)) from exc
        if value is not None:
            self.set_value(value)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, float):
                value = int(value)
            # We intentionally send value of wrong type to set_value() for error report
            self.set_value(value)
    value: int = property(lambda self: self._value, doc="Option value")

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
                 default: float = None, proposal: str = None):
        super().__init__(name, float, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return str(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        try:
            value = config.getfloat(section, self.name, vars=vars_, fallback=None)
        except ValueError as exc:
            raise TypeError("Option '%s' value must be a '%s'"
                            % (self.name, self.datatype.__name__)) from exc
        if value is not None:
            self.set_value(value)
    value: float = property(lambda self: self._value, doc="Option value")

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
                 default: bool = None, proposal: str = None):
        super().__init__(name, bool, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return 'yes' if value else 'no'
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        try:
            value = config.getboolean(section, self.name, vars=vars_, fallback=None)
        except ValueError as exc:
            raise TypeError("Option '%s' value must be a '%s'"
                            % (self.name, self.datatype.__name__)) from exc
        if value is not None:
            self.set_value(value)
    value: bool = property(lambda self: self._value, doc="Option value")

class StrListOption(Option):
    """Configuration option with list of strings value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [TStringList].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: list, description: str, required: bool = False,
                 default: TStringList = None, proposal: str = None):
        super().__init__(name, list, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return ', '.join(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            if value.strip():
                self.set_value([value.strip() for value in value.split(',')])
            else:
                self.set_value([])
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, ListValue):
                self.set_value(list(value))
            else:
                raise TypeError("Option '%s' value must be a '%s', not' %s'"
                                % (self.name, self.datatype.__name__,
                                   type(value).__name__))
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto.get_or_create_list(self.name).extend(self.value)
    value: TStringList = property(lambda self: self._value, doc="Option value")

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
                 default: ZMQAddress = None, proposal: str = None):
        super().__init__(name, ZMQAddress, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return value
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.set_value(ZMQAddress(value))
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            self.set_value(ZMQAddress(proto[self.name]))
    value: ZMQAddress = property(lambda self: self._value, doc="Option value")

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
                 default: ZMQAddressList = None, proposal: str = None):
        super().__init__(name, list, description, required, default, proposal)
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return ', '.join(value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            if value.strip():
                self.set_value([ZMQAddress(value.strip()) for value in value.split(',')])
            else:
                self.set_value([])
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, ListValue):
                self.set_value([ZMQAddress(addr) for addr in value])
            else:
                raise TypeError("Option '%s' value must be a '%s', not' %s'"
                                % (self.name, self.datatype.__name__,
                                   type(value).__name__))
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto.get_or_create_list(self.name).extend(self.value)
    value: ZMQAddressList = property(lambda self: self._value, doc="Option value")

class EnumOption(Option):
    """Configuration option with enum value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [Enum]
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :options:     List of allowed enum values.
    :value:       Current option value.
"""
    def __init__(self, name: str, enum_class: t.Type[Enum], description: str, required: bool = False,
                 default: Enum = None, proposal: str = None, options: t.List = None):
        super().__init__(name, enum_class, description, required, default, proposal)
        self.options: t.Iterable = enum_class if options is None else options
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return value.name
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    :value: New option value.

Raises:
    :TypeError: When the new value is of the wrong type.
    :ValueError: When the new value is not allowed.
"""
        if value is None:
            self.clear(False)
        else:
            if not isinstance(value, self.datatype):
                raise TypeError("Option '%s' value must be a '%s', not' %s'"
                                % (self.name, self.datatype.__name__, type(value).__name__))
            if value not in self.options:
                raise ValueError("Value '%s' not allowed for option '%s'"
                                 % (self.value, self.name))
            self._value = value
    def __fromstr(self, value: str):
        if value.isdigit():
            value = int(value)
            if value in t.cast(t.Type[Enum], self.datatype).get_value_map():
                self.set_value(t.cast(t.Type[Enum], self.datatype).get_value_map()[value])
            else:
                raise ValueError("Illegal value '%s' for enum type '%s'"
                                 % (value, self.datatype.__name__))
        else:
            value = value.upper()
            if value in t.cast(t.Type[Enum], self.datatype).get_member_map():
                self.set_value(t.cast(t.Type[Enum], self.datatype).get_member_map()[value])
            else:
                raise ValueError("Illegal value '%s' for enum type '%s'"
                                 % (value, self.datatype.__name__))
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.__fromstr(value)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, str):
                self.__fromstr(value)
            else:
                self.set_value(self.datatype(value))
    value: Enum = property(lambda self: self._value, doc="Option value")

class UUIDOption(Option):
    """Configuration option with UUID value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [uuid.UUID].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: uuid.UUID = None, proposal: str = None):
        super().__init__(name, uuid.UUID, description, required, default, proposal)
        self._value: uuid.UUID = default
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return str(self.value)
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        value = config.get(section, self.name, vars=vars_, fallback=None)
        if value is not None:
            self.set_value(uuid.UUID(value))
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            value = proto[self.name]
            if isinstance(value, str):
                value = uuid.UUID(value)
            self.set_value(value)
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto[self.name] = self.value.hex
    value: uuid.UUID = property(lambda self: self._value, doc="Option value")

class MIMEOption(Option):
    """Configuration option with MIME type specification value.

Attributes:
    :name:        Option name.
    :datatype:    Option datatype [str].
    :description: Option description. Can span multiple lines.
    :required:    True if option must have a value.
    :default:     Default value.
    :proposal:    Text with proposed configuration entry (if it's different from default).
    :value:       Current option value.
    :mime_type:   MIME type specification 'type/subtype'
    :mime_params: MIME type parameters
"""
    def __init__(self, name: str, description: str, required: bool = False,
                 default: str = None, proposal: str = None):
        super().__init__(name, str, description, required, default, proposal)
        self.__mime_type: str = None
        self.__mime_params: t.Dict[str, str] = {}
        self.__parse_value(self._value)
    def __parse_value(self, value: str) -> None:
        if value is None:
            self.__mime_type = None
            self.__mime_params.clear()
        else:
            dfm = [x.strip() for x in value.split(';')]
            mime_type: str = dfm.pop(0).lower()
            try:
                main, subtype = mime_type.split('/')
            except:
                raise ValueError("MIME type specification must be 'type/subtype[;param=value;...]'")
            if main not in ['text', 'image', 'audio', 'video', 'application', 'multipart', 'message']:
                raise ValueError("MIME type '%s' not supported" % main)
            try:
                mime_params = dict((k.strip(), v.strip()) for k, v
                                                in (x.split('=') for x in dfm))
            except:
                raise ValueError("Wrong specification of MIME type parameters")
            self.__mime_type = mime_type
            self.__mime_params = mime_params
    def clear(self, to_default: bool = True) -> None:
        """Clears the option value.

Arguments:
    :to_default: If True, sets the option value to default value, else to None.
"""
        value = self.default if to_default else None
        self.__parse_value(value)
        self._value = value
    def set_value(self, value: t.Any) -> None:
        """Set new option value.

Arguments:
    :value: New option value.

Raises:
    :TypeError:  When the new value is of the wrong type.
    :ValueError: When the new value is not allowed.
"""
        if value is None:
            self.clear(False)
        else:
            if not isinstance(value, self.datatype):
                raise TypeError("Option '%s' value must be a '%s', not' %s'"
                                % (self.name, self.datatype.__name__, type(value).__name__))
            self.__parse_value(value)
            self._value = value
    value: str = property(lambda self: self._value, doc="Option value")
    mime_type: str = property(lambda self: self.__mime_type, doc="MIME type/subtype")
    mime_params: t.ItemsView[str, str] = property(lambda self: self.__mime_params.items(),
                                                   doc="MIME type/subtype")

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
"""
    def __init__(self, name: str, config_class: t.Type['Config'], description: str,
                 required: bool = False, proposal: str = None,
                 on_validate: TOnValidate = None):
        super().__init__(name, config_class, description, required, proposal=proposal)
        self._value: Config = None
        self.__on_validate = on_validate
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return value.name
    def validate(self) -> None:
        """Checks whether required option has value other than None. Also validates Config
options.

Raises:
    :SaturninError: When required option does not have a value.
"""
        super().validate()
        if self.value is not None:
            self.value.validate()
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        section_name = config.get(section, self.name, vars=vars_, fallback=None)
        if isinstance(section_name, str):
            self.value = self.datatype(section_name, self.description)
            self.value.on_validate = self.__on_validate
            self.value.load_from(config, section_name, vars_)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            self.value = self.datatype('%s_value' % self.name, self.description)
            self.value.on_validate = self.__on_validate
            self.value.load_proto(proto.get_or_create_struct(self.name))
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.value is not None:
            self.value.save_proto(proto.get_or_create_struct(self.name))

class ConfigListOption(Option):
    """Configuration option with list of TConfig value.

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
    def __init__(self, name: str, config_class: t.Type['Config'], description: str,
                 required: bool = False, proposal: str = None,
                 on_validate: TOnValidate = None):
        super().__init__(name, config_class, description, required, proposal=proposal)
        self._value: t.List['Config'] = None
        self.__on_validate = on_validate
    def _format_value(self, value: t.Any) -> str:
        "Return value formatted for option printout."
        return ', '.join(cfg.name for cfg in value)
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
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update option value from configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
    :vars_:    Dict[option_name, option_value] with values that takes precedence over configuration.
"""
        section_names = config.get(section, self.name, vars=vars_, fallback=None)
        if isinstance(section_names, str):
            self.value = []
            for section_name in (value.strip() for value in section_names.split(',')):
                cfg: Config = self.datatype(section_name, self.description)
                cfg.on_validate = self.__on_validate
                cfg.load_from(config, section_name, vars_)
                self.value.append(cfg)
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.name in proto:
            i = 1
            for cfg_proto in proto[self.name]:
                cfg: Config = self.datatype('%s_value_%s' % (self.name, i), self.description)
                cfg.on_validate = self.__on_validate
                cfg.load_proto(cfg_proto)
                self.value.append(cfg)
                i += 1
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        if self.value is not None:
            proto_list = proto.get_or_create_list(self.name)
            for cfg in self.value:
                cfg.save_proto(proto_list.add_struct())

class Config:
    """Collection of configuration options.

Attributes:
    :name: Name associated with Collection (default section name).
    :description: Configuration description. Can span multiple lines.
    :on_validate: Event(Config) called by `validate()` after all options are validated.
    :<option_name>: Defined options are directly accessible as instance attaributes.
"""
    def __init__(self, name: str, description: str):
        self.name: str = name
        self.description: str = description
        self.__options: t.Dict[str, Option] = OrderedDict()
    def add_option(self, option: ConfigOption) -> Option:
        "Add configuration option."
        if option.name in self.options:
            raise SaturninError("Option '%s' already defined" % option.name)
        self.__options[option.name] = option
        return option
    def validate(self) -> None:
        """Checks whether all required options have value other than None.

Raises:
    :Error: When required option does not have a value.
"""
        for option in self.__options.values():
            option.validate()
        #if self.on_validate:
            #self.on_validate(self)
    def clear(self) -> None:
        "Clears all option values."
        for option in self.__options.values():
            option.clear()
    def load_from(self, config: configparser.ConfigParser, section: str,
                  vars_: t.Dict = None) -> None:
        """Update configuration.

Arguments:
    :config:  ConfigParser instance with configuration values.
    :section: Name of ConfigParser section that should be used to get new configuration values.
"""
        try:
            for option in self.__options.values():
                option.load_from(config, section, vars_)
        except Exception as exc:
            raise SaturninError("Configuration error: %s" % exc) from exc
    def load_proto(self, proto: Struct):
        """Deserialize value from `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        for option in self.__options.values():
            option.load_proto(proto)
    def save_proto(self, proto: Struct):
        """Serialize value into `protobuf.Struct` message.

Arguments:
    :proto: protobuf `Struct` message.
"""
        for option in self.__options.values():
            option.save_proto(proto)
    def get_printout(self) -> t.List[str]:
        "Return list of text lines with printout of current configuration"
        lines = [option.get_printout() for option in self.options.values()]
        if self.name != 'main':
            lines.insert(0, "Configuration [%s]:" % self.name)
        return lines
    options: t.Dict[str, Option] = property(lambda self: self.__options,
                                            doc="Options Dict[name, Option].")

class MicroserviceConfig(Config):
    """Base Task (microservice) configuration.

Attributes:
    :name: Name associated with Collection [default: 'main'].

Configuration options:
    :execution_mode: Task execution mode.
"""
    def __init__(self, name: str, description: str):
        super().__init__(name, description)
        self.execution_mode: EnumOption = \
            self.add_option(EnumOption('execution_mode', ExecutionMode,
                                       "Task execution mode",
                                       default=ExecutionMode.THREAD))

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
        self.endpoints: ZMQAddressListOption = \
            self.add_option(ZMQAddressListOption('endpoints', "Service endpoints",
                                                 required=True))

def create_config(_cls: t.Type[Config], name: str, description: str) -> Config:
    """Return newly created Config in stance. Intended to be used with `functools.partial`
in `ServiceDescriptor.config` definitions.
"""
    return _cls(name, description)

def get_config_lines(option: Option) -> t.List:
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
        default = (option._format_value(option.default) if option.default is not None
                   else '<UNDEFINED>')
        lines.append(";%s = %s\n" % (option.name, default))
    return lines
