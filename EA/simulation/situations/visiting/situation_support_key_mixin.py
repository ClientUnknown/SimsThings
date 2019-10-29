from relationships.global_relationship_tuning import RelationshipGlobalTuningfrom sims4.tuning.tunable import TunableEnumEntry, Tunablefrom venues.venue_constants import NPCSummoningPurposeimport services
class SituationSupportKeyMixin:
    SUMMONING_PURPOSE = TunableEnumEntry(description='\n        The Summoning purpose associated with a keyholder letting themselves\n        into a residential lot.\n        ', tunable_type=NPCSummoningPurpose, default=NPCSummoningPurpose.DEFAULT)
    INSTANCE_TUNABLES = {'support_given_keys': Tunable(description='\n            If enabled, keyholders who are put into this situation will be\n            "summoned" with a keyholder summoning purpose.  What this summoning\n            does is up to venue tuning. A reasonable use of this is to pull \n            keyholders into a new situation to avoid them having to perform \n            actions like ringing a door bell. If disabled, keyholders won\'t be \n            treated differently.\n            ', tunable_type=bool, default=False)}

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        if self.support_given_keys:
            relationship_tracker = sim.sim_info.relationship_tracker
            for sim_info in services.active_household():
                if relationship_tracker.has_bit(sim_info.sim_id, RelationshipGlobalTuning.NEIGHBOR_GIVEN_KEY_RELATIONSHIP_BIT):
                    services.current_zone().venue_service.venue.summon_npcs((sim.sim_info,), self.SUMMONING_PURPOSE)
