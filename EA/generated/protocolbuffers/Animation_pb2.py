from google.protobuf import descriptor
class AnimationEventHandler(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ANIMATIONEVENTHANDLER

class AnimationRequestBlock(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ANIMATIONREQUESTBLOCK

class AnimationStateRequest(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ANIMATIONSTATEREQUEST

class CurveData(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _CURVEDATA

class FocusEvent(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _FOCUSEVENT

class ConfigureAwarenessActor(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class ChannelOptions(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _CONFIGUREAWARENESSACTOR_CHANNELOPTIONS

    DESCRIPTOR = _CONFIGUREAWARENESSACTOR

class ConfigureAwarenessSourceObject(message.Message, metaclass=reflection.GeneratedProtocolMessageType):

    class GameplayChannelValue(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
        DESCRIPTOR = _CONFIGUREAWARENESSSOURCEOBJECT_GAMEPLAYCHANNELVALUE

    DESCRIPTOR = _CONFIGUREAWARENESSSOURCEOBJECT
