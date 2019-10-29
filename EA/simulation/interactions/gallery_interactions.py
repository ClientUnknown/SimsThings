from distributor.system import Distributorfrom event_testing.results import TestResultfrom objects.terrain import TerrainImmediateSuperInteractionfrom venues.venue_constants import VenueTuningimport distributor.opsimport servicesimport sims4.loglogger = sims4.log.Logger('GalleryInteractions')
class MoveInFromGallerySuperInteraction(TerrainImmediateSuperInteraction):

    @classmethod
    def _test_zone_id(cls, zone_id):
        if zone_id is None:
            return TestResult(False, 'Could not resolve into a valid zone id.')
        active_household = services.active_household()
        if zone_id == active_household.home_zone_id:
            return TestResult(False, "Cannot move sim into the active household's home zone.")
        if zone_id == services.current_zone_id():
            return TestResult(False, 'Cannot move Sim into the active zone.')
        plex_service = services.get_plex_service()
        if not plex_service.is_zone_an_apartment(zone_id, consider_penthouse_an_apartment=False):
            persistence_service = services.get_persistence_service()
            if persistence_service is None:
                return TestResult(False, 'Persistence service is not initialized.')
            zone_data = persistence_service.get_zone_proto_buff(zone_id)
            if zone_data is None:
                return TestResult(False, 'Could not resolve zone data.')
            lot_data = persistence_service.get_lot_data_from_zone_data(zone_data)
            if lot_data is None:
                return TestResult(False, 'Could not resolve lot data.')
            venue_type = services.get_instance_manager(sims4.resources.Types.VENUE).get(lot_data.venue_key)
            if venue_type is not VenueTuning.RESIDENTIAL_VENUE_TYPE:
                return TestResult(False, 'Only residential venues are eligible.')
        return TestResult.TRUE

    @classmethod
    def _get_zone_ids_from_context(cls, context):
        to_zone_id = context.pick.get_zone_id_from_pick_location()
        if to_zone_id is None:
            return (0, ())
        plex_service = services.get_plex_service()
        if not plex_service.is_zone_an_apartment(to_zone_id, consider_penthouse_an_apartment=False):
            return (to_zone_id, ())
        zone_ids = list(plex_service.get_plex_zones_in_group(to_zone_id))
        if services.current_zone_id() in zone_ids:
            return (to_zone_id, ())
        active_household_home_zone_id = services.active_household().home_zone_id
        if active_household_home_zone_id in zone_ids:
            zone_ids.remove(active_household_home_zone_id)
        return (0, zone_ids)

    @classmethod
    def _test(cls, target, context, **kwargs):
        (solo_zone_id, zone_ids) = cls._get_zone_ids_from_context(context)
        if solo_zone_id:
            if not cls._test_zone_id(solo_zone_id):
                return TestResult(False, 'Selected zone is not eligible.')
        elif not any(cls._test_zone_id(zone_id) for zone_id in zone_ids):
            return TestResult(False, 'No selected zone is eligible.')
        return TestResult.TRUE

    def _run_interaction_gen(self, timeline):
        if services.get_persistence_service().is_save_locked():
            return
        (solo_zone_id, zone_ids) = self._get_zone_ids_from_context(self.context)
        persistence_service = services.get_persistence_service()
        household_id = persistence_service.get_household_id_from_zone_id(solo_zone_id)
        household = services.household_manager().get(household_id)
        num_household_sims = len(household) if household is not None else 0
        op = distributor.ops.MoveHouseholdIntoLotFromGallery(household_id=household_id, num_household_sims=num_household_sims, plex_zone_ids=zone_ids, zone_id=solo_zone_id)
        Distributor.instance().add_op(self.sim, op)
