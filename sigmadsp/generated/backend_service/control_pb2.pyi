"""
@generated by mypy-protobuf.  Do not edit manually!
isort:skip_file
"""
import builtins
import google.protobuf.descriptor
import google.protobuf.internal.containers
import google.protobuf.message
import typing
import typing_extensions

DESCRIPTOR: google.protobuf.descriptor.FileDescriptor

class ChangeVolume(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    NAME_TOKENS_FIELD_NUMBER: builtins.int
    VALUE_FIELD_NUMBER: builtins.int
    RELATIVE_FIELD_NUMBER: builtins.int
    @property
    def name_tokens(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[typing.Text]: ...
    value: builtins.float
    relative: builtins.bool
    def __init__(self,
        *,
        name_tokens: typing.Optional[typing.Iterable[typing.Text]] = ...,
        value: builtins.float = ...,
        relative: builtins.bool = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["name_tokens",b"name_tokens","relative",b"relative","value",b"value"]) -> None: ...
global___ChangeVolume = ChangeVolume

class ControlParameterRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    CHANGE_VOLUME_FIELD_NUMBER: builtins.int
    @property
    def change_volume(self) -> global___ChangeVolume: ...
    def __init__(self,
        *,
        change_volume: typing.Optional[global___ChangeVolume] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["change_volume",b"change_volume","command",b"command"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["change_volume",b"change_volume","command",b"command"]) -> None: ...
    def WhichOneof(self, oneof_group: typing_extensions.Literal["command",b"command"]) -> typing.Optional[typing_extensions.Literal["change_volume"]]: ...
global___ControlParameterRequest = ControlParameterRequest

class LoadParameters(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    CONTENT_FIELD_NUMBER: builtins.int
    @property
    def content(self) -> google.protobuf.internal.containers.RepeatedScalarFieldContainer[typing.Text]: ...
    def __init__(self,
        *,
        content: typing.Optional[typing.Iterable[typing.Text]] = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["content",b"content"]) -> None: ...
global___LoadParameters = LoadParameters

class ControlRequest(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    RESET_DSP_FIELD_NUMBER: builtins.int
    HARD_RESET_DSP_FIELD_NUMBER: builtins.int
    LOAD_PARAMETERS_FIELD_NUMBER: builtins.int
    reset_dsp: builtins.bool
    hard_reset_dsp: builtins.bool
    @property
    def load_parameters(self) -> global___LoadParameters: ...
    def __init__(self,
        *,
        reset_dsp: builtins.bool = ...,
        hard_reset_dsp: builtins.bool = ...,
        load_parameters: typing.Optional[global___LoadParameters] = ...,
        ) -> None: ...
    def HasField(self, field_name: typing_extensions.Literal["command",b"command","hard_reset_dsp",b"hard_reset_dsp","load_parameters",b"load_parameters","reset_dsp",b"reset_dsp"]) -> builtins.bool: ...
    def ClearField(self, field_name: typing_extensions.Literal["command",b"command","hard_reset_dsp",b"hard_reset_dsp","load_parameters",b"load_parameters","reset_dsp",b"reset_dsp"]) -> None: ...
    def WhichOneof(self, oneof_group: typing_extensions.Literal["command",b"command"]) -> typing.Optional[typing_extensions.Literal["reset_dsp","hard_reset_dsp","load_parameters"]]: ...
global___ControlRequest = ControlRequest

class ControlResponse(google.protobuf.message.Message):
    DESCRIPTOR: google.protobuf.descriptor.Descriptor
    SUCCESS_FIELD_NUMBER: builtins.int
    MESSAGE_FIELD_NUMBER: builtins.int
    success: builtins.bool
    message: typing.Text
    def __init__(self,
        *,
        success: builtins.bool = ...,
        message: typing.Text = ...,
        ) -> None: ...
    def ClearField(self, field_name: typing_extensions.Literal["message",b"message","success",b"success"]) -> None: ...
global___ControlResponse = ControlResponse