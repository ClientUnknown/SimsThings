from interactions import ParticipantTypefrom interactions.base.super_interaction import SuperInteractionfrom interactions.utils.pregnancy_interactions import NameOffspringSuperInteractionMixinfrom sims.baby.baby_utils import assign_bassinet_for_baby, create_and_place_babyfrom sims.pregnancy.pregnancy_tracker import PregnancyTrackerfrom sims.sim_dialogs import SimPersonalityAssignmentDialogfrom sims.sim_info_types import Agefrom sims.sim_spawner import SimSpawnerfrom sims4.utils import flexmethodfrom ui.ui_dialog import PhoneRingTypefrom ui.ui_dialog_generic import TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAMEimport element_utilsimport interactionsimport services
class AdoptionSuperInteraction(SuperInteraction, NameOffspringSuperInteractionMixin):
    INSTANCE_TUNABLES = {'dialog': SimPersonalityAssignmentDialog.TunableFactory(description="\n            The dialog that is displayed (and asks for the player to enter a\n            first name and last name) before assigning the Sim to their\n            household.\n            \n            An additional token is passed in: the adopted Sim's data.\n            ", text_inputs=(TEXT_INPUT_FIRST_NAME, TEXT_INPUT_LAST_NAME), locked_args={'phone_ring_type': PhoneRingType.NO_RING})}

    @flexmethod
    def get_participants(cls, inst, participant_type, *args, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if participant_type == ParticipantType.PickedSim:
            _interaction_parameters = inst.interaction_parameters if inst is not None else interaction_parameters
            adopted_sim_id = next(iter(_interaction_parameters.get('picked_item_ids')))
            adoption_service = services.get_adoption_service()
            adopted_sim_info = adoption_service.get_sim_info(adopted_sim_id)
            if adopted_sim_info is not None:
                return {adopted_sim_info}
        return super(__class__, inst_or_cls).get_participants(participant_type, *args, **interaction_parameters)

    def _pre_perform(self, *args, **kwargs):
        self.add_liability(interactions.rabbit_hole.RABBIT_HOLE_LIABILTIY, interactions.rabbit_hole.RabbitHoleLiability(self))
        return super()._pre_perform(*args, **kwargs)

    def _build_outcome_sequence(self, *args, **kwargs):
        sequence = super()._build_outcome_sequence(*args, **kwargs)
        return element_utils.build_critical_section(self._name_and_create_adoptee_gen, sequence)

    def _get_name_dialog(self):
        adopted_sim_info = self.get_participant(ParticipantType.PickedSim)
        return self.dialog(self.sim, assignment_sim_info=adopted_sim_info, resolver=self.get_resolver())

    def _name_and_create_adoptee_gen(self, timeline):
        adopted_sim_info = self.get_participant(ParticipantType.PickedSim)
        if adopted_sim_info is None:
            return False
        last_name = SimSpawner.get_last_name(self.sim.last_name, adopted_sim_info.gender, adopted_sim_info.species)
        result = yield from self._do_renames_gen(timeline, (adopted_sim_info,), additional_tokens=(last_name,))
        if not result:
            return result
        parent_a = self.sim.sim_info
        parent_b = services.sim_info_manager().get(parent_a.spouse_sim_id)
        adoption_service = services.get_adoption_service()
        adoption_service.remove_sim_info(adopted_sim_info)
        (adopted_sim_info, _) = adoption_service.create_adoption_sim_info(adopted_sim_info, household=parent_a.household, account=parent_a.account, zone_id=parent_a.household.home_zone_id)
        PregnancyTracker.initialize_sim_info(adopted_sim_info, parent_a, parent_b)
        self.interaction_parameters['picked_item_ids'] = {adopted_sim_info.sim_id}
        services.daycare_service().exclude_sim_from_daycare(adopted_sim_info)
        if adopted_sim_info.age == Age.BABY:
            adopted_sim_info.set_zone_on_spawn()
            if not assign_bassinet_for_baby(adopted_sim_info):
                create_and_place_baby(adopted_sim_info)
        else:
            SimSpawner.spawn_sim(adopted_sim_info, sim_position=self.sim.position)
        return True
