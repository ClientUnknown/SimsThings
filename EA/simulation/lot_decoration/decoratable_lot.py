from distributor.ops import SetLotDecorationsfrom distributor.rollback import ProtocolBufferRollbackfrom distributor.system import Distributorfrom lot_decoration import decorations_logger, DECORATE_IMMEDIATELYfrom lot_decoration.decorated_state import DecoratedState, EMPTY_DECORATED_STATEfrom lot_decoration.decoration_provider import DEFAULT_DECORATION_PROVIDERimport build_buyimport servicesimport enum
class DecoratedLotVisualState(enum.Int, export=False):
    NOT_SET = 0
    PRESET = ...
    CUSTOM = ...

class DecoratableLot:

    def __init__(self, lot_info):
        self._household_id = lot_info.household_id
        self._zone_id = lot_info.zone_id
        self._decoration_states = {}
        self._current_provider = DEFAULT_DECORATION_PROVIDER
        self._visual_state = DecoratedLotVisualState.NOT_SET
        self._visible_preset = None

    @property
    def zone_id(self):
        return self._zone_id

    @property
    def deco_state(self):
        return self._decoration_states.get(self.deco_type_id, EMPTY_DECORATED_STATE)

    @property
    def deco_type_id(self):
        return self._current_provider.decoration_type_id

    @property
    def is_decorated(self):
        return self.deco_type_id != DEFAULT_DECORATION_PROVIDER.decoration_type_id or len(self.deco_state.custom_decorations) > 0

    @property
    def visible_preset(self):
        return self._visible_preset

    def has_custom_decorations(self, deco_type_id):
        return deco_type_id in self._decoration_states

    def load_deco_states_from_proto(self, decorated_lot_proto, provider):
        self._zone_id = decorated_lot_proto.zone_id
        self._current_provider = provider
        for state_proto in decorated_lot_proto.decoration_states:
            decoration_state = DecoratedState()
            decoration_state.load_locations_from_proto(state_proto.decorated_locations)
            self._decoration_states[state_proto.decoration_type_id] = decoration_state

    def save_deco_states_to_proto(self, lot_decorations_proto):
        if self._decoration_states or self.deco_type_id == DEFAULT_DECORATION_PROVIDER.decoration_type_id:
            return
        with ProtocolBufferRollback(lot_decorations_proto) as lot_setting_proto:
            lot_setting_proto.zone_id = self.zone_id
            lot_setting_proto.active_decoration_state = self.deco_type_id
            for (deco_type_id, decorated_state) in self._decoration_states.items():
                if decorated_state is EMPTY_DECORATED_STATE:
                    decorations_logger.error('Trying to save an empty decorated state into for deco type id {}.  This should never happen!', deco_type_id)
                else:
                    with ProtocolBufferRollback(lot_setting_proto.decoration_states) as deco_state_proto:
                        deco_state_proto.decoration_type_id = deco_type_id
                        decorated_state.save_locations_to_proto(deco_state_proto.decorated_locations)

    def is_owned_by_active_household(self):
        if self._household_id is None:
            return False
        return self._household_id == services.active_household_id()

    def switch_to_appropriate_type(self, deco_provider, client_decoration_params, preset_override=None):
        appropriate_decor = deco_provider.decoration_type_id
        if appropriate_decor != self.deco_type_id or preset_override is not None:
            self._visual_state = DecoratedLotVisualState.NOT_SET
            self._current_provider = deco_provider
            if client_decoration_params is not None:
                self._apply_client_decorate_zone(client_decoration_params, preset_override=preset_override)

    def _get_modifiable_deco_state(self):
        if self.deco_state is EMPTY_DECORATED_STATE:
            self._decoration_states[self.deco_type_id] = DecoratedState()
        return self.deco_state

    def apply_decoration(self, lot_decoration, deco_location):
        if self._apply_client_decoration(deco_location, lot_decoration=lot_decoration):
            self._visual_state = DecoratedLotVisualState.CUSTOM
            self._get_modifiable_deco_state().apply_decoration(lot_decoration, deco_location)
            return True
        decorations_logger.error('Failed to set lot decoration {} at {}', lot_decoration, deco_location)
        return False

    def remove_decoration(self, deco_location):
        if self._apply_client_decoration(deco_location, lot_decoration=None):
            self._visual_state = DecoratedLotVisualState.CUSTOM
            self._get_modifiable_deco_state().remove_decoration(deco_location)
            return True
        decorations_logger.error('Failed to remove lot decoration at {}', deco_location)
        return False

    def reset_decorations(self):
        if self.deco_type_id in self._decoration_states:
            for (location, _) in self.deco_state.custom_decorations:
                self.remove_decoration(location)
            if not self.deco_state.custom_decorations:
                del self._decoration_states[self.deco_type_id]
        else:
            decorations_logger.error('No decorations on lot for decoration type {}', self.deco_type_id)

    def on_household_owner_changed(self, household):
        self._household_id = None if household is None else household.id

    def get_deco_type_and_preset(self):
        customized = self.deco_state.customized
        deco_type = self.deco_type_id
        if deco_type == DEFAULT_DECORATION_PROVIDER.decoration_type_id or customized:
            preset = None
        else:
            preset = self._current_provider.decoration_preset
        return (deco_type, preset)

    def _apply_client_decorate_zone(self, client_decoration_params, preset_override=None):
        (_, preset) = self.get_deco_type_and_preset()
        if preset_override is not None:
            self._visual_state = DecoratedLotVisualState.CUSTOM
            self._visible_preset = preset_override
            op_kwargs = {'preset_id': self._visible_preset.guid64}
        elif preset is None:
            self._visual_state = DecoratedLotVisualState.CUSTOM
            self._visible_preset = None
            op_kwargs = {'decoration_type_id': self.deco_type_id}
        else:
            self._visual_state = DecoratedLotVisualState.PRESET
            self._visible_preset = preset
            op_kwargs = {'preset_id': self._visible_preset.guid64}
        op_kwargs['fade_in_time'] = client_decoration_params.fade_duration
        op_kwargs['fade_in_delay'] = client_decoration_params.client_fade_delay
        op_kwargs['fade_in_delay_variation'] = client_decoration_params.fade_variation_range
        Distributor.instance().add_op_with_no_owner(SetLotDecorations(self._zone_id, **op_kwargs))

    def _apply_client_decoration(self, deco_location, lot_decoration=None):
        deco_product_id = 0 if lot_decoration is None else lot_decoration.decoration_resource
        isClear = lot_decoration is None
        preset = self._current_provider.decoration_preset
        preset_id = preset.guid64 if self._visual_state == DecoratedLotVisualState.PRESET else 0
        return build_buy.set_active_lot_decoration(self._zone_id, self.deco_type_id, preset_id, deco_location.value, deco_product_id, isClear)

    def resend_client_decoration_state(self, client_decoration_params=DECORATE_IMMEDIATELY):
        self._apply_client_decorate_zone(client_decoration_params)
