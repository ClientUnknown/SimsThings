from google.protobuf import descriptor
class Interactable(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _INTERACTABLE

class PieMenuItem(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _PIEMENUITEM

class PieMenuCreate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _PIEMENUCREATE

class TravelMenuCreate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _TRAVELMENUCREATE

class TravelMenuInfo(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _TRAVELMENUINFO

class TravelMenuResponse(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _TRAVELMENURESPONSE

class TravelInitiate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _TRAVELINITIATE

class MoveInMoveOutInfo(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _MOVEINMOVEOUTINFO

class SellRetailLot(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _SELLRETAILLOT

class TravelSimsToZone(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _TRAVELSIMSTOZONE

class CASAvailableZonesInfo(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _CASAVAILABLEZONESINFO

class WorldZonesInfo(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _WORLDZONESINFO

class ZoneInfo(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _ZONEINFO

class InteractionProgressUpdate(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _INTERACTIONPROGRESSUPDATE

class SimTransferRequest(message.Message, metaclass=reflection.GeneratedProtocolMessageType):
    DESCRIPTOR = _SIMTRANSFERREQUEST
