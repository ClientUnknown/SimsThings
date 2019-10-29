from event_testing import TargetIdTypesfrom event_testing.results import TestResult, TestResultNumericfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEvent, cached_testfrom interactions import ParticipantType, ParticipantTypeSingleSimfrom sims4.tuning.tunable import TunableFactory, TunableEnumFlags, TunableTuple, TunableSet, TunableReference, TunableInterval, Tunable, TunableEnumEntry, TunableSingletonFactory, HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, TunableList, TunablePackSafeReferenceimport enumimport event_testingimport servicesimport sims4.resourcesimport singletonsimport taglogger = sims4.log.Logger('RelationshipTests', default_owner='msantander')
class RelationshipTestEvents(enum.Int):
    AllRelationshipEvents = 0
    RelationshipChanged = TestEvent.RelationshipChanged
    AddRelationshipBit = TestEvent.AddRelationshipBit
    RemoveRelationshipBit = TestEvent.RemoveRelationshipBit

class BaseRelationshipTest(BaseTest):
    UNIQUE_TARGET_TRACKING_AVAILABLE = True
    MIN_RELATIONSHIP_VALUE = -100.0
    MAX_RELATIONSHIP_VALUE = 100.0

    @TunableFactory.factory_option
    def participant_type_override(participant_type_enum, participant_type_default):
        return {'target_sim': TunableEnumFlags(description='\n                    Target(s) of the relationship(s).\n                    ', enum_type=participant_type_enum, default=participant_type_default)}

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        overlapping_bits = (value.required_relationship_bits.match_any | value.required_relationship_bits.match_all) & (value.prohibited_relationship_bits.match_any | value.prohibited_relationship_bits.match_all)
        if overlapping_bits:
            logger.error('Tuning error in {}. Cannot have overlapping required and prohibited relationship bits: {}'.format(instance_class, overlapping_bits))

    FACTORY_TUNABLES = {'subject': TunableEnumFlags(description='\n            Owner(s) of the relationship(s).\n            ', enum_type=ParticipantType, default=ParticipantType.Actor), 'required_relationship_bits': TunableTuple(match_any=TunableSet(description='\n                Any of these relationship bits will pass the test.\n                ', tunable=TunableReference(services.relationship_bit_manager(), pack_safe=True)), match_all=TunableSet(description='\n                All of these relationship bits must be present to pass the\n                test.\n                ', tunable=TunablePackSafeReference(services.relationship_bit_manager()), allow_none=True)), 'prohibited_relationship_bits': TunableTuple(match_any=TunableSet(description='\n                If any of these relationship bits match the test will fail.\n                ', tunable=TunableReference(services.relationship_bit_manager(), pack_safe=True)), match_all=TunableSet(description='\n                All of these relationship bits must match to fail the test.\n                ', tunable=TunableReference(services.relationship_bit_manager()))), 'relationship_score_interval': TunableInterval(description='\n            The range that the relationship score must be within in order for\n            this test to pass.\n            ', tunable_type=float, default_lower=MIN_RELATIONSHIP_VALUE, default_upper=MAX_RELATIONSHIP_VALUE, minimum=MIN_RELATIONSHIP_VALUE, maximum=MAX_RELATIONSHIP_VALUE), 'test_event': TunableEnumEntry(description='\n            The event that we want to trigger this instance of the tuned test\n            on.\n            ', tunable_type=RelationshipTestEvents, default=RelationshipTestEvents.AllRelationshipEvents), 'verify_tunable_callback': _verify_tunable_callback}
    __slots__ = ('test_events', 'subject', 'required_relationship_bits', 'prohibited_relationship_bits', 'track', 'relationship_score_interval', 'initiated')

    def __init__(self, subject, required_relationship_bits, prohibited_relationship_bits, track, relationship_score_interval, test_event, initiated=True, **kwargs):
        super().__init__(**kwargs)
        if test_event == RelationshipTestEvents.AllRelationshipEvents:
            self.test_events = (TestEvent.RelationshipChanged, TestEvent.AddRelationshipBit, TestEvent.RemoveRelationshipBit)
        else:
            self.test_events = (test_event,)
        self.subject = subject
        self.required_relationship_bits = required_relationship_bits
        self.prohibited_relationship_bits = prohibited_relationship_bits
        self.track = track
        self.relationship_score_interval = relationship_score_interval
        self.initiated = initiated

    @cached_test
    def __call__(self, targets=None):
        if not self.initiated:
            return TestResult.TRUE
        if targets is None:
            return TestResult(False, 'Currently Actor-only relationship tests are unsupported, valid on zone load.')
        if self.track is None:
            self.track = singletons.DEFAULT

    def goal_value(self):
        if self.num_relations:
            return self.num_relations
        return 1

class RelationshipTest(BaseRelationshipTest):
    FACTORY_TUNABLES = {'description': 'Gate availability by a relationship status.', 'target_sim': TunableEnumFlags(description='\n            Target(s) of the relationship(s).\n            ', enum_type=ParticipantType, default=ParticipantType.TargetSim), 'test_incest': TunableVariant(description="\n            Test for incest status. Test passes if this matches the two Sim's\n            incest status.\n            ", locked_args={'disabled': None, 'is incestuous': True, 'is not incestuous': False}, default='disabled'), 'track': TunableReference(description='\n            If set, the test will use the relationship score between sims for\n            this track. If unset, the track defaults to the global module\n            tunable REL_INSPECTOR_TRACK.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='RelationshipTrack', allow_none=True, pack_safe=True), 'num_relations': Tunable(description='\n            Number of Sims with specified relationships required to pass,\n            default(0) is all known relations.\n            \n            If value set to 1 or greater, then test is looking at least that\n            number of relationship to match the criteria.\n            \n            If value is set to 0, then test will pass if relationships being\n            tested must match all criteria of the test to succeed.  For\n            example, if interaction should not appear if any relationship\n            contains a relationship bit, this value should be 0.\n            ', tunable_type=int, default=0)}
    __slots__ = ('target_sim', 'test_incest', 'num_relations')

    def __init__(self, target_sim, test_incest, num_relations, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_sim = target_sim
        self.test_incest = test_incest
        self.num_relations = num_relations

    def get_target_id(self, source_sims=None, target_sims=None, id_type=None):
        if source_sims is None or target_sims is None:
            return
        for target_sim in target_sims:
            if target_sim and target_sim.is_sim:
                if id_type == TargetIdTypes.HOUSEHOLD:
                    return target_sim.household.id
                return target_sim.id

    def get_expected_args(self):
        return {'source_sims': self.subject, 'target_sims': self.target_sim}

    @cached_test
    def __call__(self, source_sims=None, target_sims=None):
        super().__call__(targets=target_sims)
        if self.num_relations:
            use_threshold = True
            threshold_count = 0
            count_it = True
        else:
            use_threshold = False
        if self.target_sim == ParticipantType.AllRelationships:
            targets_id_gen = self._all_related_sims_and_id_gen
        else:
            targets_id_gen = self._all_specified_sims_and_id_gen
        for sim_a in source_sims:
            rel_tracker = sim_a.relationship_tracker
            for (sim_b, sim_b_id) in targets_id_gen(sim_a, target_sims):
                if sim_b is None:
                    pass
                else:
                    rel_score = rel_tracker.get_relationship_score(sim_b_id, self.track)
                    if rel_score is None:
                        logger.error('{} and {} do not have a relationship score in TunableRelationshipTest.', sim_a, sim_b)
                    if rel_score < self.relationship_score_interval.lower_bound or rel_score > self.relationship_score_interval.upper_bound:
                        if use_threshold:
                            count_it = False
                        else:
                            return TestResult(False, 'Inadequate relationship level ({} not within [{},{}]) between {} and {}.', rel_score, self.relationship_score_interval.lower_bound, self.relationship_score_interval.upper_bound, sim_a, sim_b, tooltip=self.tooltip)
                    if self.required_relationship_bits.match_any:
                        for bit in self.required_relationship_bits.match_any:
                            if rel_tracker.has_bit(sim_b_id, bit):
                                break
                        if use_threshold:
                            count_it = False
                        else:
                            return TestResult(False, 'Missing all of the match_any required relationship bits between {} and {}.', sim_a, sim_b, tooltip=self.tooltip)
                    for bit in self.required_relationship_bits.match_all:
                        if bit is None:
                            return TestResult(False, 'Missing pack, so relationship bit is None.', tooltip=self.tooltip)
                        if not rel_tracker.has_bit(sim_b_id, bit):
                            if use_threshold:
                                count_it = False
                                break
                            else:
                                return TestResult(False, 'Missing relationship bit ({}) between {} and {}.', bit, sim_a, sim_b, tooltip=self.tooltip)
                    if self.prohibited_relationship_bits.match_any:
                        for bit in self.prohibited_relationship_bits.match_any:
                            if rel_tracker.has_bit(sim_b_id, bit):
                                if use_threshold:
                                    count_it = False
                                    break
                                else:
                                    return TestResult(False, 'Prohibited Relationship ({}) between {} and {}.', bit, sim_a, sim_b, tooltip=self.tooltip)
                    if self.prohibited_relationship_bits.match_all:
                        for bit in self.prohibited_relationship_bits.match_all:
                            if not rel_tracker.has_bit(sim_b_id, bit):
                                break
                        if use_threshold:
                            count_it = False
                        else:
                            return TestResult(False, '{} has all  the match_all prohibited bits with {}.', sim_a, sim_b, tooltip=self.tooltip)
                    if self.test_incest is not None:
                        is_incestuous = not sim_a.incest_prevention_test(sim_b)
                        if is_incestuous != self.test_incest:
                            return TestResult(False, 'Incest test failed. Needed {}.', self.test_incest, tooltip=self.tooltip)
                    if use_threshold:
                        if count_it:
                            threshold_count += 1
                        count_it = True
        if not use_threshold:
            if target_sims == ParticipantType.AllRelationships or len(target_sims) > 0:
                return TestResult.TRUE
            return TestResult(False, 'Nothing compared against, target_sims list is empty.')
        if not threshold_count >= self.num_relations:
            return TestResultNumeric(False, 'Number of relations required not met', current_value=threshold_count, goal_value=self.num_relations, is_money=False, tooltip=self.tooltip)
        return TestResult.TRUE

    def _all_related_sims_and_id_gen(self, source_sim, target_sims):
        for sim_b_id in source_sim.relationship_tracker.target_sim_gen():
            sim_b = services.sim_info_manager().get(sim_b_id)
            yield (sim_b, sim_b_id)

    def _all_specified_sims_and_id_gen(self, source_sims, target_sims):
        for sim in target_sims:
            if sim is None:
                yield (None, None)
            else:
                yield (sim, sim.sim_id)
TunableRelationshipTest = TunableSingletonFactory.create_auto_factory(RelationshipTest)
class ObjectTypeRelationshipTest(HasTunableSingletonFactory, BaseRelationshipTest):
    FACTORY_TUNABLES = {'description': 'Gate availability by a relationship status.\n        \n            Note: \n            This is different than the instance-based Object Relationship Component\n            and applies only to the relationships of Object Based Tracks tuned under\n            relationship tracker module tuning.\n            \n            If object rel does not exist, the test will treat the rel_track value \n            with an assumed value of 0 with no rel-bits.\n            ', 'target_type': TunableVariant(description='\n            The type of target we want to test the relationship on.  This will\n            either be a tag set (in the case where we want to test rel on \n            uninstantiated objects) or an object.\n            ', tag_set=TunableReference(description='\n                Tag set that defines the target objects of the relationship.\n                ', manager=services.get_instance_manager(sims4.resources.Types.TAG_SET), pack_safe=True), object=TunableEnumFlags(description='\n                Target Object of the relationship.\n                ', enum_type=ParticipantType, default=ParticipantType.Object), default='object'), 'track': TunableReference(description='\n            The object relationship track on which to check for bits and threshold values.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='ObjectRelationshipTrack')}
    __slots__ = ('target_type',)

    def __init__(self, target_type, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.target_type = target_type

    def get_expected_args(self):
        return {'source_sims': self.subject, 'target_type': self.target_type}

    @cached_test
    def __call__(self, source_sims=None, target_type=None):
        if self.target_type == ParticipantType.AllRelationships:
            logger.error('Object Relationships do not support the All Relationships participant. Failed to test against relationship between source:{} and target:{}', source_sims, self.target_type)
            return
        for sim_a in source_sims:
            sim_a_id = sim_a.id
            rel_tracker = self.track
            relationship_service = services.relationship_service()
            if isinstance(self.target_type, ParticipantType):
                target_object = target_type[0]
                obj_tag_set = relationship_service.get_mapped_tag_set_of_id(target_object.definition.id)
                if obj_tag_set is None:
                    logger.error('{} does not have object relationship tuning. Update the object relationship map.', target_object)
                    return TestResult(False, 'Relationship between {} and {} does not exist.', sim_a, target_object, tooltip=self.tooltip)
            else:
                obj_tag_set = self.target_type
            rel_score = relationship_service.get_object_relationship_score(sim_a_id, obj_tag_set, track=rel_tracker)
            actual_rel = rel_tracker.initial_value if rel_score is None else rel_score
            if actual_rel not in self.relationship_score_interval:
                return TestResult(False, 'Inadequate relationship level ({} not within [{},{}]) between {} and {}.', rel_score, self.relationship_score_interval.lower_bound, self.relationship_score_interval.upper_bound, sim_a, self.target_type, tooltip=self.tooltip)
            if self.required_relationship_bits.match_any:
                if rel_score is None:
                    return TestResult(False, 'No relationship between {} and {}.', sim_a, self.target_type, tooltip=self.tooltip)
                for bit in self.required_relationship_bits.match_any:
                    if relationship_service.has_object_bit(sim_a_id, obj_tag_set, bit):
                        break
                return TestResult(False, 'Missing all of the match_any required relationship bits between {} and {}.', sim_a, self.target_type, tooltip=self.tooltip)
            for bit in self.required_relationship_bits.match_all:
                if rel_score is None:
                    return TestResult(False, 'No relationship between {} and {}.', sim_a, self.target_type, tooltip=self.tooltip)
                if bit is None:
                    return TestResult(False, 'Missing pack, so relationship bit is None.', tooltip=self.tooltip)
                if not relationship_service.has_object_bit(sim_a_id, obj_tag_set, bit):
                    return TestResult(False, 'Missing relationship bit ({}) between {} and {}.', bit, sim_a, self.target_type, tooltip=self.tooltip)
            if rel_score is not None:
                for bit in self.prohibited_relationship_bits.match_any:
                    if relationship_service.has_object_bit(sim_a_id, obj_tag_set, bit):
                        return TestResult(False, 'Prohibited Relationship ({}) between {} and {}.', bit, sim_a, self.target_type, tooltip=self.tooltip)
            if self.prohibited_relationship_bits.match_any and self.prohibited_relationship_bits.match_all and rel_score is not None:
                for bit in self.prohibited_relationship_bits.match_all:
                    if not relationship_service.has_object_bit(sim_a_id, obj_tag_set, bit):
                        break
                return TestResult(False, '{} has all  the match_all prohibited bits with {}.', sim_a, self.target_type, tooltip=self.tooltip)
            return TestResult.TRUE

class ComparativeRelationshipTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject_a': TunableEnumFlags(description='\n            Owner(s) of the relationship(s) to be compared with subject_b.\n            ', enum_type=ParticipantType, default=ParticipantType.Actor), 'subject_b': TunableEnumFlags(description='\n            Owner(s) of the relationship(s) to be compared with subject_a.\n            ', enum_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumFlags(description='\n            Target of the relationship(s).\n            ', enum_type=ParticipantType, default=ParticipantType.TargetSim), 'track': TunableReference(description='\n            The relationship track to compare.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='RelationshipTrack'), 'fallback': TunableVariant(description='\n            The fallback winner in case subjects a and b have the exact same\n            average relationship with the target.\n            ', locked_args={'Subject A': True, 'Subject B': False}, default='Subject A'), 'expected_result': TunableVariant(description='\n            The expected result of this relationship comparison.\n            ', locked_args={'Subject A has higher relationship with target.': True, 'Subject B has higher relationship with target.': False}, default='Subject A has higher relationship with target.')}

    def get_expected_args(self):
        return {'subject_a': self.subject_a, 'subject_b': self.subject_b, 'target': self.target}

    def get_average_relationship(self, subjects, targets):
        final_rel = 0
        for target_sim in targets:
            rel = 0
            num_subjects = 0
            tracker = target_sim.relationship_tracker
            for subject_sim in subjects:
                if target_sim == subject_sim:
                    pass
                else:
                    num_subjects += 1
                    rel += tracker.get_relationship_score(subject_sim.id, self.track)
            if num_subjects > 0:
                final_rel += rel/num_subjects
        final_rel /= len(targets)
        return final_rel

    @cached_test
    def __call__(self, subject_a=None, subject_b=None, target=None):
        a_average = self.get_average_relationship(subject_a, target)
        b_average = self.get_average_relationship(subject_b, target)
        a_higher = a_average > b_average
        if self.fallback:
            a_higher = True
        if a_average == b_average and a_higher or self.expected_result:
            return TestResult(False, 'Sims {} expected to have a higher average relationship with Sims {} than Sims {}, but that is not the case.', subject_a, target, subject_b)
        if a_higher and not self.expected_result:
            return TestResult(False, 'Sims {} expected to have a lower average relationship with Sims {} than Sims {}, but that is not the case.', subject_a, target, subject_b)
        return TestResult.TRUE

class RelationshipBitTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumFlags(description='\n            Owner(s) of the relationship(s) to be compared with subject_b.\n            ', enum_type=ParticipantType, default=ParticipantType.Actor), 'target': TunableEnumFlags(description='\n            Owner(s) of the relationship(s) to be compared with subject_a.\n            ', enum_type=ParticipantType, default=ParticipantType.TargetSim), 'relationship_bits': TunableSet(description='\n            Any of these relationship bits will pass the test.\n            ', tunable=TunableReference(services.relationship_bit_manager()), minlength=1), 'test_event': TunableVariant(description='\n            Event to listen to.\n            ', locked_args={'Bit Added': TestEvent.AddRelationshipBit, 'Bit Removed': TestEvent.RemoveRelationshipBit}, default='Bit Added')}

    @property
    def test_events(self):
        return (self.test_event,)

    def get_expected_args(self):
        return {'subject': self.subject, 'target': self.target, 'relationship_bit': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, subject, target, relationship_bit):
        if relationship_bit not in self.relationship_bits:
            return TestResult(False, 'Event {} did not trigger for bit {} between Sims {} and {}, bits of interest: {}', relationship_bit, subject, target, self.relationship_bits)
        return TestResult.TRUE

class RelationshipModifiedByStatisticTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'description': '\n            Gate availability by combination of relationship tracks and statistics.\n            ', 'subject': TunableEnumFlags(description='\n            Owner(s) of the relationship.\n            ', enum_type=ParticipantTypeSingleSim, default=ParticipantType.Actor), 'target_sim': TunableEnumFlags(description='\n            Target(s) of the relationship.\n            ', enum_type=ParticipantTypeSingleSim, default=ParticipantType.TargetSim), 'relationship_tracks': TunableList(description='\n            List of the relationship tracks and respective multipliers.\n            ', tunable=TunableTuple(track=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='RelationshipTrack'), multiplier=Tunable(tunable_type=float, default=1))), 'subject_statistics': TunableList(description='\n            List of the statistics and respective multipliers for the subject.\n            ', tunable=TunableTuple(statistic=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity', 'RankedStatistic', 'Skill', 'Statistic', 'LifeSkillStatistic')), multiplier=Tunable(tunable_type=float, default=1))), 'target_statistics': TunableList(description='\n            List of the statistics and respective multipliers for the target.\n            ', tunable=TunableTuple(statistic=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions=('Commodity', 'RankedStatistic', 'Skill', 'Statistic', 'LifeSkillStatistic')), multiplier=Tunable(tunable_type=float, default=1))), 'score_interval': TunableInterval(description='\n            The range that the score must be within in order for this test to \n            pass.  Min inclusive, max exclusive.\n            Score is sum of all specified statistics and tracks multiplied by \n            their respective multipliers.\n            ', tunable_type=float, default_lower=0, default_upper=1000)}

    def get_expected_args(self):
        return {'source_sims': self.subject, 'target_sims': self.target_sim}

    @cached_test
    def __call__(self, source_sims=None, target_sims=None):
        if target_sims is None:
            return TestResult(False, 'Currently Actor-only relationship tests are unsupported, valid on zone load.')
        value = 0
        for sim_a in source_sims:
            rel_tracker = sim_a.relationship_tracker
            for sim_b in target_sims:
                if sim_b is None:
                    pass
                else:
                    sim_b_id = sim_b.sim_id
                    for track_pair in self.relationship_tracks:
                        score = rel_tracker.get_relationship_score(sim_b_id, track_pair.track)
                        if score is not None:
                            value += score*track_pair.multiplier
                    value += RelationshipModifiedByStatisticTest._sum_modified_statistics(sim_a, self.subject_statistics)
                    value += RelationshipModifiedByStatisticTest._sum_modified_statistics(sim_b, self.target_statistics)
                    if value < self.score_interval.lower_bound or value >= self.score_interval.upper_bound:
                        return TestResult(False, 'Inadequate statistic modified relationship level ({} not within [{},{}]) between {} and {}.', value, self.score_interval.lower_bound, self.score_interval.upper_bound, sim_a, sim_b, tooltip=self.tooltip)
                    return TestResult(True)
        return TestResult(False, 'No valid actor or target in StatisticModifiedRelationshipTest')

    @staticmethod
    def _sum_modified_statistics(sim, statistics):
        value = 0
        for statistic_pair in statistics:
            stat_type = statistic_pair.statistic
            stat_tracker = sim.get_tracker(stat_type)
            if stat_tracker is not None:
                stat = stat_tracker.get_statistic(stat_type) or stat_type
                score = stat.get_user_value() if hasattr(stat, 'get_user_value') else None
                if score is not None:
                    value += score*statistic_pair.multiplier
        return value
