import operatorfrom protocolbuffers import GameplaySaveData_pb2from distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom interactions import ParticipantTypefrom lot_decoration import decorations_logger, TunableClientLotDecorationParams, DECORATE_IMMEDIATELYfrom lot_decoration.decoration_provider import HolidayDecorationProvider, DEFAULT_DECORATION_PROVIDERfrom lot_decoration.lot_decoration_request import EVERYDAY_DECORATION_REQUEST, HolidayDecorationRequestfrom lot_decoration.neighborhood_decoration_state import NeighborhoodDecorationStatefrom sims4.common import Packfrom sims4.resources import Typesfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunablePackSafeReference, TunableListfrom sims4.utils import classpropertyfrom zone_tests import ZoneTest, PickedZoneIdsimport persistence_error_typesimport services
class LotDecorationService(Service):
    LOT_DECORATED_STATISTIC = TunablePackSafeReference(description='\n        The tunable statistic used to delineate that the active lot has been\n        decorated.  Used by Box of Decorations to set state based off whether\n        the lot has been decorated or not.\n        ', manager=services.get_instance_manager(Types.STATISTIC))
    AUTO_DECORATION_PARAMS = TunableClientLotDecorationParams(description='\n            The parameters used for when the neighbor lots get their decorations\n            automatically put up during gameplay.\n        ', default_fade_duration=0.5, default_fade_variation_range=2, default_client_fade_delay=5)
    PLAYER_DECORATION_PARAMS = TunableClientLotDecorationParams(description='\n            The parameters used for when the player chooses to put up/down\n            the decorations on their lot.\n        ', default_fade_duration=0.5, default_fade_variation_range=0, default_client_fade_delay=0)
    NON_DECORATABLE_TESTS = TunableList(description='\n        A list of tests applied to the neighborhood zones to determine if they \n        will avoid being auto-decorated for occasions like holidays.\n        \n        Any test that passes will cause the specified zone to not decorate\n        automatically.\n        ', tunable=ZoneTest.TunableFactory(locked_args={'tooltip': None, 'zone_source': PickedZoneIds()}))

    def __init__(self, *_, **__):
        self._neighborhood_deco_state = {}
        self._deco_provider_cache = {DEFAULT_DECORATION_PROVIDER.decoration_type_id: DEFAULT_DECORATION_PROVIDER}
        self._active_requests = {}
        self._active_requests[None] = EVERYDAY_DECORATION_REQUEST
        self._world_decorations_set = {}

    @classproperty
    def required_packs(cls):
        return (Pack.EP05,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_LOT_DECORATION_SERVICE

    def load(self, zone_data=None):
        save_slot_data = services.get_persistence_service().get_save_slot_proto_buff()
        service_proto = save_slot_data.gameplay_data.lot_decoration_service
        if service_proto is None:
            return
        for decorated_lot_proto in service_proto.lot_decorations:
            zone_id = decorated_lot_proto.zone_id
            neighborhood_state = self.get_neighborhood_state_for_zone(zone_id)
            if neighborhood_state is None:
                pass
            else:
                deco_type_id = decorated_lot_proto.active_decoration_state
                if self._is_valid_deco_type_id(deco_type_id):
                    provider = self._get_decoration_provider(deco_type_id)
                else:
                    provider = DEFAULT_DECORATION_PROVIDER
                decorated_lot = neighborhood_state.get_deco_lot_by_zone_id(zone_id)
                decorated_lot.load_deco_states_from_proto(decorated_lot_proto, provider)
        for world_setting in service_proto.world_decorations_set:
            if not self._is_valid_deco_type_id(world_setting.set_decorations):
                pass
            else:
                self._world_decorations_set[world_setting.world_id] = world_setting.set_decorations

    def save(self, save_slot_data=None, **__):
        lot_decoration_service_proto = GameplaySaveData_pb2.PersistableLotDecorationService()
        for neighborhood in self._neighborhood_deco_state.values():
            for lot in neighborhood.lots:
                lot.save_deco_states_to_proto(lot_decoration_service_proto.lot_decorations)
        for (world_id, set_decorations) in self._world_decorations_set.items():
            with ProtocolBufferRollback(lot_decoration_service_proto.world_decorations_set) as world_setting:
                world_setting.world_id = world_id
                world_setting.set_decorations = set_decorations
        save_slot_data.gameplay_data.lot_decoration_service = lot_decoration_service_proto

    def on_zone_load(self):
        self._try_set_neighborhood_state()

    def on_all_households_and_sim_infos_loaded(self, client):
        self._try_set_neighborhood_state()

    def _is_valid_deco_type_id(self, deco_type_id):
        if deco_type_id == 0:
            return True
        holiday_service = services.holiday_service()
        if holiday_service is None:
            return False
        return holiday_service.is_valid_holiday_id(deco_type_id)

    def _try_set_neighborhood_state(self):
        zone = services.current_zone()
        if zone is None:
            return
        request_to_process = self._get_highest_priority_request()
        request_provider = self._get_decoration_provider(request_to_process.provided_type)
        check_priorities = len(self._active_requests) > 1
        if check_priorities and (zone.world_id not in self._world_decorations_set or request_provider.decoration_type_id != self._world_decorations_set[zone.world_id]):
            self._process_decoration_request(request_to_process, decorate_immediately=True)
        else:
            self._send_neighborhood_state_to_client()
        self._update_current_lot_statistic()

    def _send_neighborhood_state_to_client(self):
        neighborhood = self._get_current_neighborhood_state()
        if neighborhood is None:
            return
        for lot in neighborhood.lots:
            lot.resend_client_decoration_state()

    def get_neighborhood_state_for_zone(self, zone_id):
        zone_proto = services.get_persistence_service().get_zone_proto_buff(zone_id)
        if zone_proto is None:
            decorations_logger.warn('Could not find zone data for zone {}', zone_id)
            return
        neighborhood_proto = services.get_persistence_service().get_neighborhood_proto_buff(zone_proto.neighborhood_id)
        if neighborhood_proto is None:
            decorations_logger.warn('Could not find neighborhood data for zone {}', zone_id)
            return
        world_id = zone_proto.world_id
        if self._neighborhood_deco_state.get(world_id) is None:
            world_zone_data = [zone_proto for zone_proto in services.get_persistence_service().zone_proto_buffs_gen() if zone_proto.world_id == world_id]
            self._neighborhood_deco_state[world_id] = NeighborhoodDecorationState(world_id, world_zone_data)
        return self._neighborhood_deco_state[world_id]

    def _get_current_neighborhood_state(self):
        return self.get_neighborhood_state_for_zone(services.current_zone_id())

    def _get_decoration_provider(self, deco_type_id):
        if deco_type_id is None:
            return DEFAULT_DECORATION_PROVIDER
        if deco_type_id == DEFAULT_DECORATION_PROVIDER.decoration_type_id:
            return DEFAULT_DECORATION_PROVIDER
        if deco_type_id not in self._deco_provider_cache:
            self._deco_provider_cache[deco_type_id] = HolidayDecorationProvider(deco_type_id)
        return self._deco_provider_cache[deco_type_id]

    def get_active_lot_decoration_type_id(self):
        deco_lot = self._get_active_lot_decoration_state()
        if deco_lot is None:
            decorations_logger.error("Could not find active lot's decoration data.")
            return
        return deco_lot.deco_type_id

    def _get_active_lot_decoration_state(self):
        zone_id = services.current_zone_id()
        neighborhood_decoration_state = self.get_neighborhood_state_for_zone(zone_id)
        if neighborhood_decoration_state is None:
            decorations_logger.error('Could not find neighborhood state zone {}', zone_id)
            return
        return neighborhood_decoration_state.get_deco_lot_by_zone_id(zone_id)

    def does_lot_have_custom_decorations(self, holiday_id):
        if holiday_id is None:
            decorations_logger.error('None is being used as holiday_id.  holiday_id should always be numeric.')
            holiday_id = 0
        decoration_state = self._get_active_lot_decoration_state()
        return decoration_state is not None and decoration_state.has_custom_decorations(holiday_id)

    def handle_lot_owner_changed(self, zone_id, household):
        state = self.get_neighborhood_state_for_zone(zone_id)
        if state is None:
            return
        lot = state.get_deco_lot_by_zone_id(zone_id)
        if lot is None:
            decorations_logger.error('Could not find decorated lot info for zone {}', zone_id)
            return
        lot.on_household_owner_changed(household)

    def _update_current_lot_statistic(self):
        if self.LOT_DECORATED_STATISTIC is None:
            return
        zone = services.current_zone()
        lot = zone.lot
        neighborhood_state = self.get_neighborhood_state_for_zone(zone.id)
        if neighborhood_state is None:
            return
        lot_decorated_state = neighborhood_state.get_deco_lot_by_zone_id(zone.id)
        lot.set_stat_value(self.LOT_DECORATED_STATISTIC, 1 if lot_decorated_state.is_decorated else 0)

    def apply_decoration_for_holiday(self, decoration_resource, decoration_location, holiday_id):
        if decoration_location not in decoration_resource.available_locations:
            decorations_logger.warn('{} not in available locations for {}', decoration_location, decoration_resource)
        deco_lot = self._get_active_lot_decoration_state()
        if deco_lot is None:
            return
        deco_lot.switch_to_appropriate_type(self._get_decoration_provider(holiday_id), None)
        deco_lot.apply_decoration(decoration_resource, decoration_location)
        deco_lot.resend_client_decoration_state(client_decoration_params=self.PLAYER_DECORATION_PARAMS)
        self._update_current_lot_statistic()

    def remove_decoration_for_holiday(self, decoration_location, holiday_id):
        deco_lot = self._get_active_lot_decoration_state()
        if deco_lot is None:
            return
        deco_lot.switch_to_appropriate_type(self._get_decoration_provider(holiday_id), None)
        deco_lot.remove_decoration(decoration_location)
        deco_lot.resend_client_decoration_state(client_decoration_params=self.PLAYER_DECORATION_PARAMS)
        self._update_current_lot_statistic()

    def reset_decoration_to_holiday_default(self, holiday_id):
        deco_lot = self._get_active_lot_decoration_state()
        if deco_lot is None:
            return
        deco_lot.switch_to_appropriate_type(self._get_decoration_provider(holiday_id), None)
        deco_lot.reset_decorations()
        deco_lot.resend_client_decoration_state(client_decoration_params=self.PLAYER_DECORATION_PARAMS)
        self._update_current_lot_statistic()

    def request_holiday_decorations(self, holiday_drama_node, from_load=False):
        self._active_requests[holiday_drama_node] = HolidayDecorationRequest(holiday_drama_node)
        if not from_load:
            self._handle_highest_priority_request()

    def cancel_decoration_requests_for(self, requester):
        if requester in self._active_requests:
            del self._active_requests[requester]
        if services.current_zone().is_zone_shutting_down:
            return
        self._handle_highest_priority_request()

    def _get_highest_priority_request(self):
        highest_priority_request = max(self._active_requests.values(), key=operator.attrgetter('priority'))
        return highest_priority_request

    def _handle_highest_priority_request(self):
        highest_priority_request = self._get_highest_priority_request()
        self._process_decoration_request(highest_priority_request)

    def _process_decoration_request(self, request, decorate_immediately=False):
        self.decorate_neighborhood_for_holiday(request.provided_type, decorate_immediately=decorate_immediately)

    def decorate_neighborhood_for_holiday(self, holiday_id, decorate_immediately=False, preset_override=None):
        neighborhood_decoration_state = self.get_neighborhood_state_for_zone(services.current_zone_id())
        if neighborhood_decoration_state is None:
            return
        holiday_provider = self._get_decoration_provider(holiday_id)
        for lot in neighborhood_decoration_state.lots:
            if lot.is_owned_by_active_household():
                pass
            else:
                resolver = SingleSimResolver(None, additional_participants={ParticipantType.PickedZoneId: (lot.zone_id,)})
                if any(resolver(test) for test in self.NON_DECORATABLE_TESTS):
                    decoration_provider = DEFAULT_DECORATION_PROVIDER
                else:
                    decoration_provider = holiday_provider
                lot.switch_to_appropriate_type(decoration_provider, DECORATE_IMMEDIATELY if decorate_immediately else self.AUTO_DECORATION_PARAMS, preset_override=preset_override)
        self._update_current_lot_statistic()
        self._world_decorations_set[neighborhood_decoration_state.world_id] = holiday_provider.decoration_type_id

    def decorate_zone_for_holiday(self, zone_id, holiday_id, preset_override=None):
        neighborhood_decoration_state = self.get_neighborhood_state_for_zone(zone_id)
        if neighborhood_decoration_state is None:
            return
        lot = neighborhood_decoration_state.get_deco_lot_by_zone_id(zone_id)
        lot.switch_to_appropriate_type(self._get_decoration_provider(holiday_id), self.PLAYER_DECORATION_PARAMS, preset_override=preset_override)
        self._update_current_lot_statistic()

    def refresh_neighborhood_decorations(self):
        self._send_neighborhood_state_to_client()

    def get_lot_decorations_gsi_data(self):
        gsi_data = []
        for (world_id, neighborhood_state) in self._neighborhood_deco_state.items():
            for lot_info in neighborhood_state.lots:
                entry = {}
                entry['zone_id'] = str(hex(lot_info.zone_id))
                entry['world_id'] = str(hex(world_id))
                entry['deco_type_id'] = str(lot_info.deco_type_id)
                entry['owned_by_active_household'] = str(lot_info.is_owned_by_active_household())
                entry['preset'] = str(lot_info.visible_preset)
                entry['customized'] = str(lot_info.deco_state.customized)
                entry['current_lot'] = str(services.current_zone_id() == lot_info.zone_id)
                entry['Decorations'] = lot_info.deco_state.get_deco_state_gsi_data()
                gsi_data.append(entry)
        return gsi_data
