from event_testing.resolver import InteractionResolverfrom filters.tunable import FilterResultfrom interactions.base.picker_interaction import SimPickerInteraction, AutonomousSimPickerSuperInteractionfrom interactions.base.picker_strategy import SimPickerEnumerationStrategyfrom sims4.tuning.tunable import TunableList, TunableVariant, TunablePackSafeReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom situations.situation_by_definition_or_tags import SituationSearchByDefinitionOrTagsVariantfrom vet.vet_picker_strategy import VetCustomerPickerEnumerationStrategyimport servicesimport sims4
class SituationSimsPickerMixin:
    INSTANCE_TUNABLES = {'valid_situations': SituationSearchByDefinitionOrTagsVariant(description='\n            Situations where the guest list will be collected to populate the picker.\n            ', tuning_group=GroupNames.PICKERTUNING), 'job_filter': TunableList(description='\n            If provided, only looks for Sims with the specified jobs.\n            ', tunable=TunablePackSafeReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB)), tuning_group=GroupNames.PICKERTUNING)}
    REMOVE_INSTANCE_TUNABLES = ('sim_filter', 'sim_filter_household_override', 'sim_filter_requesting_sim', 'include_uninstantiated_sims', 'include_instantiated_sims', 'include_actor_sim', 'include_target_sim')

    @flexmethod
    def _get_valid_sim_choices_gen(cls, inst, target, context, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        for situation in cls.valid_situations.get_all_matching_situations():
            for sim in situation.all_sims_in_situation_gen():
                if not cls.job_filter or situation.get_current_job_for_sim(sim) not in cls.job_filter:
                    pass
                elif inst_or_cls.sim_tests:
                    if inst:
                        interaction_parameters = inst.interaction_parameters.copy()
                    else:
                        interaction_parameters = kwargs.copy()
                    interaction_parameters['picked_item_ids'] = {sim.sim_id}
                    resolver = InteractionResolver(cls, inst, target=target, context=context, **interaction_parameters)
                    if inst_or_cls.sim_tests.run_tests(resolver):
                        yield FilterResult(sim_info=sim.sim_info)
                        yield FilterResult(sim_info=sim.sim_info)
                else:
                    yield FilterResult(sim_info=sim.sim_info)

class SituationSimsPickerInteraction(SituationSimsPickerMixin, SimPickerInteraction):
    pass

class AutonomousSituationSimsPickerInteraction(SituationSimsPickerMixin, AutonomousSimPickerSuperInteraction):
    INSTANCE_TUNABLES = {'choice_strategy': TunableVariant(description='\n            Strategy to use for picking a Sim.\n            ', default='default_sim_picker', default_sim_picker=SimPickerEnumerationStrategy.TunableFactory(), vet_customer_picker=VetCustomerPickerEnumerationStrategy.TunableFactory(), tuning_group=GroupNames.PICKERTUNING)}
    REMOVE_INSTANCE_TUNABLES = ('test_compatibility',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, choice_enumeration_strategy=self.choice_strategy, **kwargs)
