from event_testing.resolver import SingleSimResolver, SingleObjectResolverfrom interactions.aop import AffordanceObjectPairfrom interactions.base.super_interaction import SuperInteractionfrom interactions.social.social_super_interaction import SocialSuperInteractionfrom interactions.utils.outcome import TunableOutcomefrom objects.object_tests import ObjectCriteriaTestfrom objects.slot_tests import TunableSlotTestfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.tunable import TunableList, TunableTuple, OptionalTunable, TunableVariantfrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom statistics.skill import Skillimport event_testing.tests
class TunableObjectTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableVariant(slot_test=TunableSlotTest()), **kwargs)

class ObjectCriteriaAndSpecificTests(ObjectCriteriaTest):
    FACTORY_TUNABLES = {'additional_object_tests': TunableObjectTestSet(description='\n            If checked, any craftable object (such as a painting) must be finished\n            for it to be considered.\n            ')}
    __slots__ = ('additional_object_tests',)

    def get_total_value_and_number_of_matches(self, active_household_id, active_sim_id, current_zone, objects_to_test, positional_relationship_participants):
        number_of_matches = 0
        total_value = 0
        for obj in objects_to_test:
            if self.object_meets_criteria(obj, active_household_id, active_sim_id, current_zone, positional_relationship_participants=positional_relationship_participants):
                if self.additional_object_tests:
                    resolver = SingleObjectResolver(obj)
                    if not self.additional_object_tests.run_tests(resolver):
                        pass
                    else:
                        number_of_matches += 1
                        total_value += obj.depreciated_value if self.use_depreciated_values else obj.catalog_value
                else:
                    number_of_matches += 1
                    total_value += obj.depreciated_value if self.use_depreciated_values else obj.catalog_value
        return (total_value, number_of_matches)

class SkillBasedMultiInteraction(SocialSuperInteraction):
    INSTANCE_TUNABLES = {'skill_interactions': TunableList(description='\n            For each item in this list, if the actor has the skill, and the\n            object criteria test passes, a new interaction will be generated on\n            the Sim.\n            ', tunable=TunableTuple(description='\n                If the actor has the skill, and the object criteria test passes,\n                a new interaction will be generated on the Sim.\n                ', skill=Skill.TunablePackSafeReference(description='\n                    If the actor of the interaction has this skill, the Interaction Data will be\n                    used to generate interactions on the actor.\n                    '), object_criteria=OptionalTunable(ObjectCriteriaAndSpecificTests.TunableFactory(description='\n                    If enabled, the object criteria test must also pass for the\n                    Interaction Data to generate interactions on the actor. \n                    ')), interaction_data=TunableList(TunableTuple(description='\n                    The data used to generate interactions on the actor.,\n                    ', interaction_name=TunableLocalizedStringFactory(description='\n                        The name given to the generated interaction.\n                        '), outcome=TunableOutcome(description='\n                        The outcome to use for the generated interaction.\n                        ')))), tuning_group=GroupNames.CORE)}

    def __init__(self, *args, display_name_override=None, outcome_override=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._display_name_override = display_name_override
        self._outcome_override = outcome_override

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        resolver = SingleSimResolver(context.sim)
        for skill_interaction in cls.skill_interactions:
            skill_tracker = target.get_tracker(skill_interaction.skill)
            if skill_tracker is None:
                pass
            else:
                skill_stat = skill_tracker.get_statistic(skill_interaction.skill, add=False)
                if skill_stat is None:
                    pass
                elif not skill_interaction.object_criteria is not None or not resolver(skill_interaction.object_criteria):
                    pass
                else:
                    for interaction_datum in skill_interaction.interaction_data:
                        yield AffordanceObjectPair(cls, target, cls, None, display_name_override=interaction_datum.interaction_name, outcome_override=interaction_datum.outcome, **kwargs)

    def _build_outcome_sequence(self):
        if self._outcome_override is not None:
            return self._outcome_override.build_elements(self, update_global_outcome_result=True)

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, display_name_override=None, **interaction_parameters):
        if display_name_override is not None:
            return display_name_override()
        return super(SuperInteraction, inst if inst is not None else cls)._get_name(target=target, context=context, **interaction_parameters)
