from distributor.rollback import ProtocolBufferRollbackfrom lot_decoration import decorations_loggerfrom lot_decoration.lot_decoration_enums import DecorationLocationfrom sims4.repr_utils import standard_reprfrom sims4.resources import Typesfrom singletons import EMPTY_SETimport services
class _DecoratedStateBase:

    def apply_decoration(self, lot_decoration, deco_location):
        raise NotImplementedError

    def remove_decoration(self, deco_location):
        raise NotImplementedError

    @property
    def customized(self):
        raise NotImplementedError

    @property
    def custom_decorations(self):
        raise NotImplementedError

    def get_deco_state_gsi_data(self):
        return ()

class EmptyDecoratedState(_DecoratedStateBase):

    def apply_decoration(self, lot_decoration, deco_location):
        raise RuntimeError('Attempting to modify an immutable state!')

    def remove_decoration(self, deco_location):
        raise RuntimeError('Attempting to modify an immutable state!')

    @property
    def customized(self):
        return False

    @property
    def custom_decorations(self):
        return EMPTY_SET
EMPTY_DECORATED_STATE = EmptyDecoratedState()
class DecoratedState(_DecoratedStateBase):
    __slots__ = ('_custom_decorations', '_customized')

    def __init__(self):
        self._custom_decorations = {}
        self._customized = False

    def __repr__(self):
        return standard_repr(self, customized=self.customized, custom_decorations=self.custom_decorations)

    def apply_decoration(self, lot_decoration, deco_location):
        self._custom_decorations[deco_location] = lot_decoration
        self._customized = True

    def remove_decoration(self, deco_location):
        if deco_location not in self._custom_decorations:
            return
        del self._custom_decorations[deco_location]
        self._customized = True

    @property
    def customized(self):
        return self._customized

    @property
    def custom_decorations(self):
        return tuple(self._custom_decorations.items())

    def load_locations_from_proto(self, locations_proto):
        self._customized = True
        lot_decoration_manager = services.get_instance_manager(Types.LOT_DECORATION)
        for decorated_location_proto in locations_proto:
            decoration_guid = decorated_location_proto.decoration
            decoration = lot_decoration_manager.get(decoration_guid)
            if decoration is None:
                decorations_logger.warn('Could not find decoration resource for guid {}', decoration_guid)
            else:
                self._custom_decorations[DecorationLocation(decorated_location_proto.location)] = decoration

    def save_locations_to_proto(self, locations_proto):
        for (location, decoration) in self._custom_decorations.items():
            with ProtocolBufferRollback(locations_proto) as location_proto:
                location_proto.location = location.value
                location_proto.decoration = decoration.guid64

    def get_deco_state_gsi_data(self):
        gsi_data = []
        for (deco_location, decoration) in self._custom_decorations.items():
            gsi_data.append({'deco_location': deco_location.name, 'decoration': str(decoration)})
        return gsi_data
