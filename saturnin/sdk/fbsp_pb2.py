# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: fbsp.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf.internal import enum_type_wrapper
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import any_pb2 as google_dot_protobuf_dot_any__pb2
from google.protobuf import struct_pb2 as google_dot_protobuf_dot_struct__pb2


DESCRIPTOR = _descriptor.FileDescriptor(
  name='fbsp.proto',
  package='firebird.butler',
  syntax='proto3',
  serialized_pb=_b('\n\nfbsp.proto\x12\x0f\x66irebird.butler\x1a\x19google/protobuf/any.proto\x1a\x1cgoogle/protobuf/struct.proto\"*\n\nPlatformId\x12\x0b\n\x03uid\x18\x01 \x01(\x0c\x12\x0f\n\x07version\x18\x02 \x01(\t\"\x17\n\x08VendorId\x12\x0b\n\x03uid\x18\x01 \x01(\x0c\"\xdd\x01\n\x13\x41gentIdentification\x12\x0b\n\x03uid\x18\x01 \x01(\x0c\x12\x0c\n\x04name\x18\x02 \x01(\t\x12\x0f\n\x07version\x18\x03 \x01(\t\x12)\n\x06vendor\x18\x04 \x01(\x0b\x32\x19.firebird.butler.VendorId\x12-\n\x08platform\x18\x05 \x01(\x0b\x32\x1b.firebird.butler.PlatformId\x12\x16\n\x0e\x63lassification\x18\x06 \x01(\t\x12(\n\nsupplement\x18\x07 \x03(\x0b\x32\x14.google.protobuf.Any\"f\n\x12PeerIdentification\x12\x0b\n\x03uid\x18\x01 \x01(\x0c\x12\x0b\n\x03pid\x18\x02 \x01(\r\x12\x0c\n\x04host\x18\x03 \x01(\t\x12(\n\nsupplement\x18\x04 \x03(\x0b\x32\x14.google.protobuf.Any\",\n\rInterfaceSpec\x12\x0e\n\x06number\x18\x01 \x01(\r\x12\x0b\n\x03uid\x18\x02 \x01(\x0c\"\x8c\x01\n\x10\x45rrorDescription\x12\x0c\n\x04\x63ode\x18\x01 \x01(\x04\x12\x13\n\x0b\x64\x65scription\x18\x02 \x01(\t\x12(\n\x07\x63ontext\x18\x03 \x01(\x0b\x32\x17.google.protobuf.Struct\x12+\n\nannotation\x18\x04 \x01(\x0b\x32\x17.google.protobuf.Struct\"\xa7\x01\n\x0eHelloDataframe\x12\x35\n\x08instance\x18\x01 \x01(\x0b\x32#.firebird.butler.PeerIdentification\x12\x34\n\x06\x63lient\x18\x02 \x01(\x0b\x32$.firebird.butler.AgentIdentification\x12(\n\nsupplement\x18\x03 \x03(\x0b\x32\x14.google.protobuf.Any\"\xd7\x01\n\x10WelcomeDataframe\x12\x35\n\x08instance\x18\x01 \x01(\x0b\x32#.firebird.butler.PeerIdentification\x12\x35\n\x07service\x18\x02 \x01(\x0b\x32$.firebird.butler.AgentIdentification\x12+\n\x03\x61pi\x18\x03 \x03(\x0b\x32\x1e.firebird.butler.InterfaceSpec\x12(\n\nsupplement\x18\x04 \x03(\x0b\x32\x14.google.protobuf.Any\"I\n\x0e\x43\x61ncelRequests\x12\r\n\x05token\x18\x01 \x01(\x0c\x12(\n\nsupplement\x18\x02 \x03(\x0b\x32\x14.google.protobuf.Any\"c\n\x10StateInformation\x12%\n\x05state\x18\x01 \x01(\x0e\x32\x16.firebird.butler.State\x12(\n\nsupplement\x18\x02 \x03(\x0b\x32\x14.google.protobuf.Any*\x8e\x01\n\x05State\x12\x0b\n\x07UNKNOWN\x10\x00\x12\t\n\x05READY\x10\x01\x12\x0b\n\x07RUNNING\x10\x02\x12\x0b\n\x07WAITING\x10\x03\x12\r\n\tSUSPENDED\x10\x04\x12\x0c\n\x08\x46INISHED\x10\x05\x12\x0b\n\x07\x41\x42ORTED\x10\x06\x12\x0b\n\x07\x43REATED\x10\x01\x12\x0b\n\x07\x42LOCKED\x10\x03\x12\x0b\n\x07STOPPED\x10\x04\x1a\x02\x10\x01\x42?\n\x13org.firebird.butlerB\tFBSPProtoP\x01\xa2\x02\x03\x46PB\xaa\x02\x14\x46irebird.Butler.FBSPb\x06proto3')
  ,
  dependencies=[google_dot_protobuf_dot_any__pb2.DESCRIPTOR,google_dot_protobuf_dot_struct__pb2.DESCRIPTOR,])

_STATE = _descriptor.EnumDescriptor(
  name='State',
  full_name='firebird.butler.State',
  filename=None,
  file=DESCRIPTOR,
  values=[
    _descriptor.EnumValueDescriptor(
      name='UNKNOWN', index=0, number=0,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='READY', index=1, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='RUNNING', index=2, number=2,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='WAITING', index=3, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='SUSPENDED', index=4, number=4,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='FINISHED', index=5, number=5,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='ABORTED', index=6, number=6,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='CREATED', index=7, number=1,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='BLOCKED', index=8, number=3,
      options=None,
      type=None),
    _descriptor.EnumValueDescriptor(
      name='STOPPED', index=9, number=4,
      options=None,
      type=None),
  ],
  containing_type=None,
  options=_descriptor._ParseOptions(descriptor_pb2.EnumOptions(), _b('\020\001')),
  serialized_start=1239,
  serialized_end=1381,
)
_sym_db.RegisterEnumDescriptor(_STATE)

State = enum_type_wrapper.EnumTypeWrapper(_STATE)
UNKNOWN = 0
READY = 1
RUNNING = 2
WAITING = 3
SUSPENDED = 4
FINISHED = 5
ABORTED = 6
CREATED = 1
BLOCKED = 3
STOPPED = 4



_PLATFORMID = _descriptor.Descriptor(
  name='PlatformId',
  full_name='firebird.butler.PlatformId',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='uid', full_name='firebird.butler.PlatformId.uid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='version', full_name='firebird.butler.PlatformId.version', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=88,
  serialized_end=130,
)


_VENDORID = _descriptor.Descriptor(
  name='VendorId',
  full_name='firebird.butler.VendorId',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='uid', full_name='firebird.butler.VendorId.uid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=132,
  serialized_end=155,
)


_AGENTIDENTIFICATION = _descriptor.Descriptor(
  name='AgentIdentification',
  full_name='firebird.butler.AgentIdentification',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='uid', full_name='firebird.butler.AgentIdentification.uid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='name', full_name='firebird.butler.AgentIdentification.name', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='version', full_name='firebird.butler.AgentIdentification.version', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='vendor', full_name='firebird.butler.AgentIdentification.vendor', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='platform', full_name='firebird.butler.AgentIdentification.platform', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='classification', full_name='firebird.butler.AgentIdentification.classification', index=5,
      number=6, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='firebird.butler.AgentIdentification.supplement', index=6,
      number=7, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=158,
  serialized_end=379,
)


_PEERIDENTIFICATION = _descriptor.Descriptor(
  name='PeerIdentification',
  full_name='firebird.butler.PeerIdentification',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='uid', full_name='firebird.butler.PeerIdentification.uid', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='pid', full_name='firebird.butler.PeerIdentification.pid', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='host', full_name='firebird.butler.PeerIdentification.host', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='firebird.butler.PeerIdentification.supplement', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=381,
  serialized_end=483,
)


_INTERFACESPEC = _descriptor.Descriptor(
  name='InterfaceSpec',
  full_name='firebird.butler.InterfaceSpec',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='number', full_name='firebird.butler.InterfaceSpec.number', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='uid', full_name='firebird.butler.InterfaceSpec.uid', index=1,
      number=2, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=485,
  serialized_end=529,
)


_ERRORDESCRIPTION = _descriptor.Descriptor(
  name='ErrorDescription',
  full_name='firebird.butler.ErrorDescription',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='code', full_name='firebird.butler.ErrorDescription.code', index=0,
      number=1, type=4, cpp_type=4, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='description', full_name='firebird.butler.ErrorDescription.description', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='context', full_name='firebird.butler.ErrorDescription.context', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='annotation', full_name='firebird.butler.ErrorDescription.annotation', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=532,
  serialized_end=672,
)


_HELLODATAFRAME = _descriptor.Descriptor(
  name='HelloDataframe',
  full_name='firebird.butler.HelloDataframe',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='instance', full_name='firebird.butler.HelloDataframe.instance', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='client', full_name='firebird.butler.HelloDataframe.client', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='firebird.butler.HelloDataframe.supplement', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=675,
  serialized_end=842,
)


_WELCOMEDATAFRAME = _descriptor.Descriptor(
  name='WelcomeDataframe',
  full_name='firebird.butler.WelcomeDataframe',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='instance', full_name='firebird.butler.WelcomeDataframe.instance', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='service', full_name='firebird.butler.WelcomeDataframe.service', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='api', full_name='firebird.butler.WelcomeDataframe.api', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='firebird.butler.WelcomeDataframe.supplement', index=3,
      number=4, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=845,
  serialized_end=1060,
)


_CANCELREQUESTS = _descriptor.Descriptor(
  name='CancelRequests',
  full_name='firebird.butler.CancelRequests',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='token', full_name='firebird.butler.CancelRequests.token', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='firebird.butler.CancelRequests.supplement', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1062,
  serialized_end=1135,
)


_STATEINFORMATION = _descriptor.Descriptor(
  name='StateInformation',
  full_name='firebird.butler.StateInformation',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='state', full_name='firebird.butler.StateInformation.state', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='firebird.butler.StateInformation.supplement', index=1,
      number=2, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1137,
  serialized_end=1236,
)

_AGENTIDENTIFICATION.fields_by_name['vendor'].message_type = _VENDORID
_AGENTIDENTIFICATION.fields_by_name['platform'].message_type = _PLATFORMID
_AGENTIDENTIFICATION.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_PEERIDENTIFICATION.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_ERRORDESCRIPTION.fields_by_name['context'].message_type = google_dot_protobuf_dot_struct__pb2._STRUCT
_ERRORDESCRIPTION.fields_by_name['annotation'].message_type = google_dot_protobuf_dot_struct__pb2._STRUCT
_HELLODATAFRAME.fields_by_name['instance'].message_type = _PEERIDENTIFICATION
_HELLODATAFRAME.fields_by_name['client'].message_type = _AGENTIDENTIFICATION
_HELLODATAFRAME.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_WELCOMEDATAFRAME.fields_by_name['instance'].message_type = _PEERIDENTIFICATION
_WELCOMEDATAFRAME.fields_by_name['service'].message_type = _AGENTIDENTIFICATION
_WELCOMEDATAFRAME.fields_by_name['api'].message_type = _INTERFACESPEC
_WELCOMEDATAFRAME.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_CANCELREQUESTS.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_STATEINFORMATION.fields_by_name['state'].enum_type = _STATE
_STATEINFORMATION.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
DESCRIPTOR.message_types_by_name['PlatformId'] = _PLATFORMID
DESCRIPTOR.message_types_by_name['VendorId'] = _VENDORID
DESCRIPTOR.message_types_by_name['AgentIdentification'] = _AGENTIDENTIFICATION
DESCRIPTOR.message_types_by_name['PeerIdentification'] = _PEERIDENTIFICATION
DESCRIPTOR.message_types_by_name['InterfaceSpec'] = _INTERFACESPEC
DESCRIPTOR.message_types_by_name['ErrorDescription'] = _ERRORDESCRIPTION
DESCRIPTOR.message_types_by_name['HelloDataframe'] = _HELLODATAFRAME
DESCRIPTOR.message_types_by_name['WelcomeDataframe'] = _WELCOMEDATAFRAME
DESCRIPTOR.message_types_by_name['CancelRequests'] = _CANCELREQUESTS
DESCRIPTOR.message_types_by_name['StateInformation'] = _STATEINFORMATION
DESCRIPTOR.enum_types_by_name['State'] = _STATE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

PlatformId = _reflection.GeneratedProtocolMessageType('PlatformId', (_message.Message,), dict(
  DESCRIPTOR = _PLATFORMID,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.PlatformId)
  ))
_sym_db.RegisterMessage(PlatformId)

VendorId = _reflection.GeneratedProtocolMessageType('VendorId', (_message.Message,), dict(
  DESCRIPTOR = _VENDORID,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.VendorId)
  ))
_sym_db.RegisterMessage(VendorId)

AgentIdentification = _reflection.GeneratedProtocolMessageType('AgentIdentification', (_message.Message,), dict(
  DESCRIPTOR = _AGENTIDENTIFICATION,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.AgentIdentification)
  ))
_sym_db.RegisterMessage(AgentIdentification)

PeerIdentification = _reflection.GeneratedProtocolMessageType('PeerIdentification', (_message.Message,), dict(
  DESCRIPTOR = _PEERIDENTIFICATION,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.PeerIdentification)
  ))
_sym_db.RegisterMessage(PeerIdentification)

InterfaceSpec = _reflection.GeneratedProtocolMessageType('InterfaceSpec', (_message.Message,), dict(
  DESCRIPTOR = _INTERFACESPEC,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.InterfaceSpec)
  ))
_sym_db.RegisterMessage(InterfaceSpec)

ErrorDescription = _reflection.GeneratedProtocolMessageType('ErrorDescription', (_message.Message,), dict(
  DESCRIPTOR = _ERRORDESCRIPTION,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.ErrorDescription)
  ))
_sym_db.RegisterMessage(ErrorDescription)

HelloDataframe = _reflection.GeneratedProtocolMessageType('HelloDataframe', (_message.Message,), dict(
  DESCRIPTOR = _HELLODATAFRAME,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.HelloDataframe)
  ))
_sym_db.RegisterMessage(HelloDataframe)

WelcomeDataframe = _reflection.GeneratedProtocolMessageType('WelcomeDataframe', (_message.Message,), dict(
  DESCRIPTOR = _WELCOMEDATAFRAME,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.WelcomeDataframe)
  ))
_sym_db.RegisterMessage(WelcomeDataframe)

CancelRequests = _reflection.GeneratedProtocolMessageType('CancelRequests', (_message.Message,), dict(
  DESCRIPTOR = _CANCELREQUESTS,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.CancelRequests)
  ))
_sym_db.RegisterMessage(CancelRequests)

StateInformation = _reflection.GeneratedProtocolMessageType('StateInformation', (_message.Message,), dict(
  DESCRIPTOR = _STATEINFORMATION,
  __module__ = 'fbsp_pb2'
  # @@protoc_insertion_point(class_scope:firebird.butler.StateInformation)
  ))
_sym_db.RegisterMessage(StateInformation)


DESCRIPTOR.has_options = True
DESCRIPTOR._options = _descriptor._ParseOptions(descriptor_pb2.FileOptions(), _b('\n\023org.firebird.butlerB\tFBSPProtoP\001\242\002\003FPB\252\002\024Firebird.Butler.FBSP'))
_STATE.has_options = True
_STATE._options = _descriptor._ParseOptions(descriptor_pb2.EnumOptions(), _b('\020\001'))
# @@protoc_insertion_point(module_scope)
