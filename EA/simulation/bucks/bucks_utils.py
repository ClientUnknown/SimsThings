from bucks.bucks_enums import BucksType, BucksTrackerTypefrom sims4.tuning.tunable import TunableMapping, TunableEnumEntryimport services
class BucksUtils:
    BUCK_TYPE_TO_TRACKER_MAP = TunableMapping(description='\n        Maps a buck type to the tracker that uses that bucks type.\n        ', key_type=TunableEnumEntry(tunable_type=BucksType, default=BucksType.INVALID, invalid_enums=BucksType.INVALID, pack_safe=True), key_name='Bucks Type', value_type=BucksTrackerType, value_name='Bucks Tracker')

    @classmethod
    def get_tracker_for_bucks_type(cls, bucks_type, owner_id=None, add_if_none=False):
        bucks_tracker_type = BucksUtils.BUCK_TYPE_TO_TRACKER_MAP.get(bucks_type)
        if owner_id is None or bucks_tracker_type == BucksTrackerType.HOUSEHOLD:
            active_household = services.active_household()
            return active_household.bucks_tracker
        if bucks_tracker_type == BucksTrackerType.CLUB:
            club_service = services.get_club_service()
            if club_service is None:
                return
            club = club_service.get_club_by_id(owner_id)
            if club is not None:
                return club.bucks_tracker
        elif bucks_tracker_type == BucksTrackerType.SIM:
            sim_info = services.sim_info_manager().get(owner_id)
            if sim_info is not None:
                return sim_info.get_bucks_tracker(add_if_none=add_if_none)
