from google.protobuf import descriptor
class FileDescriptorSet(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _FILEDESCRIPTORSET

class FileDescriptorProto(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _FILEDESCRIPTORPROTO

class DescriptorProto(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class ExtensionRange(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _DESCRIPTORPROTO_EXTENSIONRANGE

    DESCRIPTOR = _DESCRIPTORPROTO

class FieldDescriptorProto(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _FIELDDESCRIPTORPROTO

class EnumDescriptorProto(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ENUMDESCRIPTORPROTO

class EnumValueDescriptorProto(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ENUMVALUEDESCRIPTORPROTO

class ServiceDescriptorProto(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _SERVICEDESCRIPTORPROTO

class MethodDescriptorProto(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _METHODDESCRIPTORPROTO

class FileOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _FILEOPTIONS

class MessageOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _MESSAGEOPTIONS

class FieldOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _FIELDOPTIONS

class EnumOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ENUMOPTIONS

class EnumValueOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ENUMVALUEOPTIONS

class ServiceOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _SERVICEOPTIONS

class MethodOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _METHODOPTIONS

class UninterpretedOption(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class NamePart(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _UNINTERPRETEDOPTION_NAMEPART

    DESCRIPTOR = _UNINTERPRETEDOPTION

class SourceCodeInfo(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class Location(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _SOURCECODEINFO_LOCATION

    DESCRIPTOR = _SOURCECODEINFO
