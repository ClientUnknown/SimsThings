from _weakrefset import WeakSetfrom event_testing.test_events import TestEventfrom objects import ALL_HIDDEN_REASONSfrom role.role_state import RoleStatefrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, TunableSet, TunableTuplefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommonfrom situations.situation_job import SituationJobfrom situations.situation_types import SituationCreationUIOptionimport servicesimport sims4.resources
class CaregiverSituation(SituationComplexCommon):
    CAREGIVER_EVENTS = (TestEvent.SituationStarted, TestEvent.AvailableDaycareSimsChanged)
    INSTANCE_TUNABLES = {'caregiver_data': TunableTuple(description='\n            The relationship bits to apply to Sims.\n            ', caregiver_bit=TunableReference(description="\n                The bit that is applied to Sims that are the situation owner's\n                Sim's caregiver. This is, for example, a bit on an adult\n                targeting a toddler.\n                ", manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT)), caregiver_job=SituationJob.TunableReference(description='\n                The situation job that caregivers are assigned when in this situation.\n                '), caregiver_rolestate=RoleState.TunableReference(description='\n                The role state that caregivers are assigned when in this situation.\n                '), care_dependent_bit=TunableReference(description='\n                The bit that is applied to Sims that are the situation owner\n                This is, for example, a bit on a toddler targeting an adult.\n                ', manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT))), 'caregiver_relationships': TunableSet(description='\n            A list of bits that make Sims primary caregivers. If any Sim with\n            any of these bits is instantiated and living in the same household \n            as the care dependent, they are considered caregivers.\n            \n            If no primary caregiver exists, and no caregiver service exists,\n            active TYAE Sims are made caregivers.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.RELATIONSHIP_BIT), pack_safe=True))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pending_caregivers = WeakSet()

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return ((cls.caregiver_data.caregiver_job, cls.caregiver_data.caregiver_rolestate),)

    def _is_valid_caregiver(self, care_dependent, caregiver, ignore_zone=False):
        if ignore_zone or care_dependent.zone_id != caregiver.zone_id:
            return False
        if caregiver.is_toddler_or_younger:
            return False
        if caregiver.is_pet:
            return False
        if care_dependent.household_id == caregiver.household_id and any(caregiver.relationship_tracker.has_bit(care_dependent.sim_id, rel_bit) for rel_bit in self.caregiver_relationships):
            return True
        else:
            daycare_service = services.daycare_service()
            if daycare_service is not None and daycare_service.is_daycare_service_npc_available(sim_info=caregiver, household=care_dependent.household):
                return True
        return False

    def _update_caregiver_status(self):
        care_dependent = self._guest_list.host_sim
        if care_dependent is None:
            return
        if care_dependent.household is None:
            return
        if care_dependent.is_being_destroyed:
            return
        available_sims = tuple(sim_info for sim_info in services.daycare_service().get_available_sims_gen())
        current_caregivers = set(self._situation_sims)
        for sim in current_caregivers:
            self._pending_caregivers.discard(sim)
        eligible_caregivers = set(sim_info for sim_info in available_sims if self._is_valid_caregiver(care_dependent, sim_info))
        if not eligible_caregivers:
            eligible_caregivers = set(sim_info for sim_info in care_dependent.household.can_live_alone_info_gen() if sim_info in available_sims)
        for sim in self._pending_caregivers:
            eligible_caregivers.discard(sim.sim_info)
        for potential_caregiver in tuple(eligible_caregivers):
            sim = potential_caregiver.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is None or sim.is_being_destroyed:
                eligible_caregivers.discard(potential_caregiver)
            elif sim in current_caregivers:
                pass
            else:
                self.invite_sim_to_job(sim, job=self.caregiver_data.caregiver_job)
                self._pending_caregivers.add(sim)
                care_dependent.relationship_tracker.add_relationship_bit(potential_caregiver.sim_id, self.caregiver_data.care_dependent_bit)
                potential_caregiver.relationship_tracker.add_relationship_bit(care_dependent.sim_id, self.caregiver_data.caregiver_bit)
        for sim in tuple(current_caregivers):
            if sim.sim_info not in eligible_caregivers:
                self._remove_caregiver_rel_bits(care_dependent, sim.sim_info)
                self.remove_sim_from_situation(sim)
                current_caregivers.discard(sim)

    def _remove_caregiver_rel_bits(self, care_dependent, other_sim_info=None):
        if other_sim_info is not None:
            care_dependent.relationship_tracker.remove_relationship_bit(other_sim_info.id, self.caregiver_data.care_dependent_bit)
            other_sim_info.relationship_tracker.remove_relationship_bit(care_dependent.id, self.caregiver_data.caregiver_bit)
        else:
            for relationship in care_dependent.relationship_tracker:
                other_sim_id = relationship.get_other_sim_id(care_dependent.sim_id)
                relationship.remove_bit(care_dependent.sim_id, other_sim_id, self.caregiver_data.care_dependent_bit)
                relationship.remove_bit(other_sim_id, care_dependent.sim_id, self.caregiver_data.caregiver_bit)

    def get_care_dependent_if_last_caregiver(self, sim_info, excluding_interaction_types=None):
        care_dependent = self._guest_list.host_sim
        if care_dependent.household.home_zone_id == services.current_zone_id():
            return
        if not care_dependent.relationship_tracker.has_relationship(sim_info.id):
            return
        for relationship in care_dependent.relationship_tracker:
            if relationship.get_other_sim_info(care_dependent.sim_id) is sim_info:
                if not relationship.has_bit(care_dependent.sim_id, self.caregiver_data.care_dependent_bit):
                    return
                    if relationship.has_bit(care_dependent.sim_id, self.caregiver_data.care_dependent_bit):
                        if excluding_interaction_types is not None:
                            other_sim = relationship.get_other_sim(care_dependent.sim_id)
                            if other_sim is None:
                                pass
                            elif other_sim.has_any_interaction_running_or_queued_of_types(excluding_interaction_types):
                                pass
                            else:
                                return
                        else:
                            return
            elif relationship.has_bit(care_dependent.sim_id, self.caregiver_data.care_dependent_bit):
                if excluding_interaction_types is not None:
                    other_sim = relationship.get_other_sim(care_dependent.sim_id)
                    if other_sim is None:
                        pass
                    elif other_sim.has_any_interaction_running_or_queued_of_types(excluding_interaction_types):
                        pass
                    else:
                        return
                else:
                    return
        return care_dependent

    def start_situation(self):
        self._update_caregiver_status()
        services.get_event_manager().register(self, self.CAREGIVER_EVENTS)
        return super().start_situation()

    def _destroy(self):
        services.get_event_manager().unregister(self, self.CAREGIVER_EVENTS)
        care_dependent = self._guest_list.host_sim
        self._remove_caregiver_rel_bits(care_dependent)
        super()._destroy()

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event in self.CAREGIVER_EVENTS:
            self._update_caregiver_status()
lock_instance_tunables(CaregiverSituation, exclusivity=BouncerExclusivityCategory.CAREGIVER, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0)