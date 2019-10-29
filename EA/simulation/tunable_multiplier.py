from _sims4_collections import frozendictfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantType, ParticipantTypeSinglefrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableList, TunableTuple, TunableRange, Tunable, TunableFactory, TunableVariant, TunablePackSafeReference, TunableEnumEntry, OptionalTunableimport servicesimport sims4
class TestedSum(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'base_value': Tunable(description='\n            The basic value to return if no modifiers are applied.\n            ', default=0, tunable_type=float), 'modifiers': TunableList(description='\n            A list of modifiers to add to Base Value.\n            ', tunable=TunableTuple(modifier=Tunable(description='\n                    The value to apply add to Base Value if the associated\n                    tests pass. Can be negative\n                    ', tunable_type=float, default=0), tests=TunableTestSet(description='\n                    A series of tests that must pass in order for the modifier\n                    to be applied.\n                    ')))}

    def get_max_modifier(self, participant_resolver):
        if not self.modifiers:
            return self.base_value
        max_value = sims4.math.NEG_INFINITY
        for mod in self.modifiers:
            if mod.tests.run_tests(participant_resolver):
                max_value = max(max_value, mod.modifier)
        max_value = max_value if max_value != sims4.math.NEG_INFINITY else 0
        return self.base_value + max_value

    def get_modified_value(self, participant_resolver):
        if not self.modifiers:
            return self.base_value
        return self.base_value + sum(mod.modifier for mod in self.modifiers if mod.tests.run_tests(participant_resolver))

def _get_tunable_multiplier_list_entry(**tuple_elements):
    return TunableList(description='\n        A list of multipliers to apply to base_value.\n        ', tunable=TunableTuple(multiplier=TunableRange(description='\n                The multiplier to apply to base_value if the associated\n                tests pass.\n                ', tunable_type=float, default=1, minimum=0), tests=TunableTestSet(description='\n                A series of tests that must pass in order for multiplier to\n                be applied.\n                '), **tuple_elements))

class TunableMultiplier(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'base_value': Tunable(description='\n            The basic value to return if no modifications are applied.\n            ', default=1, tunable_type=float), 'multipliers': _get_tunable_multiplier_list_entry()}
    ONE = None

    @TunableFactory.factory_option
    def multiplier_options(use_tooltip=False):
        tuple_elements = {}
        if use_tooltip:
            tuple_elements['tooltip'] = OptionalTunable(description='\n                                            If enabled, provides a tooltip for\n                                            this entry if it is the first entry\n                                            to pass its tests.\n                                            \n                                            Future: Offer ways to combine tooltips in separated lists, etc.\n                                            ', tunable=TunableLocalizedStringFactory())
        else:
            tuple_elements['locked_args'] = {'tooltip': frozendict()}
        return {'multipliers': _get_tunable_multiplier_list_entry(**tuple_elements)}

    def get_multiplier_and_tooltip(self, participant_resolver):
        multiplier = self.base_value
        tooltip = None
        for multiplier_data in self.multipliers:
            if multiplier_data.tests.run_tests(participant_resolver):
                multiplier *= multiplier_data.multiplier
                if tooltip is None:
                    tooltip = multiplier_data.tooltip
        return (multiplier, tooltip)

    def get_multiplier(self, participant_resolver):
        (multiplier, _) = self.get_multiplier_and_tooltip(participant_resolver)
        return multiplier
TunableMultiplier.ONE = TunableMultiplier(base_value=1, multipliers=())
class TunableStatisticModifierCurve(HasTunableSingletonFactory, AutoFactoryInit):

    @TunableFactory.factory_option
    def axis_name_overrides(x_axis_name=None, y_axis_name=None):
        return {'multiplier': TunableVariant(description='\n                Define how the multiplier will be applied.\n                ', value_curve=TunableCurve(description='\n                    The multiplier will be determined by interpolating against a\n                    curve. The user-value is used. This means that a curve for\n                    skills should have levels as its x-axis.\n                    ', x_axis_name=x_axis_name, y_axis_name=y_axis_name), locked_args={'raw_value': None}, default='raw_value')}

    FACTORY_TUNABLES = {'statistic': TunablePackSafeReference(description="\n            The payout amount will be multiplied by this statistic's value.\n            ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'subject': TunableEnumEntry(description='\n            The participant to look for the specified statistic on.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'multiplier': TunableVariant(description='\n            Define how the multiplier will be applied.\n            ', value_curve=TunableCurve(description='\n                The multiplier will be determined by interpolating against a\n                curve. The user-value is used. This means that a curve for\n                skills should have levels as its x-axis.\n                '), locked_args={'raw_value': None}, default='raw_value')}

    def get_value(self, stat, sim):
        return stat.convert_to_user_value(stat.get_value())

    def get_multiplier(self, resolver, sim):
        subject = resolver.get_participant(participant_type=self.subject, sim=sim)
        if subject is not None:
            stat = subject.get_stat_instance(self.statistic)
            if stat is not None:
                value = self.get_value(stat, sim)
                if self.multiplier is not None:
                    return self.multiplier.get(value)
                else:
                    return value
        return 1.0

class TunableSkillModifierCurve(TunableStatisticModifierCurve):
    FACTORY_TUNABLES = {'statistic': TunablePackSafeReference(description="\n            The payout amount will be multiplied by this skill's value.\n            ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Skill',)), 'use_effective_skill_level': Tunable(description='\n            If checked, the effective skill level will be used.\n            ', tunable_type=bool, default=False)}

    def get_value(self, stat, sim):
        if self.use_effective_skill_level:
            return sim.get_effective_skill_level(stat)
        return super().get_value(stat, sim)

class TunableObjectCostModifierCurve(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The object whose cost you want to base the multiplier on.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'multiplier_curve': TunableCurve(description=' \n            The multiplier will be determined by interpolating against a curve.\n            The value of the subject in simoleons is used. This means that a \n            curve for cost should have value at its x-axis.\n            ', x_axis_name='Value', y_axis_name='Multiplier')}

    def get_multiplier(self, resolver, sim):
        subject = resolver.get_participant(participant_type=self.subject, sim=sim)
        if subject is not None:
            value = subject.current_value
            return self.multiplier_curve.get(value)
        return 1.0
