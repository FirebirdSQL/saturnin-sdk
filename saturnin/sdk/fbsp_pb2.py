# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: saturnin/sdk/fbsp.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()


from google.protobuf import any_pb2 as google_dot_protobuf_dot_any__pb2
from saturnin.sdk import fbsd_pb2 as saturnin_dot_sdk_dot_fbsd__pb2

from saturnin.sdk.fbsd_pb2 import *

DESCRIPTOR = _descriptor.FileDescriptor(
  name='saturnin/sdk/fbsp.proto',
  package='fbsp',
  syntax='proto3',
  serialized_pb=_b('\n\x17saturnin/sdk/fbsp.proto\x12\x04\x66\x62sp\x1a\x19google/protobuf/any.proto\x1a\x17saturnin/sdk/fbsd.proto\"\x91\x01\n\x0eHelloDataframe\x12*\n\x08instance\x18\x01 \x01(\x0b\x32\x18.fbsd.PeerIdentification\x12)\n\x06\x63lient\x18\x02 \x01(\x0b\x32\x19.fbsd.AgentIdentification\x12(\n\nsupplement\x18\x03 \x03(\x0b\x32\x14.google.protobuf.Any\"\xb6\x01\n\x10WelcomeDataframe\x12*\n\x08instance\x18\x01 \x01(\x0b\x32\x18.fbsd.PeerIdentification\x12*\n\x07service\x18\x02 \x01(\x0b\x32\x19.fbsd.AgentIdentification\x12 \n\x03\x61pi\x18\x03 \x03(\x0b\x32\x13.fbsd.InterfaceSpec\x12(\n\nsupplement\x18\x04 \x03(\x0b\x32\x14.google.protobuf.Any\"I\n\x0e\x43\x61ncelRequests\x12\r\n\x05token\x18\x01 \x01(\x0c\x12(\n\nsupplement\x18\x02 \x03(\x0b\x32\x14.google.protobuf.Any\"X\n\x10StateInformation\x12\x1a\n\x05state\x18\x01 \x01(\x0e\x32\x0b.fbsd.State\x12(\n\nsupplement\x18\x02 \x03(\x0b\x32\x14.google.protobuf.AnyP\x01\x62\x06proto3')
  ,
  dependencies=[google_dot_protobuf_dot_any__pb2.DESCRIPTOR,saturnin_dot_sdk_dot_fbsd__pb2.DESCRIPTOR,],
  public_dependencies=[saturnin_dot_sdk_dot_fbsd__pb2.DESCRIPTOR,])




_HELLODATAFRAME = _descriptor.Descriptor(
  name='HelloDataframe',
  full_name='fbsp.HelloDataframe',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='instance', full_name='fbsp.HelloDataframe.instance', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='client', full_name='fbsp.HelloDataframe.client', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='fbsp.HelloDataframe.supplement', index=2,
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
  serialized_start=86,
  serialized_end=231,
)


_WELCOMEDATAFRAME = _descriptor.Descriptor(
  name='WelcomeDataframe',
  full_name='fbsp.WelcomeDataframe',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='instance', full_name='fbsp.WelcomeDataframe.instance', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='service', full_name='fbsp.WelcomeDataframe.service', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='api', full_name='fbsp.WelcomeDataframe.api', index=2,
      number=3, type=11, cpp_type=10, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='fbsp.WelcomeDataframe.supplement', index=3,
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
  serialized_start=234,
  serialized_end=416,
)


_CANCELREQUESTS = _descriptor.Descriptor(
  name='CancelRequests',
  full_name='fbsp.CancelRequests',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='token', full_name='fbsp.CancelRequests.token', index=0,
      number=1, type=12, cpp_type=9, label=1,
      has_default_value=False, default_value=_b(""),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='fbsp.CancelRequests.supplement', index=1,
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
  serialized_start=418,
  serialized_end=491,
)


_STATEINFORMATION = _descriptor.Descriptor(
  name='StateInformation',
  full_name='fbsp.StateInformation',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='state', full_name='fbsp.StateInformation.state', index=0,
      number=1, type=14, cpp_type=8, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='supplement', full_name='fbsp.StateInformation.supplement', index=1,
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
  serialized_start=493,
  serialized_end=581,
)

_HELLODATAFRAME.fields_by_name['instance'].message_type = saturnin_dot_sdk_dot_fbsd__pb2._PEERIDENTIFICATION
_HELLODATAFRAME.fields_by_name['client'].message_type = saturnin_dot_sdk_dot_fbsd__pb2._AGENTIDENTIFICATION
_HELLODATAFRAME.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_WELCOMEDATAFRAME.fields_by_name['instance'].message_type = saturnin_dot_sdk_dot_fbsd__pb2._PEERIDENTIFICATION
_WELCOMEDATAFRAME.fields_by_name['service'].message_type = saturnin_dot_sdk_dot_fbsd__pb2._AGENTIDENTIFICATION
_WELCOMEDATAFRAME.fields_by_name['api'].message_type = saturnin_dot_sdk_dot_fbsd__pb2._INTERFACESPEC
_WELCOMEDATAFRAME.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_CANCELREQUESTS.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
_STATEINFORMATION.fields_by_name['state'].enum_type = saturnin_dot_sdk_dot_fbsd__pb2._STATE
_STATEINFORMATION.fields_by_name['supplement'].message_type = google_dot_protobuf_dot_any__pb2._ANY
DESCRIPTOR.message_types_by_name['HelloDataframe'] = _HELLODATAFRAME
DESCRIPTOR.message_types_by_name['WelcomeDataframe'] = _WELCOMEDATAFRAME
DESCRIPTOR.message_types_by_name['CancelRequests'] = _CANCELREQUESTS
DESCRIPTOR.message_types_by_name['StateInformation'] = _STATEINFORMATION
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

HelloDataframe = _reflection.GeneratedProtocolMessageType('HelloDataframe', (_message.Message,), dict(
  DESCRIPTOR = _HELLODATAFRAME,
  __module__ = 'saturnin.sdk.fbsp_pb2'
  # @@protoc_insertion_point(class_scope:fbsp.HelloDataframe)
  ))
_sym_db.RegisterMessage(HelloDataframe)

WelcomeDataframe = _reflection.GeneratedProtocolMessageType('WelcomeDataframe', (_message.Message,), dict(
  DESCRIPTOR = _WELCOMEDATAFRAME,
  __module__ = 'saturnin.sdk.fbsp_pb2'
  # @@protoc_insertion_point(class_scope:fbsp.WelcomeDataframe)
  ))
_sym_db.RegisterMessage(WelcomeDataframe)

CancelRequests = _reflection.GeneratedProtocolMessageType('CancelRequests', (_message.Message,), dict(
  DESCRIPTOR = _CANCELREQUESTS,
  __module__ = 'saturnin.sdk.fbsp_pb2'
  # @@protoc_insertion_point(class_scope:fbsp.CancelRequests)
  ))
_sym_db.RegisterMessage(CancelRequests)

StateInformation = _reflection.GeneratedProtocolMessageType('StateInformation', (_message.Message,), dict(
  DESCRIPTOR = _STATEINFORMATION,
  __module__ = 'saturnin.sdk.fbsp_pb2'
  # @@protoc_insertion_point(class_scope:fbsp.StateInformation)
  ))
_sym_db.RegisterMessage(StateInformation)


# @@protoc_insertion_point(module_scope)
