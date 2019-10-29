from protocolbuffers import GameplaySaveData_pb2from apartments.landlord_tuning import LandlordTuningfrom distributor.shared_messages import IconInfoDatafrom relationships.relationship_track import RelationshipTrackfrom sims4.common import Packfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyimport persistence_error_typesimport servicesimport sims4.loglogger = sims4.log.Logger('LandlordService', default_owner='rmccord')
class LandlordService(Service):

    def __init__(self):
        super().__init__()
        self._landlord_id = None

    @classproperty
    def required_packs(cls):
        return (Pack.EP03,)

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_LANDLORD_SERVICE

    def save(self, save_slot_data=None, **__):
        if self._landlord_id is None:
            return
        landlord_proto = GameplaySaveData_pb2.PersistableLandlordService()
        landlord_proto.landlord_id = self._landlord_id
        save_slot_data.gameplay_data.landlord_service = landlord_proto

    def setup(self, save_slot_data=None, **__):
        if save_slot_data.gameplay_data.HasField('landlord_service'):
            self._landlord_id = save_slot_data.gameplay_data.landlord_service.landlord_id

    def get_landlord_sim_info(self):
        landlord_filter = LandlordTuning.LANDLORD_FILTER
        if landlord_filter is None:
            return
        if self._landlord_id is not None:
            if services.sim_filter_service().does_sim_match_filter(self._landlord_id, sim_filter=landlord_filter):
                return services.sim_info_manager().get(self._landlord_id)
            self._landlord_id = None
        landlords = services.sim_filter_service().submit_matching_filter(sim_filter=landlord_filter, number_of_sims_to_find=1, allow_instanced_sims=True, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
        if landlords:
            landlord_sim_info = landlords[0].sim_info
            self._landlord_id = landlord_sim_info.id
        else:
            landlord_sim_info = None
        return landlord_sim_info

    def get_existing_landlord_sim_info(self):
        if self._landlord_id is not None:
            return services.sim_info_manager().get(self._landlord_id)
        landlord_filter = LandlordTuning.LANDLORD_FILTER
        if landlord_filter is None:
            return
        landlords = services.sim_filter_service().submit_filter(sim_filter=landlord_filter, callback=None, allow_yielding=False, gsi_source_fn=self.get_sim_filter_gsi_name)
        if landlords:
            landlord_sim_info = landlords[0].sim_info
            self._landlord_id = landlord_sim_info.id
        else:
            landlord_sim_info = None
        return landlord_sim_info

    def get_sim_filter_gsi_name(self):
        return str(self)

    def on_all_households_and_sim_infos_loaded(self, client):
        plex_service = services.get_plex_service()
        households = {services.owning_household_of_active_lot(), services.active_household()}
        households.discard(None)
        if any(plex_service.is_zone_a_plex(household.home_zone_id) for household in households):
            landlord_sim_info = self.get_landlord_sim_info()
            if landlord_sim_info is None:
                logger.error('Unable to create landlord for owned apartment', owner='nabaker')
                return
        else:
            landlord_sim_info = self.get_existing_landlord_sim_info()
            if landlord_sim_info is None or landlord_sim_info.relationship_tracker is None:
                return
        for household in households:
            home_zone_is_plex = plex_service.is_zone_a_plex(household.home_zone_id)
            self.setup_household_relationships(landlord_sim_info, household, home_zone_is_plex=home_zone_is_plex)

    def setup_household_relationships(self, landlord_sim_info, household, home_zone_is_plex=False):
        for sim_info in household:
            if home_zone_is_plex:
                sim_info.relationship_tracker.get_relationship_track(landlord_sim_info.id, RelationshipTrack.FRIENDSHIP_TRACK, add=True)
                landlord_sim_info.relationship_tracker.get_relationship_track(sim_info.id, RelationshipTrack.FRIENDSHIP_TRACK, add=True)
                sim_info.relationship_tracker.add_relationship_bit(landlord_sim_info.id, LandlordTuning.LANDLORD_REL_BIT, force_add=True)
                landlord_sim_info.relationship_tracker.add_relationship_bit(sim_info.id, LandlordTuning.TENANT_REL_BIT, force_add=True)
            else:
                sim_info.relationship_tracker.remove_relationship_bit(landlord_sim_info.id, LandlordTuning.LANDLORD_REL_BIT)
                landlord_sim_info.relationship_tracker.remove_relationship_bit(sim_info.id, LandlordTuning.TENANT_REL_BIT)

    def on_loading_screen_animation_finished(self):
        household = services.active_household()
        plex_service = services.get_plex_service()
        if household is not None and (household.has_home_zone_been_active() or plex_service.is_zone_an_apartment(household.home_zone_id, consider_penthouse_an_apartment=False)):
            active_sim = services.get_active_sim()
            landlord_sim_info = self.get_landlord_sim_info()
            if active_sim is not None and landlord_sim_info is not None:
                dialog = LandlordTuning.LANDLORD_FIRST_PLAY_RENT_REMINDER_NOTIFICATION(active_sim)
                dialog.show_dialog(icon_override=IconInfoData(obj_instance=landlord_sim_info))
