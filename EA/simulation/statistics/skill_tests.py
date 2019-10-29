from event_testing.results import TestResult, TestResultNumericfrom event_testing.test_events import TestEvent, cached_testfrom interactions import ParticipantTypefrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import TunableFactory, TunableEnumEntry, TunableThreshold, Tunable, HasTunableSingletonFactory, AutoFactoryInit, TunableInterval, TunableVariant, OptionalTunable, TunableReferencefrom statistics.skill import Skillimport event_testing.test_baseimport servicesimport sims4import statistics.skillimport taglogger = sims4.log.Logger('SkillTests', default_owner='bosee')
class SkillTagThresholdTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.SkillLevelChange,)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'skill_tag': TunableEnumEntry(description='\n            What tag to test for.\n            ', tunable_type=tag.Tag, invalid_enums=(tag.Tag.INVALID,), default=tag.Tag.INVALID), 'skill_threshold': TunableThreshold(description='\n            The threshold level to test of each skill.\n            '), 'skill_quantity': Tunable(description='\n            The minimum number of skills at or above this level required to pass.\n            ', tunable_type=int, default=0), 'test_only_changed_skill': Tunable(description='\n            If checked then we will only test the skill that actually changed.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        if self.test_only_changed_skill:
            return {'test_targets': self.who, 'skill': event_testing.test_constants.FROM_EVENT_DATA}
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=None, skill=None):
        skill_tag = self.skill_tag
        threshold = self.skill_threshold
        quantity = self.skill_quantity
        for target in test_targets:
            if skill_tag is None:
                return TestResult(False, 'Tag not present or failed to load.')
            if target is None:
                logger.error('Trying to call SkillTagThresholdTest for skill_tag {} which has target as None.', skill_tag)
                return TestResult(False, 'Target({}) does not exist', self.who)
            if skill_tag is tag.Tag.INVALID:
                return TestResult(False, 'Tag test is set to INVALID, aborting test.')
            if threshold.value == 0 or quantity == 0:
                return TestResult(False, 'Threshold or Quantity not set, aborting test.')
            num_passed = 0
            highest_skill_value = 0
            if skill is not None:
                skills_to_check = (skill,)
            else:
                skills_to_check = target.all_skills()
            for stat in skills_to_check:
                if skill_tag in stat.tags:
                    curr_value = 0
                    if not stat.is_initial_value:
                        curr_value = stat.get_user_value()
                    if threshold.compare(curr_value):
                        num_passed += 1
                    elif curr_value > highest_skill_value:
                        highest_skill_value = curr_value
            if not num_passed >= quantity:
                if num_passed == 0 and quantity == 1:
                    return TestResultNumeric(False, 'The number of applicable skills: {} was not high enough to pass: {}.', num_passed, quantity, current_value=highest_skill_value, goal_value=threshold.value, is_money=False, tooltip=self.tooltip)
                return TestResultNumeric(False, 'The number of applicable skills: {} was not high enough to pass: {}.', num_passed, quantity, current_value=num_passed, goal_value=quantity, is_money=False, tooltip=self.tooltip)
        return TestResult.TRUE

    def validate_tuning_for_objective(self, objective):
        if self.skill_tag is tag.Tag.INVALID and self.skill_threshold.value == 0 and self.skill_quantity == 0:
            logger.error('Invalid tuning in objective {}.  One of the following must be true: Tag must not be INVALID, Threshold Value must be greater than 0, or Quantity must be greater than 0.', objective)

    def goal_value(self):
        if self.skill_quantity > 1:
            return self.skill_quantity
        return self.skill_threshold.value

class SkillThreshold(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'skill_threshold': TunableThreshold(description='\n            The Threshold for the skill level to be valid.\n            ', value=Tunable(description='\n                The value of a threshold.\n                ', tunable_type=int, default=0))}

    @property
    def skill_range_max(self):
        comparison_operator = sims4.math.Operator.from_function(self.skill_threshold.comparison)
        if comparison_operator == sims4.math.Operator.LESS_OR_EQUAL or comparison_operator == sims4.math.Operator.LESS or comparison_operator == sims4.math.Operator.EQUAL:
            return self.skill_threshold.value
        else:
            return statistics.skill.MAX_SKILL_LEVEL

    @property
    def skill_range_min(self):
        comparison_operator = sims4.math.Operator.from_function(self.skill_threshold.comparison)
        if comparison_operator == sims4.math.Operator.GREATER_OR_EQUAL or comparison_operator == sims4.math.Operator.GREATER or comparison_operator == sims4.math.Operator.EQUAL:
            return self.skill_threshold.value
        else:
            return 0

    def __call__(self, curr_value):
        if not self.skill_threshold.compare(curr_value):
            return TestResult(False, 'Skill failed threshold test.')
        return TestResult.TRUE

class SkillInterval(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'skill_interval': TunableInterval(description='\n            The range (inclusive) a skill level must be in to pass this test.\n            ', tunable_type=int, default_lower=1, default_upper=10, minimum=0, maximum=statistics.skill.MAX_SKILL_LEVEL)}
    __slots__ = ('skill_interval',)

    @property
    def skill_range_min(self):
        return self.skill_interval.lower_bound

    @property
    def skill_range_max(self):
        return self.skill_interval.upper_bound

    def __call__(self, curr_value):
        if curr_value < self.skill_interval.lower_bound or curr_value > self.skill_interval.upper_bound:
            return TestResult(False, 'skill level not in desired range.')
        return TestResult.TRUE

class SkillRangeTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of this test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'skill': Skill.TunablePackSafeReference(description='\n            The skill to test against. \n            \n            Should the Sim not have the specified skill, or should the skill not\n            be available because of pack restrictions, this Sim will be\n            considered at level 0.\n            '), 'skill_range': TunableVariant(description='\n            A skill range defined by either an interval or a threshold.\n            ', interval=SkillInterval.TunableFactory(), threshold=SkillThreshold.TunableFactory(), default='interval'), 'use_effective_skill_level': Tunable(description="\n            If checked, then instead of using the skill's actual level, the test\n            will use the skill's effective level for the purpose of satisfying\n            the specified criteria.\n            ", tunable_type=bool, needs_tuning=True, default=False)}
    __slots__ = ('subject', 'skill', 'skill_range', 'use_effective_skill_level')

    def get_expected_args(self):
        return {'test_targets': self.subject}

    @property
    def skill_range_min(self):
        return self.skill_range.skill_range_min

    @property
    def skill_range_max(self):
        max_possible_level = self.skill.get_max_skill_value()
        range_max = self.skill_range.skill_range_max
        if range_max > max_possible_level:
            logger.error("SkillRangeTest has a tuned skill range upper bound of {} that is higher than {}'s highest level of {}.", self.skill, range_max, max_possible_level, owner='rmccord')
        return range_max

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if self.skill is None:
                skill_value = 0
            else:
                skill_or_skill_type = target.get_statistic(self.skill, add=False) or self.skill
                if self.use_effective_skill_level and target.is_instanced():
                    skill_value = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS).get_effective_skill_level(skill_or_skill_type)
                else:
                    skill_value = skill_or_skill_type.get_user_value()
            if not self.skill_range(skill_value):
                return TestResult(False, 'skill level not in desired range.', tooltip=self.tooltip)
            return TestResult.TRUE
        return TestResult(False, 'Sim does not have required skill.', tooltip=self.tooltip)

class SkillAllUnlockedMaxedOut(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of this test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'negate': Tunable(description='\n        If this is true then it will negate the result of the test type. That \n        means the test will return true if there is at least one unlocked skill \n        that is not maxed out and false if all unlocked skills are maxed out.\n        ', tunable_type=bool, default=False)}
    __slots__ = ('subject', 'negate')

    def get_expected_args(self):
        return {'test_targets': self.subject}

    def __call__(self, test_targets=()):
        for target in test_targets:
            skills = target.all_skills()
            for skill in skills:
                if not skill.reached_max_level:
                    if self.negate:
                        return TestResult.TRUE
                    return TestResult(False, "At least one unlocked skill isn't max level", tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, 'All skills are max level', tooltip=self.tooltip)
        else:
            return TestResult.TRUE

class SkillHasUnlockedAll(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of this test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'include_unlocked_by_max': Tunable(description="\n        If this is true, the test will also test skills which will become\n        available when an available skill reaches max level (this is specified\n        in 'Skill Unlocks On Max' in skill tuning.\n        ", tunable_type=bool, default=True), 'negate': Tunable(description='\n        If this is true then it will negate the result of the test type. That\n        means the test will return true if there is at least one skill which is\n        not unlocked and false if all available skills are unlocked.\n        ', tunable_type=bool, default=False)}
    __slots__ = ('subject', 'negate', 'include_unlocked_by_max')

    def get_expected_args(self):
        return {'test_targets': self.subject}

    def __call__(self, test_targets=()):
        for target in test_targets:
            target_skills = target.all_skills()
            available_skills = set()
            skill_manager = services.get_instance_manager(sims4.resources.Types.STATISTIC)
            for skill_cls in skill_manager.get_ordered_types(only_subclasses_of=Skill):
                if not target.age not in skill_cls.ages:
                    if skill_cls.hidden:
                        pass
                    else:
                        available_skills.add(skill_cls)
                        if self.include_unlocked_by_max:
                            for unlocked_by_max_skill in skill_cls.skill_unlocks_on_max:
                                available_skills.add(unlocked_by_max_skill)
            for skill_cls in available_skills:
                if not any(type(skill) is skill_cls for skill in target_skills):
                    if self.negate:
                        return TestResult.TRUE
                    return TestResult(False, "At least one available skill isn't unlocked", tooltip=self.tooltip)
        if self.negate:
            return TestResult(False, 'All skills are unlocked', tooltip=self.tooltip)
        else:
            return TestResult.TRUE

class SkillInUseTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                Who or what to apply this test to.\n                ', tunable_type=participant_type_enum, default=participant_type_default)}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'skill': OptionalTunable(description='\n            Specify the skill to test against.\n            ', tunable=TunableReference(description='\n                "The skill to test against.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='Skill'), enabled_name='Specified_Skill', disabled_name='Any_Skill')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if self.skill is None:
                if target.current_skill_guid != 0:
                    return TestResult.TRUE
                    if target.current_skill_guid == self.skill.guid64:
                        return TestResult.TRUE
            elif target.current_skill_guid == self.skill.guid64:
                return TestResult.TRUE
        return TestResult(False, 'Failed SkillInUseTest', tooltip=self.tooltip)
