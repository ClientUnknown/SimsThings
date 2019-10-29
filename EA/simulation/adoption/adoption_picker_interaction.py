from adoption.adoption_liability import AdoptionLiabilityfrom adoption.adoption_tuning import _AdoptionSimDatafrom interactions import ParticipantTypefrom interactions.base.picker_interaction import PickerSuperInteractionMixinfrom interactions.base.picker_strategy import SimPickerEnumerationStrategyfrom interactions.base.super_interaction import SuperInteractionfrom interactions.interaction_finisher import FinishingTypefrom interactions.utils.tunable import TunableContinuationfrom sims.aging.aging_tuning import AgingTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableList, TunableTuple, TunableInterval, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom ui.ui_dialog_picker import TunablePickerDialogVariant, ObjectPickerTuningFlags, SimPickerRowimport element_utilsimport servicesimport sims4
class _AdoptionActionPushContinuation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'continuation': TunableContinuation(description='\n            A continuation that is pushed when the acting Sim is selected.\n            ', class_restrictions=('AdoptionSuperInteraction',), locked_args={'actor': ParticipantType.Actor})}

    def __call__(self, interaction, picked_sim_ids):
        interaction.interaction_parameters['picked_item_ids'] = frozenset(picked_sim_ids)
        interaction.push_tunable_continuation(self.continuation, picked_item_ids=picked_sim_ids)

class _AdoptionActionStartSituation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'situation_type': TunableReference(description='\n            The situation to start.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), class_restrictions=('SituationComplexAdoption',)), 'adoptee_situation_job': TunableReference(description='\n            The job given to the Sim who is going to be adopted.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))}

    def __call__(self, interaction, picked_sim_ids):
        guest_list = SituationGuestList(invite_only=True)
        adoption_service = services.get_adoption_service()
        for sim_id in picked_sim_ids:
            replacement_sim_info = adoption_service.convert_base_sim_info_to_full(sim_id)
            if replacement_sim_info is None:
                sim_id_to_adopt = sim_id
            else:
                sim_id_to_adopt = replacement_sim_info.sim_id
            guest_list.add_guest_info(SituationGuestInfo(sim_id_to_adopt, self.adoptee_situation_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, reservation=True))
        services.get_zone_situation_manager().create_situation(self.situation_type, guest_list=guest_list, user_facing=False)

class AdoptionPickerSuperInteraction(SuperInteraction, PickerSuperInteractionMixin):
    INSTANCE_TUNABLES = {'picker_dialog': TunablePickerDialogVariant(description='\n            The Sim picker to use to show Sims eligible for adoption.\n            ', available_picker_flags=ObjectPickerTuningFlags.SIM, tuning_group=GroupNames.PICKERTUNING), 'picker_entries': TunableList(description='\n            A list of picker entries. For each Sim type (age/gender\n            combination), specify the ideal number of Sims in the picker.\n            ', tunable=TunableTuple(count=TunableInterval(description='\n                    Define the number of Sims that must match the specified\n                    creation data. The lower bound is the minimum required\n                    number. The upper bound is the ideal number.\n                    ', tunable_type=int, default_lower=1, default_upper=2, minimum=1), creation_data=_AdoptionSimData.TunableFactory()), tuning_group=GroupNames.PICKERTUNING), 'adoption_action': TunableVariant(description='\n            Define how the actual adoption is carried out.\n            ', continuation=_AdoptionActionPushContinuation.TunableFactory(), situation=_AdoptionActionStartSituation.TunableFactory(), default='continuation', tuning_group=GroupNames.PICKERTUNING)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, choice_enumeration_strategy=SimPickerEnumerationStrategy(), **kwargs)
        self._picked_sim_ids = ()

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.sim, target=self.target)
        yield from element_utils.run_child(timeline, element_utils.soft_sleep_forever())
        if not self._picked_sim_ids:
            return False
        self.adoption_action(self, self._picked_sim_ids)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        adoption_service = services.get_adoption_service()
        with adoption_service.real_sim_info_cache():
            for entry in inst_or_cls.picker_entries:
                for sim_info in adoption_service.get_sim_infos(entry.count, entry.creation_data.age, entry.creation_data.gender, entry.creation_data.species):
                    aging_data = AgingTuning.get_aging_data(sim_info.species)
                    age_transition_data = aging_data.get_age_transition_data(sim_info.age)
                    row_description = age_transition_data.age_trait.display_name(sim_info)
                    yield SimPickerRow(sim_id=sim_info.sim_id, tag=sim_info.sim_id, row_description=row_description)

    def _pre_perform(self, *args, **kwargs):
        if self.sim.household.free_slot_count == 0:
            self.cancel(FinishingType.FAILED_TESTS, cancel_reason_msg="There aren't any free household slots.")
            return
        return super()._pre_perform(*args, **kwargs)

    def _on_selected(self, picked_sim_ids):
        self._picked_sim_ids = picked_sim_ids
        household = self.sim.household
        count = len(self._picked_sim_ids)
        if count > household.free_slot_count:
            self._picked_sim_ids = ()
        if self._picked_sim_ids:
            self.add_liability(AdoptionLiability.LIABILITY_TOKEN, AdoptionLiability(household, self._picked_sim_ids))

    def on_multi_choice_selected(self, picked_sim_ids, **kwargs):
        self._on_selected(picked_sim_ids)
        self.trigger_soft_stop()

    def on_choice_selected(self, picked_sim_id, **kwargs):
        if picked_sim_id is not None:
            self._on_selected((picked_sim_id,))
        self.trigger_soft_stop()
lock_instance_tunables(AdoptionPickerSuperInteraction, pie_menu_option=None)