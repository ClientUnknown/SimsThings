from clubs.club_enums import ClubGatheringVibefrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableEnumEntryimport services
class SetClubGatheringVibe(BaseLootOperation):
    FACTORY_TUNABLES = {'vibe': TunableEnumEntry(description='\n            The vibe to set the gathering to.\n            ', tunable_type=ClubGatheringVibe, default=ClubGatheringVibe.NO_VIBE)}

    def __init__(self, vibe, **kwargs):
        super().__init__(**kwargs)
        self._vibe = vibe

    def _apply_to_subject_and_target(self, subject, target, resolver):
        club_service = services.get_club_service()
        if club_service is None:
            return
        subject_sim = subject.get_sim_instance()
        if subject_sim is None:
            return
        gathering = club_service.sims_to_gatherings_map.get(subject_sim)
        if gathering is None:
            return
        gathering.set_club_vibe(self._vibe)
