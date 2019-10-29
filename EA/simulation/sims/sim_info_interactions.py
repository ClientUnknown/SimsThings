from event_testing.results import TestResultfrom interactions import ParticipantTypefrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import Tunablefrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom venues.venue_constants import NPCSummoningPurposefrom world import regionimport services
class SimInfoInteraction(ImmediateSuperInteraction):
    INSTANCE_SUBCLASSES_ONLY = True

    def __init__(self, *args, sim_info=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim_info = sim_info

    @flexmethod
    def get_participants(cls, inst, participant_type:ParticipantType, sim=DEFAULT, target=DEFAULT, sim_info=None, **interaction_parameters) -> set:
        result = super(ImmediateSuperInteraction, inst if inst is not None else cls).get_participants(participant_type, sim=sim, target=target, **interaction_parameters)
        result = set(result)
        if participant_type & ParticipantType.Actor:
            if inst is not None:
                sim_info = inst._sim_info
            if sim_info is not None:
                result.add(sim_info)
        return tuple(result)
lock_instance_tunables(SimInfoInteraction, simless=True)
class BringHereInteraction(SimInfoInteraction):
    INSTANCE_TUNABLES = {'check_region_compatibility': Tunable(description='\n            If checked then we will check for region compatibility.\n            ', tunable_type=bool, default=True)}

    @classmethod
    def _test(cls, *args, sim_info=None, **kwargs):
        if sim_info.zone_id == services.current_zone_id():
            return TestResult(False, 'Cannot bring a sim to a zone that is already the current zone.')
        if cls.check_region_compatibility:
            current_region = services.current_region()
            sim_region = region.get_region_instance_from_zone_id(sim_info.zone_id)
            if sim_region is None or not sim_region.is_region_compatible(current_region):
                return TestResult(False, 'Cannot bring a sim to an incompatible region.')
        return super()._test(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        household = self._sim_info.household
        sim_infos_to_bring = services.daycare_service().get_abandoned_toddlers(household, (self._sim_info,))
        sim_infos_to_bring.append(self._sim_info)
        caretaker_zone_ids = set()
        offlot_pets = set()
        current_zone_id = services.current_zone_id()
        for sim_info in household:
            if sim_info is self._sim_info:
                pass
            elif sim_info.is_human:
                if sim_info.is_child_or_older:
                    caretaker_zone_ids.add(sim_info.zone_id)
                    if sim_info.zone_id == current_zone_id:
                        pass
                    elif sim_info.zone_id == sim_info.vacation_or_home_zone_id:
                        pass
                    else:
                        offlot_pets.add(sim_info)
            elif sim_info.zone_id == current_zone_id:
                pass
            elif sim_info.zone_id == sim_info.vacation_or_home_zone_id:
                pass
            else:
                offlot_pets.add(sim_info)
        for pet in offlot_pets:
            if pet.zone_id not in caretaker_zone_ids:
                sim_infos_to_bring.append(pet)
        services.current_zone().venue_service.venue.summon_npcs(tuple(sim_infos_to_bring), NPCSummoningPurpose.BRING_PLAYER_SIM_TO_LOT)

class SwitchToZoneInteraction(SimInfoInteraction):

    @classmethod
    def _test(cls, *args, sim_info=None, **kwargs):
        if sim_info.zone_id == 0:
            return TestResult(False, 'Cannot travel to a zone of 0.')
        if sim_info.zone_id == services.current_zone_id():
            return TestResult(False, 'Cannot switch to zone that is the current zone.')
        if sim_info in services.daycare_service().get_sim_infos_for_nanny(sim_info.household):
            return TestResult(False, 'Cannot switch to a sim that should be with the nanny.')
        return super()._test(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        self._sim_info.send_travel_switch_to_zone_op()
        return True
