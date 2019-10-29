from event_testing.results import TestResult, TestResultNumericfrom event_testing.test_events import TestEvent, cached_testfrom interactions import ParticipantTypefrom objects import ALL_HIDDEN_REASONSfrom objects.object_tests import TunableObjectStateValueThresholdfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.math import Operatorfrom sims4.tuning.tunable import TunableFactory, TunableEnumEntry, Tunable, TunableList, TunableThreshold, TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableOperator, TunableReference, TunablePackSafeReference, TunableSet, OptionalTunable, TunableTuple, TunableRangeimport algosimport event_testing.test_baseimport servicesimport sims4.tuning.tunableimport statistics.statisticlogger = sims4.log.Logger('Tests', default_owner='mkartika')
class SpecifiedStatThresholdMixin:

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(participant_type_enum, participant_type_default, description='Who or what to apply this test to')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, safe_to_skip=True, **kwargs)

    def _get_make_true_value(self):
        if self.stat is not None:
            for value in algos.binary_walk_gen(list(range(int(self.stat.min_value), int(self.stat.max_value) + 1))):
                if self.threshold.compare(value):
                    return (TestResult.TRUE, value)
            operator_symbol = Operator.from_function(self.threshold.comparison).symbol
        return (TestResult(False, 'Could not find value to satisfy operation: {} {} {}', self.value.state, operator_symbol, self.value), None)

    def goal_value(self):
        return self.threshold.value

class _PointsValue(HasTunableSingletonFactory):

    def get_value(self, sim, stat):
        tracker = sim.get_tracker(stat)
        return tracker.get_value(stat)

    def validate(self, instance_class, stat):
        pass

class _UserValue(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'highest_level_reached_instead': Tunable(description="\n            If checked this will test against the highest level reached. This\n            currently only works with Ranked Statistics. Other statistics do\n            not have a notion of highest level reached. If we are using\n            something that doesn't support highest level reached it will \n            test against the current level instead.\n            ", tunable_type=bool, default=False)}

    def get_value(self, sim, stat):
        tracker = sim.get_tracker(stat)
        if self.highest_level_reached_instead:
            from statistics.ranked_statistic import RankedStatistic
            if issubclass(stat, (RankedStatistic,)):
                stat = tracker.get_statistic(stat)
                if stat is not None:
                    return stat.highest_level
        return tracker.get_user_value(stat)

    def validate(self, instance_class, stat):
        pass

class _RankValue(HasTunableSingletonFactory):

    def get_value(self, sim, stat):
        tracker = sim.get_tracker(stat)
        stat_inst = tracker.get_statistic(stat)
        if stat_inst is not None:
            return stat_inst.rank_level
        return stat.initial_rank

    def validate(self, instance_class, stat):
        from statistics.ranked_statistic import RankedStatistic
        if issubclass(stat, (RankedStatistic,)):
            return
        return 'Trying to do a Relative Stat Threshold Test using Rank instead of Value in {} but the stat {} is not a Ranked Statistic.'.format(instance_class, stat)

class StatThresholdTest(SpecifiedStatThresholdMixin, HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.SkillLevelChange, TestEvent.StatValueUpdate)

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.who == ParticipantType.Invalid or value.threshold is None:
            logger.error('Missing or invalid argument at {}: {}', instance_class, tunable_name)
        stat = value.stat
        if stat is not None:
            if 'Types.INTERACTION' in str(source) and stat.is_skill:
                threshold = value.threshold
                if threshold.value == 1.0 and threshold.comparison is sims4.math.Operator.GREATER_OR_EQUAL.function:
                    logger.error('StatThresholdTest for skill ({}) >= 1 is invalid in instance({}). Please remove the test.', stat, instance_class)
            error_str = value.score_to_use.validate(instance_class, stat)
            if error_str is not None:
                logger.error(error_str)

    FACTORY_TUNABLES = {'verify_tunable_callback': _verify_tunable_callback, 'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'stat': TunablePackSafeReference(description='\n            The stat we are operating on.\n            ', manager=services.statistic_manager()), 'threshold': TunableVariant(description='\n            The value or state threshold to test against.\n            ', state_value_threshold=TunableObjectStateValueThreshold(description='\n                The state threshold for this test.\n                '), value_threshold=TunableThreshold(description="\n                The threshold to control availability based on the statistic's\n                value.\n                "), default='value_threshold'), 'must_have_stat': Tunable(description='\n            Setting this to True (checked) will ensure that this test only\n            passes if the tested Sim actually has the statistic referenced. If\n            left False (unchecked), this test will evaluate as if the Sim had\n            the statistic at the value of 0\n            ', tunable_type=bool, default=False), 'score_to_use': TunableVariant(description='\n            Depending on the choice, this decides what value to use for the \n            threshold comparison.\n            ', points=_PointsValue.TunableFactory(description='\n                Use the raw points for the comparison in the test.\n                '), user_value=_UserValue.TunableFactory(description='\n                Use the user value for the comparison in the test.\n                '), rank=_RankValue.TunableFactory(description='\n                Use the rank value for the comparison in the test.\n                '), default='user_value')}
    __slots__ = ('who', 'stat', 'threshold', 'must_have_stat')

    def get_expected_args(self):
        return {'test_targets': self.who, 'statistic': event_testing.test_constants.FROM_EVENT_DATA}

    def get_test_events_to_register(self):
        return ()

    def get_custom_event_registration_keys(self):
        keys = [(TestEvent.SkillLevelChange, self.stat), (TestEvent.StatValueUpdate, self.stat)]
        return keys

    @cached_test
    def __call__(self, test_targets=(), statistic=None):
        if statistic is not None and self.stat is not statistic:
            return TestResult(False, 'Stat being looked for is not the stat that changed.')
        for target in test_targets:
            if target is None:
                logger.error('Trying to call StatThresholdTest on {} which is None', target)
                return TestResult(False, 'Target({}) does not exist', self.who)
            curr_value = 0
            if self.stat is not None:
                tracker = target.get_tracker(self.stat)
                stat_inst = tracker.get_statistic(self.stat)
                if not (self.stat.is_skill and stat_inst.is_initial_value):
                    curr_value = self.score_to_use.get_value(target, self.stat)
            else:
                stat_inst = None
            if stat_inst is None and self.must_have_stat:
                return TestResultNumeric(False, '{} Does not have stat: {}.', self.who.name, self.stat, current_value=curr_value, goal_value=self.threshold.value, is_money=False, tooltip=self.tooltip)
            if not self.threshold.compare(curr_value):
                operator_symbol = Operator.from_function(self.threshold.comparison).symbol
                return TestResultNumeric(False, '{} failed stat check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.stat, operator_symbol, self.threshold.value, curr_value, current_value=curr_value, goal_value=self.threshold.value, is_money=False, tooltip=self.tooltip)
        return TestResult.TRUE

    def __repr__(self):
        return 'Stat: {}, Threshold: {} on Subject {}'.format(self.stat, self.threshold, self.who)

    def validate_tuning_for_objective(self, objective):
        if self.stat is not None and not self.stat.valid_for_stat_testing:
            logger.error('Stat {} is not valid for testing in objective {}.', self.stat, objective)

class RelativeStatTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        stat = value.stat
        if stat is None:
            return
        target_stats = value.target_stats
        error_str = value.score_to_use.validate(instance_class, stat)
        if error_str is not None:
            logger.error(error_str)
        for target_stat in target_stats:
            if target_stat is None:
                pass
            else:
                error_str = value.score_to_use.validate(instance_class, target_stat)
                if error_str is not None:
                    logger.error(error_str)

    FACTORY_TUNABLES = {'verify_tunable_callback': _verify_tunable_callback, 'source': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor, invalid_enums=(ParticipantType.Invalid,)), 'target': TunableEnumEntry(description='\n            Who or what to use for the comparison\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'stat': TunablePackSafeReference(description='\n            The stat we are using for the comparison\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'target_stats': TunableList(description='\n            The stat on the target we want to compare against.\n            If there is more than one, all must pass the comparison.\n            If there is none, it compares the same stat.\n            ', tunable=TunablePackSafeReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))), 'comparison': TunableOperator(description='\n            The comparison to perform against the value. The test passes if (source_stat comparison target)\n            ', default=sims4.math.Operator.GREATER_OR_EQUAL), 'score_to_use': TunableVariant(description='\n            Depending on the choice, this decides what value to use for the \n            threshold comparison.\n            ', points=_PointsValue.TunableFactory(description='\n                Use the raw points for the comparison in the test.\n                '), user_value=_UserValue.TunableFactory(description='\n                Use the user value for the comparison in the test.\n                '), rank=_RankValue.TunableFactory(description='\n                Use the rank value for the comparison in the test.\n                '), default='user_value'), 'difference': Tunable(description='\n            The difference between the source and target stat in order to pass \n            the threshold. This value is added to the source stat value and the \n            threshold is checked against the resulting value.\n            ', tunable_type=int, default=0)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'source_objects': self.source, 'target_objects': self.target}

    @cached_test
    def __call__(self, source_objects=None, target_objects=None):
        if self.stat is None:
            return TestResult(False, 'Stat failed to load.')
        for source_obj in source_objects:
            if source_obj is None:
                logger.error('Trying to call RelativeStatThresholdTest on {} which is None for {}', source_obj)
                return TestResult(False, 'Target({}) does not exist', self.source)
            source_curr_value = self.score_to_use.get_value(source_obj, self.stat)
            source_curr_value += self.difference
            for target_obj in target_objects:
                if target_obj is None:
                    logger.error('Trying to call RelativeStatThresholdTest on {} which is None for {}', target_obj)
                    return TestResult(False, 'Target({}) does not exist', self.target)
                if self.target_stats:
                    for target_stat in self.target_stats:
                        target_curr_value = self.score_to_use.get_value(target_obj, target_stat)
                        threshold = sims4.math.Threshold(target_curr_value, self.comparison)
                        if not threshold.compare(source_curr_value):
                            operator_symbol = Operator.from_function(self.comparison).symbol
                            return TestResult(False, '{} failed relative stat check: {}.{} {} {} (current value: {})', self.source.name, target_obj.__class__.__name__, target_stat.__name__, operator_symbol, target_curr_value, source_curr_value)
                else:
                    target_curr_value = self.score_to_use.get_value(target_obj, self.stat)
                    threshold = sims4.math.Threshold(target_curr_value, self.comparison)
                    if not threshold.compare(source_curr_value):
                        operator_symbol = Operator.from_function(self.comparison).symbol
                        return TestResult(False, '{} failed relative stat check: {}.{} {} {} (current value: {})', self.source.name, target_obj.__class__.__name__, self.stat.__name__, operator_symbol, target_curr_value, source_curr_value, tooltip=self.tooltip)
        return TestResult.TRUE

class RankedStatThresholdTest(SpecifiedStatThresholdMixin, HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.RankedStatisticChange,)

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.who == ParticipantType.Invalid or value.threshold is None:
            logger.error('Missing or invalid argument at {}: {}', instance_class, tunable_name)
        ranked_stat = value.ranked_stat
        if ranked_stat is not None:
            from statistics.ranked_statistic import RankedStatistic
            if not issubclass(ranked_stat, (RankedStatistic,)):
                logger.error('Trying to Do a Ranked Stat Threshold Test in {} but the ranked_stat {} is not a Ranked Statistic.', instance_class, ranked_stat)

    FACTORY_TUNABLES = {'verify_tunable_callback': _verify_tunable_callback, 'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'ranked_stat': TunablePackSafeReference(description='\n            The ranked stat we are operating on.\n            ', manager=services.statistic_manager()), 'threshold': TunableVariant(description='\n            The value or state threshold to test against.\n            ', state_value_threshold=TunableObjectStateValueThreshold(description='\n                The state threshold for this test.\n                '), value_threshold=TunableThreshold(description="\n                The threshold to control availability based on the ranked\n                statistic's value.\n                "), default='value_threshold'), 'must_have_ranked_stat': Tunable(description='\n            Setting this to True (checked) will ensure that this test only\n            passes if the tested Sim actually has the ranked statistic \n            referenced. If left False (unchecked), this test will evaluate \n            as if the Sim had the ranked statistic at the value of 0\n            ', tunable_type=bool, default=False), 'test_against_highest_rank': Tunable(description='\n            When checked this test will only return True is the highest rank\n            achieved is in the threshold specified, and not the current rank.\n            ', tunable_type=bool, default=False), 'num_participants': OptionalTunable(description='\n            If disabled, all participants must pass this stat test.\n            If enabled, we test against this number for the number of participants\n            that need this value of stat to pass. \n            ', tunable=TunableThreshold(description='\n                The threshold of the number of participants who must meet the \n                criteria individually.\n                '), disabled_name='all_participants')}
    __slots__ = ('who', 'ranked_stat', 'threshold', 'must_have_ranked_stat')

    def get_expected_args(self):
        return {'test_targets': self.who, 'ranked_statistic': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, test_targets=(), ranked_statistic=None):
        if ranked_statistic is not None and self.ranked_stat is not ranked_statistic:
            return TestResult(False, 'Ranked Stat being looked for is not the ranked_stat that changed.')
        num_passed = 0
        for target in test_targets:
            if target is None:
                logger.error('Trying to call RankedStatThresholdTest on {} which is None', target)
                return TestResult(False, 'Target({}) does not exist', self.who)
            value = 0
            if self.ranked_stat is not None:
                tracker = target.get_tracker(self.ranked_stat)
                ranked_stat_inst = tracker.get_statistic(self.ranked_stat)
                if not (self.ranked_stat.is_skill and ranked_stat_inst.is_initial_value):
                    if self.test_against_highest_rank:
                        value = ranked_stat_inst.highest_rank_achieved
                    else:
                        value = ranked_stat_inst.rank_level
            else:
                ranked_stat_inst = None
            if ranked_stat_inst is None and self.must_have_ranked_stat and self.num_participants is None:
                return TestResultNumeric(False, '{} Does not have ranked stat: {}.', self.who.name, self.ranked_stat, current_value=value, goal_value=self.threshold.value, is_money=False, tooltip=self.tooltip)
            if not self.threshold.compare(value):
                operator_symbol = Operator.from_function(self.threshold.comparison).symbol
                if self.num_participants is None:
                    return TestResultNumeric(False, '{} failed ranked stat check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.ranked_stat, operator_symbol, self.threshold.value, value, current_value=value, goal_value=self.threshold.value, is_money=False, tooltip=self.tooltip)
                    num_passed += 1
            else:
                num_passed += 1
        if self.num_participants is not None and not self.num_participants.compare(num_passed):
            return TestResult(False, 'Failed num participants needed for {}. Required {} {} but has {}.', self.ranked_stat, Operator.from_function(self.num_participants.comparison).symbol, self.num_participants.value, num_passed, tooltip=self.tooltip)
        return TestResult.TRUE

    @property
    def stat(self):
        return self.ranked_stat

    def __repr__(self):
        return 'Ranked Stat: {}, Threshold: {} on Subject {}'.format(self.ranked_stat, self.threshold, self.who)

class MotiveThresholdTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.MotiveLevelChange,)

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(participant_type_enum, participant_type_default, description='Who or what to apply this test to')}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'stats': TunableList(description='\n            The stat we are operating on.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=True)), 'threshold': TunableThreshold(description="\n            The threshold to control availability based on the statistic's value.")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target is None:
                logger.error('Trying to call MotiveThresholdTest on {} which is None', target)
                return TestResult(False, 'Target({}) does not exist', self.who)
            for stat in self.stats:
                tracker = target.get_tracker(stat)
                curr_value = tracker.get_user_value(stat)
                if not self.threshold.compare(curr_value):
                    operator_symbol = Operator.from_function(self.threshold.comparison).symbol
                    return TestResult(False, '{} failed stat check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, stat.__name__, operator_symbol, self.threshold.value, curr_value, tooltip=self.tooltip)
        return TestResult.TRUE

class StatInMotionTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(description='\n                Who or what to apply this test to\n                ', tunable_type=participant_type_enum, default=participant_type_default, invalid_enums=(ParticipantType.Invalid,))}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor, invalid_enums=(ParticipantType.Invalid,)), 'stat': TunableReference(description='\n            The stat we are operating on.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'threshold': TunableThreshold(description='\n            The threshold of loss or gain rate for this statistic in order to pass.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        for target in test_targets:
            if target is None:
                logger.error('Trying to call StatInMotionTest on {} which is None', target)
                return TestResult(False, 'Target({}) does not exist', self.who)
            curr_value = target.get_statistic(self.stat).get_change_rate_without_decay()
            if not self.threshold.compare(curr_value):
                return TestResult(False, 'Failed stat motion check')
        return TestResult.TRUE

class TunableStatOfCategoryTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'who': TunableEnumEntry(participant_type_enum, participant_type_default, description='Who or what to apply this test to')}

    FACTORY_TUNABLES = {'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'statistic_category': TunableEnumEntry(description='\n            The category to check for.\n            ', tunable_type=statistics.statistic_categories.StatisticCategory, default=statistics.statistic_categories.StatisticCategory.INVALID, pack_safe=True), 'check_for_existence': Tunable(description='\n            If checked, this test will succeed if any statistic of the category\n            exists.  If unchecked, this test will succeed only if no statistics\n            of the category exist.\n            ', tunable_type=bool, default=True)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, safe_to_skip=True, **kwargs)

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets=()):
        category = self.statistic_category
        check_exist = self.check_for_existence
        for target in test_targets:
            found_category_on_sim = False
            for commodity in target.commodity_tracker.get_all_commodities():
                if category in commodity.get_categories() and not commodity.is_at_convergence():
                    if check_exist:
                        found_category_on_sim = True
                    else:
                        return TestResult(False, 'Sim has a commodity disallowed by StatOfCategoryTest')
            if check_exist and not found_category_on_sim:
                TestResult(False, 'Sim does not have a commodity required by StatOfCategoryTest')
        return TestResult.TRUE

class _AllObjectCommodityAdvertised(HasTunableSingletonFactory):

    def get_objects_gen(self):
        yield from services.object_manager().get_valid_objects_gen()

class _LaundryObjectCommodityAdvertised(HasTunableSingletonFactory):

    def get_objects_gen(self):
        laundry_service = services.get_laundry_service()
        if laundry_service is not None:
            yield from laundry_service.laundry_hero_objects

class TunableObjectCommodityAdvertisedVariant(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, all_objects=_AllObjectCommodityAdvertised.TunableFactory(), laundry_objects=_LaundryObjectCommodityAdvertised.TunableFactory(), default='all_objects', **kwargs)

class CommodityAdvertisedTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    REQUIRE_ANY = 0
    REQUIRE_ALL = 1
    REQUIRE_NONE = 2
    FACTORY_TUNABLES = {'commodities': TunableSet(description='\n            A list of commodities that must be advertised by some interaction\n            on the current lot.\n            ', tunable=TunableReference(description='\n                The type of commodity to search for.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC))), 'static_commodities': TunableSet(description='\n            A list of static commodities that must be advertised by some\n            interaction on the current lot.\n            ', tunable=TunableReference(description='\n                The type of static commodity to search for.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATIC_COMMODITY))), 'requirements': TunableVariant(description='\n            A variant specifying the terms of this test with regards to the\n            tuned commodities.\n            \n            * Require Any: The test will pass if any of the tuned commodities \n            are found on an object.\n            * Require All: The test will only pass if all of the tuned\n            commodities are found on a single object.\n            * Require None: The test will only pass if none of the tuned\n            commodities are found on any object on the lot.\n            ', locked_args={'require_any': REQUIRE_ANY, 'require_all': REQUIRE_ALL, 'require_none': REQUIRE_NONE}, default='require_any'), 'require_reservable_by_participant': OptionalTunable(description='\n            If enabled, the object that advertises the commodity must by reservable\n            by the specified participant type.\n            ', tunable=TunableEnumEntry(description='\n                The participant that must be able to reserve the object.\n                ', tunable_type=ParticipantType, default=ParticipantType.Actor)), 'tested_objects': TunableObjectCommodityAdvertisedVariant(description='\n            The test will only check these objects for tuned advertised \n            commodities.\n            \n            EX: to improve performance, when we know that tuned commodities \n            will only be found on laundry objects, set this to Laundry Objects \n            instead of All Objects.\n            '), 'test_aops': Tunable(description='\n            If checked, the obj that is advertising the tuned commodities must\n            also have the aops that grant that commodity be able to run.\n            \n            EX: check if any dishes on the lot can be eaten. Even if the\n            dishes advertise the eat static commodity, the individual dish themselves might\n            not be able to be eaten because they are spoiled, empty, etc.\n            ', tunable_type=bool, default=False), 'check_affordance_suppression': Tunable(description='\n            If checked, suppressed affordances will not be considered.\n            ', tunable_type=bool, default=False), 'test_connectivity_to_target': Tunable(description='\n            If checked, this test will ensure the target Sim can pass a pt to\n            pt connectivity check to the advertising object.\n            ', tunable_type=bool, default=True), 'allow_targeted_objects': Tunable(description="\n            If enabled, objects targeted (ParticipantType.Object) by the\n            interaction are allowed to pass this test. Typically, for cleaning\n            up dishes, we disallow targeted objects because we don't want you\n            to run the affordance on dishes you are carrying.\n            ", tunable_type=bool, default=False), 'test_autonomous_availability': Tunable(description='\n            If enabled, this test will consider advertising objects that the\n            Sim can use autonomously. This should be specifically disabled if\n            we want to bypass on lot and off lot autonomy rules for the purpose\n            of this test.\n            ', tunable_type=bool, default=True), 'test_reservations': Tunable(description="\n            If enabled, this test will consider advertising objects that the\n            Sim can currently reserve. This should be specifically disabled if\n            we don't care about object reservations.\n            ", tunable_type=bool, default=True)}

    def get_expected_args(self):
        expected_args = {'target_objects': ParticipantType.Object, 'context': ParticipantType.InteractionContext, 'actor_set': ParticipantType.Actor}
        if self.require_reservable_by_participant is not None:
            expected_args['reserve_participants'] = self.require_reservable_by_participant
        return expected_args

    @property
    def allow_failfast_tests(self):
        return False

    def _has_valid_aop(self, obj, motives, context, test_aops, check_suppression):
        for affordance in obj.super_affordances(context):
            if not affordance.commodity_flags & motives:
                pass
            else:
                for aop in affordance.potential_interactions(obj, context):
                    if check_suppression and obj.check_affordance_for_suppression(context.sim, aop, False):
                        pass
                    elif test_aops:
                        test_result = aop.test(context)
                        if not test_result:
                            pass
                        else:
                            return True
                    else:
                        return True
        return False

    @cached_test
    def __call__(self, target_objects=None, reserve_participants=None, context=None, actor_set=None):
        actor_info = next(iter(actor_set))
        actor = actor_info.get_sim_instance()
        if actor is None:
            return TestResult(False, 'The actor Sim is not instantiated.')
        reference_object = actor
        targets = set()
        if target_objects:
            targets = set(target_objects)
            for obj in target_objects:
                if obj.is_sim:
                    sim_instance = obj.get_sim_instance()
                    if sim_instance is None:
                        pass
                    else:
                        reference_object = sim_instance
                        break
                        if not obj.is_in_inventory():
                            reference_object = obj
                            break
                if not obj.is_in_inventory():
                    reference_object = obj
                    break
        motives = self.static_commodities.union(self.commodities)
        autonomy_rule = actor.get_off_lot_autonomy_rule()
        for obj in self.tested_objects.get_objects_gen():
            if self.allow_targeted_objects or obj in targets:
                pass
            else:
                motive_intersection = obj.commodity_flags & motives
                if not motive_intersection:
                    pass
                elif self.test_autonomous_availability and not actor.autonomy_component.get_autonomous_availability_of_object(obj, autonomy_rule, reference_object=reference_object):
                    pass
                elif self.test_reservations and reserve_participants is not None:
                    for sim in reserve_participants:
                        sim_instance = sim.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                        if sim_instance is not None and obj.may_reserve(sim_instance):
                            break
                elif (self.test_aops or self.check_affordance_suppression) and not self._has_valid_aop(obj, motives, context, self.test_aops, self.check_affordance_suppression):
                    pass
                elif self.test_connectivity_to_target and not obj.is_connected(actor):
                    pass
                else:
                    if self.requirements == self.REQUIRE_NONE:
                        return TestResult(False, 'A specified commodity was found, but we are requiring that no specified commodities are found.', tooltip=self.tooltip)
                    if self.requirements == self.REQUIRE_ANY:
                        return TestResult.TRUE
                    if self.requirements == self.REQUIRE_ALL and motive_intersection == motives:
                        return TestResult.TRUE
        if self.requirements == self.REQUIRE_NONE:
            return TestResult.TRUE
        if reserve_participants is not None:
            return TestResult(False, 'No required commodities or static commodities are advertising where the object is reservable by participant type {}.', self.require_reservable_by_participant, tooltip=self.tooltip)
        return TestResult(False, 'No required commodities or static commodities are advertising.', tooltip=self.tooltip)

class CommodityDesiredByOtherSims(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'commodity': TunableTuple(commodity=TunableReference(description='\n                The type of commodity to test.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), threshold=TunableThreshold(description='\n                The threashold to test for.\n                ')), 'only_other_sims': Tunable(description='\n            If checked, the sim running this test is not counted.', tunable_type=bool, default=True), 'only_household_sims': Tunable(description='\n            If checked, only sims in the same household as the testing sim \n            are considered.', tunable_type=bool, default=True), 'count': Tunable(description='\n            The number of sims that must desire the commodity for this test\n            to pass.', tunable_type=int, default=1), 'invert': Tunable(description='\n            If checked, the test will be inverted.  In other words, the test \n            will fail if any sim desires the tuned commodity.', tunable_type=bool, default=False)}

    def get_expected_args(self):
        expected_args = {'context': ParticipantType.InteractionContext}
        return expected_args

    @cached_test
    def __call__(self, context=None):
        logger.assert_log(context is not None, 'Context is None in CommodityDesiredByOtherSims test.', owner='rez')
        total_passed = 0
        for sim in services.sim_info_manager().instanced_sims_gen():
            if self.only_other_sims and context is not None and context.sim is sim:
                pass
            elif self.only_household_sims and context is not None and context.sim.household_id != sim.household_id:
                pass
            else:
                commodity_inst = sim.get_stat_instance(self.commodity.commodity)
                if commodity_inst is not None and self.commodity.threshold.compare(commodity_inst.get_value()):
                    total_passed += 1
                    if total_passed >= self.count:
                        if not self.invert:
                            return TestResult.TRUE
                        return TestResult(False, 'Too many sims desire this commodity.', tooltip=self.tooltip)
        if not self.invert:
            return TestResult(False, 'Not enough sims desire this commodity.', tooltip=self.tooltip)
        else:
            return TestResult.TRUE
