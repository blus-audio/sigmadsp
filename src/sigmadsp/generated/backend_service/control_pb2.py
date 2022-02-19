# -*- coding: utf-8 -*-
# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: control.proto
"""Generated protocol buffer code."""
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='control.proto',
  package='sigmadsp.backend_service',
  syntax='proto3',
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_pb=b'\n\rcontrol.proto\x12\x18sigmadsp.backend_service\"B\n\x0c\x43hangeVolume\x12\x11\n\tcell_name\x18\x01 \x01(\t\x12\r\n\x05value\x18\x02 \x01(\x01\x12\x10\n\x08relative\x18\x03 \x01(\x08\"!\n\x0eLoadParameters\x12\x0f\n\x07\x63ontent\x18\x01 \x03(\t\"\xb6\x01\n\x0e\x43ontrolRequest\x12?\n\rchange_volume\x18\x01 \x01(\x0b\x32&.sigmadsp.backend_service.ChangeVolumeH\x00\x12\x13\n\treset_dsp\x18\x02 \x01(\x08H\x00\x12\x43\n\x0fload_parameters\x18\x03 \x01(\x0b\x32(.sigmadsp.backend_service.LoadParametersH\x00\x42\t\n\x07\x63ommand\"3\n\x0f\x43ontrolResponse\x12\x0f\n\x07success\x18\x01 \x01(\x08\x12\x0f\n\x07message\x18\x02 \x01(\t2i\n\x07\x42\x61\x63kend\x12^\n\x07\x63ontrol\x12(.sigmadsp.backend_service.ControlRequest\x1a).sigmadsp.backend_service.ControlResponseb\x06proto3'
)




_CHANGEVOLUME = _descriptor.Descriptor(
  name='ChangeVolume',
  full_name='sigmadsp.backend_service.ChangeVolume',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='cell_name', full_name='sigmadsp.backend_service.ChangeVolume.cell_name', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='value', full_name='sigmadsp.backend_service.ChangeVolume.value', index=1,
      number=2, type=1, cpp_type=5, label=1,
      has_default_value=False, default_value=float(0),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='relative', full_name='sigmadsp.backend_service.ChangeVolume.relative', index=2,
      number=3, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=43,
  serialized_end=109,
)


_LOADPARAMETERS = _descriptor.Descriptor(
  name='LoadParameters',
  full_name='sigmadsp.backend_service.LoadParameters',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='content', full_name='sigmadsp.backend_service.LoadParameters.content', index=0,
      number=1, type=9, cpp_type=9, label=3,
      has_default_value=False, default_value=[],
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=111,
  serialized_end=144,
)


_CONTROLREQUEST = _descriptor.Descriptor(
  name='ControlRequest',
  full_name='sigmadsp.backend_service.ControlRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='change_volume', full_name='sigmadsp.backend_service.ControlRequest.change_volume', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='reset_dsp', full_name='sigmadsp.backend_service.ControlRequest.reset_dsp', index=1,
      number=2, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='load_parameters', full_name='sigmadsp.backend_service.ControlRequest.load_parameters', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='command', full_name='sigmadsp.backend_service.ControlRequest.command',
      index=0, containing_type=None,
      create_key=_descriptor._internal_create_key,
    fields=[]),
  ],
  serialized_start=147,
  serialized_end=329,
)


_CONTROLRESPONSE = _descriptor.Descriptor(
  name='ControlResponse',
  full_name='sigmadsp.backend_service.ControlResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  create_key=_descriptor._internal_create_key,
  fields=[
    _descriptor.FieldDescriptor(
      name='success', full_name='sigmadsp.backend_service.ControlResponse.success', index=0,
      number=1, type=8, cpp_type=7, label=1,
      has_default_value=False, default_value=False,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
    _descriptor.FieldDescriptor(
      name='message', full_name='sigmadsp.backend_service.ControlResponse.message', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=b"".decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      serialized_options=None, file=DESCRIPTOR,  create_key=_descriptor._internal_create_key),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  serialized_options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=331,
  serialized_end=382,
)

_CONTROLREQUEST.fields_by_name['change_volume'].message_type = _CHANGEVOLUME
_CONTROLREQUEST.fields_by_name['load_parameters'].message_type = _LOADPARAMETERS
_CONTROLREQUEST.oneofs_by_name['command'].fields.append(
  _CONTROLREQUEST.fields_by_name['change_volume'])
_CONTROLREQUEST.fields_by_name['change_volume'].containing_oneof = _CONTROLREQUEST.oneofs_by_name['command']
_CONTROLREQUEST.oneofs_by_name['command'].fields.append(
  _CONTROLREQUEST.fields_by_name['reset_dsp'])
_CONTROLREQUEST.fields_by_name['reset_dsp'].containing_oneof = _CONTROLREQUEST.oneofs_by_name['command']
_CONTROLREQUEST.oneofs_by_name['command'].fields.append(
  _CONTROLREQUEST.fields_by_name['load_parameters'])
_CONTROLREQUEST.fields_by_name['load_parameters'].containing_oneof = _CONTROLREQUEST.oneofs_by_name['command']
DESCRIPTOR.message_types_by_name['ChangeVolume'] = _CHANGEVOLUME
DESCRIPTOR.message_types_by_name['LoadParameters'] = _LOADPARAMETERS
DESCRIPTOR.message_types_by_name['ControlRequest'] = _CONTROLREQUEST
DESCRIPTOR.message_types_by_name['ControlResponse'] = _CONTROLRESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

ChangeVolume = _reflection.GeneratedProtocolMessageType('ChangeVolume', (_message.Message,), {
  'DESCRIPTOR' : _CHANGEVOLUME,
  '__module__' : 'control_pb2'
  # @@protoc_insertion_point(class_scope:sigmadsp.backend_service.ChangeVolume)
  })
_sym_db.RegisterMessage(ChangeVolume)

LoadParameters = _reflection.GeneratedProtocolMessageType('LoadParameters', (_message.Message,), {
  'DESCRIPTOR' : _LOADPARAMETERS,
  '__module__' : 'control_pb2'
  # @@protoc_insertion_point(class_scope:sigmadsp.backend_service.LoadParameters)
  })
_sym_db.RegisterMessage(LoadParameters)

ControlRequest = _reflection.GeneratedProtocolMessageType('ControlRequest', (_message.Message,), {
  'DESCRIPTOR' : _CONTROLREQUEST,
  '__module__' : 'control_pb2'
  # @@protoc_insertion_point(class_scope:sigmadsp.backend_service.ControlRequest)
  })
_sym_db.RegisterMessage(ControlRequest)

ControlResponse = _reflection.GeneratedProtocolMessageType('ControlResponse', (_message.Message,), {
  'DESCRIPTOR' : _CONTROLRESPONSE,
  '__module__' : 'control_pb2'
  # @@protoc_insertion_point(class_scope:sigmadsp.backend_service.ControlResponse)
  })
_sym_db.RegisterMessage(ControlResponse)



_BACKEND = _descriptor.ServiceDescriptor(
  name='Backend',
  full_name='sigmadsp.backend_service.Backend',
  file=DESCRIPTOR,
  index=0,
  serialized_options=None,
  create_key=_descriptor._internal_create_key,
  serialized_start=384,
  serialized_end=489,
  methods=[
  _descriptor.MethodDescriptor(
    name='control',
    full_name='sigmadsp.backend_service.Backend.control',
    index=0,
    containing_service=None,
    input_type=_CONTROLREQUEST,
    output_type=_CONTROLRESPONSE,
    serialized_options=None,
    create_key=_descriptor._internal_create_key,
  ),
])
_sym_db.RegisterServiceDescriptor(_BACKEND)

DESCRIPTOR.services_by_name['Backend'] = _BACKEND

# @@protoc_insertion_point(module_scope)
