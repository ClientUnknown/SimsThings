from protocolbuffers import Consts_pb2from build_buy import HouseholdInventoryFlagsfrom objects.object_manager import DistributableObjectManagerfrom sims4.utils import classpropertyfrom world import regionfrom world.region import Regionfrom world.travel_group import TravelGroupimport build_buyimport objects.systemimport persistence_error_typesimport servicesimport sims4.logimport sims4.telemetryimport telemetry_helperTELEMETRY_GROUP_TRAVEL_GROUPS = 'TGRP'TELEMETRY_HOOK_TRAVEL_GROUP_START = 'TGST'TELEMETRY_HOOK_TRAVEL_GROUP_END = 'TGEN'TELEMETRY_TRAVEL_GROUP_ID = 'tgid'TELEMETRY_TRAVEL_GROUP_ZONE_ID = 'tgzo'TELEMETRY_TRAVEL_GROUP_SIZE = 'tgsz'TELEMETRY_TRAVEL_GROUP_DURATION = 'tgdu'travel_group_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_TRAVEL_GROUPS)logger = sims4.log.Logger('TravelGroupManager')
class TravelGroupManager(DistributableObjectManager):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rented_zones = {}

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_TRAVEL_GROUP_MANAGER

    def is_current_zone_rented(self):
        return services.current_zone_id() in self._rented_zones.keys()

    def is_zone_rentable(self, zone_id):
        return zone_id not in self._rented_zones.keys()

    def get_travel_group_by_sim_info(self, sim_info):
        return self.get(sim_info.travel_group_id)

    def get_travel_group_by_household(self, household):
        for sim_info in household.sim_info_gen():
            travel_group = self.get(sim_info.travel_group_id)
            if travel_group is not None:
                return travel_group

    def get_travel_group_by_sim_id(self, sim_id):
        sim_info = services.sim_info_manager().get(sim_id)
        if sim_info is not None or not sim_info.travel_group_id:
            return
        return self.get_travel_group_by_sim_info(sim_info)

    def get_travel_group_ids_in_region(self, region_id=None):
        region_id = region_id or services.current_region().guid64
        return (group.id for group in self.values() if region.get_region_instance_from_zone_id(group.zone_id).guid64 == region_id)

    def get_travel_group_by_zone_id(self, zone_id):
        for travel_group in self.values():
            if travel_group.zone_id == zone_id:
                return travel_group

    def create_travel_group_and_rent_zone(self, sim_infos, zone_id, played, create_timestamp, end_timestamp, cost=0):
        setup_alarms = not played
        travel_group = TravelGroup(played=played, create_timestamp=create_timestamp, end_timestamp=end_timestamp, setup_alarms=setup_alarms)
        result = self.rent_zone(zone_id, travel_group)
        if not (result and sim_infos):
            return False
        self.add(travel_group)
        for sim_info in sim_infos:
            travel_group.add_sim_info(sim_info)
        if played:
            leader_sim_info = services.active_sim_info()
            if leader_sim_info not in sim_infos:
                leader_sim_info = sim_infos[0]
            services.active_household().funds.try_remove(cost, reason=Consts_pb2.FUNDS_MONEY_VACATION, sim=services.get_active_sim())
            with telemetry_helper.begin_hook(travel_group_telemetry_writer, TELEMETRY_HOOK_TRAVEL_GROUP_START, sim_info=leader_sim_info) as hook:
                hook.write_int(TELEMETRY_TRAVEL_GROUP_ID, travel_group.id)
                hook.write_int(TELEMETRY_TRAVEL_GROUP_ZONE_ID, zone_id)
                hook.write_int(TELEMETRY_TRAVEL_GROUP_SIZE, len(travel_group))
                hook.write_int(TELEMETRY_TRAVEL_GROUP_DURATION, int(travel_group.duration_time_span.in_minutes()))
        return True

    def destroy_travel_group_and_release_zone(self, travel_group, last_sim_info=None, return_objects=False):
        if travel_group.played:
            if last_sim_info is None:
                leader_sim_info = services.active_sim_info()
                if leader_sim_info not in travel_group:
                    leader_sim_info = next(iter(travel_group), None)
            else:
                leader_sim_info = last_sim_info
            with telemetry_helper.begin_hook(travel_group_telemetry_writer, TELEMETRY_HOOK_TRAVEL_GROUP_END, sim_info=leader_sim_info) as hook:
                hook.write_int(TELEMETRY_TRAVEL_GROUP_ID, travel_group.id)
                hook.write_int(TELEMETRY_TRAVEL_GROUP_ZONE_ID, travel_group.zone_id)
                hook.write_int(TELEMETRY_TRAVEL_GROUP_SIZE, len(travel_group))
                hook.write_int(TELEMETRY_TRAVEL_GROUP_DURATION, int(travel_group.duration_time_span.in_minutes()))
        for sim_info in tuple(travel_group):
            travel_group.remove_sim_info(sim_info, destroy_on_empty=False)
        self.release_zone(travel_group.zone_id)
        services.get_persistence_service().del_travel_group_proto_buff(travel_group.id)
        services.travel_group_manager().remove(travel_group)
        if return_objects:
            self.return_objects_left_in_destination_world()
        return True

    def rent_zone(self, zone_id, travel_group):
        if not self.is_zone_rentable(zone_id):
            existing_travel_group = self._rented_zones[zone_id]
            if existing_travel_group.played:
                return False
            self.destroy_travel_group_and_release_zone(existing_travel_group, return_objects=False)
        travel_group.rent_zone(zone_id)
        self._rented_zones[zone_id] = travel_group
        return True

    def release_zone(self, zone_id):
        travel_group = self._rented_zones.pop(zone_id, False)
        if not travel_group:
            return False
        return True

    def get_rentable_zones(self):
        return []

    def return_objects_left_in_destination_world(self):
        zone = services.current_zone()
        neighborhood_protocol_buffer = services.get_persistence_service().get_neighborhood_proto_buff(zone.neighborhood_id)
        region_tuning = Region.REGION_DESCRIPTION_TUNING_MAP.get(neighborhood_protocol_buffer.region_id)
        if region_tuning is not None and region_tuning.store_travel_group_placed_objects:
            return
        current_zone_id = zone.id
        household_manager = services.household_manager()
        save_game_protocol_buffer = services.get_persistence_service().get_save_game_data_proto()
        for clean_up_save_data in save_game_protocol_buffer.destination_clean_up_data:
            if clean_up_save_data.travel_group_id in self:
                pass
            elif clean_up_save_data.household_id not in household_manager:
                clean_up_save_data.household_id = 0
            else:
                for obj_clean_up_data in clean_up_save_data.object_clean_up_data_list:
                    obj_data = obj_clean_up_data.object_data

                    def post_create_old_object(created_obj):
                        created_obj.load_object(obj_data)
                        build_buy.move_object_to_household_inventory(created_obj, failure_flags=HouseholdInventoryFlags.DESTROY_OBJECT)

                    definition_id = build_buy.get_vetted_object_defn_guid(current_zone_id, obj_data.object_id, obj_data.guid or obj_data.type)
                    if definition_id is None:
                        pass
                    else:
                        objects.system.create_object(definition_id, obj_id=obj_data.object_id, loc_type=obj_data.loc_type, post_add=post_create_old_object)
                clean_up_save_data.household_id = 0

    def on_all_households_and_sim_infos_loaded(self, client):
        self.load_travel_groups()

    def clean_objects_left_in_destination_world(self):
        zone = services.current_zone()
        current_zone_id = zone.id
        open_street_id = zone.open_street_id
        travel_group_manager = services.travel_group_manager()
        clean_up_data_indexes_to_remove = []
        object_manager = services.object_manager()
        save_game_protocol_buffer = services.get_persistence_service().get_save_game_data_proto()
        for (clean_up_index, clean_up_save_data) in enumerate(save_game_protocol_buffer.destination_clean_up_data):
            if clean_up_save_data.travel_group_id in travel_group_manager:
                pass
            elif clean_up_save_data.household_id != 0:
                pass
            else:
                object_indexes_to_delete = []
                for (index, object_clean_up_data) in enumerate(clean_up_save_data.object_clean_up_data_list):
                    if not object_clean_up_data.zone_id == current_zone_id:
                        if object_clean_up_data.world_id == open_street_id:
                            obj = object_manager.get(object_clean_up_data.object_data.object_id)
                            if obj is not None:
                                obj.destroy(source=self, cause='Destination world clean up.')
                            object_indexes_to_delete.append(index)
                    obj = object_manager.get(object_clean_up_data.object_data.object_id)
                    if obj is not None:
                        obj.destroy(source=self, cause='Destination world clean up.')
                    object_indexes_to_delete.append(index)
                if len(object_indexes_to_delete) == len(clean_up_save_data.object_clean_up_data_list):
                    clean_up_save_data.ClearField('object_clean_up_data_list')
                else:
                    for index in reversed(object_indexes_to_delete):
                        del clean_up_save_data.object_clean_up_data_list[index]
                if len(clean_up_save_data.object_clean_up_data_list) == 0:
                    clean_up_data_indexes_to_remove.append(clean_up_index)
        for index in reversed(clean_up_data_indexes_to_remove):
            del save_game_protocol_buffer.destination_clean_up_data[index]

    def load_travel_groups(self):
        delete_group_ids = []
        for travel_group_proto in services.get_persistence_service().all_travel_group_proto_gen():
            travel_group_id = travel_group_proto.travel_group_id
            travel_group = self.get(travel_group_id)
            if travel_group is None:
                travel_group = self.load_travel_group(travel_group_proto)
            if travel_group is None:
                delete_group_ids.append(travel_group_id)
        for travel_group_id in delete_group_ids:
            services.get_persistence_service().del_travel_group_proto_buff(travel_group_id)

    def load_travel_group(self, travel_group_proto):
        travel_group = TravelGroup(setup_alarms=True)
        travel_group.load_data(travel_group_proto)
        logger.info('Travel Group loaded. id:{:10} #sim_infos:{:2}', travel_group.id, len(travel_group))
        if not travel_group.travel_group_size:
            return
        self.add(travel_group)
        self._rented_zones[travel_group.zone_id] = travel_group
        for sim_info in travel_group.sim_info_gen():
            sim_info.career_tracker.resend_at_work_infos()
        return travel_group

    def save(self, **kwargs):
        for travel_group in self.values():
            self.save_travel_group(travel_group)

    def save_travel_group(self, travel_group):
        persistence_service = services.get_persistence_service()
        travel_group_proto = persistence_service.get_travel_group_proto_buff(travel_group.id)
        if travel_group_proto is None:
            travel_group_proto = persistence_service.add_travel_group_proto_buff()
        travel_group.save_data(travel_group_proto)
