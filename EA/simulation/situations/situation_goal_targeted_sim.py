import randomfrom clubs.club_tests import ClubTestfrom event_testing.resolver import DoubleSimResolverfrom event_testing.results import TestResultfrom event_testing.test_events import TestEventfrom interactions import ParticipantType, ParticipantTypeSimfrom relationships.relationship_tests import TunableRelationshipTestfrom sims4.tuning.tunable import Tunable, TunableMapping, TunableEnumEntry, TunableTuple, OptionalTunable, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_goal import SituationGoal, UiSituationGoalStatusimport enumimport event_testing.test_variantsimport event_testing.tests_with_dataimport servicesimport sims.sim_info_testsimport sims4.tuning.tunableimport statistics.skill_tests
class TunableTargetedSimTestVariant(sims4.tuning.tunable.TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(statistic=event_testing.statistic_tests.StatThresholdTest.TunableFactory(locked_args={'who': ParticipantType.TargetSim, 'tooltip': None}), relative_statistic=event_testing.statistic_tests.RelativeStatTest.TunableFactory(locked_args={'source': ParticipantType.Actor, 'target': ParticipantType.TargetSim}), skill_tag=statistics.skill_tests.SkillTagThresholdTest.TunableFactory(locked_args={'who': ParticipantType.TargetSim, 'tooltip': None}), mood=sims.sim_info_tests.MoodTest.TunableFactory(locked_args={'who': ParticipantTypeSim.TargetSim, 'tooltip': None}), sim_info=sims.sim_info_tests.SimInfoTest.TunableFactory(locked_args={'who': ParticipantType.TargetSim, 'tooltip': None}), trait=sims.sim_info_tests.TraitTest.TunableFactory(locked_args={'subject': ParticipantType.TargetSim, 'tooltip': None}), topic=event_testing.test_variants.TunableTopicTest(locked_args={'subject': ParticipantType.Actor, 'target_sim': ParticipantType.TargetSim, 'tooltip': None}), buff=sims.sim_info_tests.BuffTest.TunableFactory(locked_args={'subject': ParticipantType.TargetSim, 'tooltip': None}), relationship=TunableRelationshipTest(locked_args={'subject': ParticipantType.Actor, 'target_sim': ParticipantType.TargetSim, 'tooltip': None}), motive=event_testing.statistic_tests.MotiveThresholdTest.TunableFactory(locked_args={'who': ParticipantType.TargetSim, 'tooltip': None}), filter=sims.sim_info_tests.FilterTest.TunableFactory(locked_args={'filter_target': ParticipantType.TargetSim, 'relative_sim': ParticipantType.Actor, 'tooltip': None}), situation_job=event_testing.test_variants.TunableSituationJobTest(locked_args={'participant': ParticipantType.TargetSim, 'tooltip': None}), gender_preference=sims.sim_info_tests.GenderPreferenceTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'target_sim': ParticipantType.TargetSim, 'tooltip': None}), club=ClubTest.TunableFactory(locked_args={'club': ClubTest.CLUB_USE_ANY, 'tooltip': None}), career=event_testing.test_variants.TunableCareerTest.TunableFactory(locked_args={'subjects': ParticipantType.TargetSim, 'tooltip': None}), bucks_perks_test=event_testing.test_variants.BucksPerkTest.TunableFactory(locked_args={'participant': ParticipantType.TargetSim, 'tooltip': None}), description=description, **kwargs)

class TunableTargetedSimTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableTargetedSimTestVariant(), **kwargs)

class SituationGoalSimTargetingOptions(enum.Int):
    PlayerChoice = 0
    Inherited = 1
    GoalSystemChoice = 2
    GoalSystemChoiceExcludingInherited = 3
    DebugChoice = 4

class SituationGoalTargetedSim(SituationGoal):
    REQUIRED_SIM_ID = 'required_sim_id'
    ACTUAL_SIM_ID = 'actual_sim_id'
    IS_TARGETED = True
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'_target_tests': TunableTargetedSimTestSet(description='\n                A set of tests that a sim must to be a target of this goal.\n                ', tuning_group=GroupNames.TESTS), '_target_option': sims4.tuning.tunable.TunableEnumEntry(SituationGoalSimTargetingOptions, SituationGoalSimTargetingOptions.PlayerChoice, description='How to apply the target tests. See design document for Event Goals'), '_select_sims_outside_of_situation': sims4.tuning.tunable.Tunable(bool, False, description='\n                If true then when the goal system selects sims for the target\n                the sims outside of the active situation can be chosen.\n                ')}

    @classmethod
    def _can_sim_pass_test(cls, target_sim_info, actor_sim_info, inherited_target_sim_info):
        if cls._target_option == SituationGoalSimTargetingOptions.GoalSystemChoiceExcludingInherited and target_sim_info is inherited_target_sim_info:
            return False
        if actor_sim_info is None:
            return True
        if actor_sim_info.id == target_sim_info.id:
            return False
        double_sim_resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
        return cls._target_tests.run_tests(double_sim_resolver)

    @classmethod
    def can_be_given_as_goal(cls, actor, situation, inherited_target_sim_info=None, **kwargs):
        result = super(SituationGoalTargetedSim, cls).can_be_given_as_goal(actor, situation, **kwargs)
        if not result:
            return result
        actor_sim_info = None if actor is None else actor.sim_info
        if cls._target_option == SituationGoalSimTargetingOptions.Inherited:
            if inherited_target_sim_info is None:
                return TestResult(False, 'Situation goal tuned to look for inherited target, but no inherited target given.')
            if actor is None:
                return TestResult.TRUE
            double_sim_resolver = DoubleSimResolver(actor_sim_info, inherited_target_sim_info)
            return cls._target_tests.run_tests(double_sim_resolver)
        if cls._target_option == SituationGoalSimTargetingOptions.PlayerChoice:
            return TestResult.TRUE
        if cls._target_option == SituationGoalSimTargetingOptions.DebugChoice:
            return TestResult.TRUE
        if situation is None or cls._select_sims_outside_of_situation:
            for sim_info in services.sim_info_manager().instanced_sim_info_including_baby_gen():
                if cls._can_sim_pass_test(sim_info, actor_sim_info, inherited_target_sim_info):
                    return TestResult.TRUE
        else:
            for sim in situation.all_sims_in_situation_gen():
                if cls._can_sim_pass_test(sim.sim_info, actor_sim_info, inherited_target_sim_info):
                    return TestResult.TRUE
        return TestResult(False, 'No valid target found for situation goal target.')

    def __init__(self, *args, inherited_target_sim_info=None, reader=None, **kwargs):
        super().__init__(*args, inherited_target_sim_info=inherited_target_sim_info, reader=reader, **kwargs)
        self._required_target_sim_info = None
        self._actual_target_sim_info_id = None
        if reader is not None:
            required_sim_id = reader.read_uint64(self.REQUIRED_SIM_ID, 0)
            self._required_target_sim_info = services.sim_info_manager().get(required_sim_id)
            actual_sim_id = reader.read_uint64(self.ACTUAL_SIM_ID, 0)
            self._actual_target_sim_info_id = actual_sim_id
        if self._required_target_sim_info is not None:
            return
        if self._target_option == SituationGoalSimTargetingOptions.PlayerChoice:
            return
        if self._target_option == SituationGoalSimTargetingOptions.Inherited:
            self._required_target_sim_info = inherited_target_sim_info
            return
        if self._target_option == SituationGoalSimTargetingOptions.DebugChoice:
            self._required_target_sim_info = inherited_target_sim_info
            return
        possible_sim_infos = []
        if self._situation is None or self._select_sims_outside_of_situation:
            for sim_info in services.sim_info_manager().instanced_sim_info_including_baby_gen():
                if self._can_sim_pass_test(sim_info, self._sim_info, inherited_target_sim_info):
                    possible_sim_infos.append(sim_info)
        else:
            for sim in self._situation.all_sims_in_situation_gen():
                if self._can_sim_pass_test(sim.sim_info, self._sim_info, inherited_target_sim_info):
                    possible_sim_infos.append(sim.sim_info)
        if possible_sim_infos:
            self._required_target_sim_info = random.choice(possible_sim_infos)

    def create_seedling(self):
        seedling = super().create_seedling()
        writer = seedling.writer
        if self._required_target_sim_info is not None:
            writer.write_uint64(self.REQUIRED_SIM_ID, self._required_target_sim_info.id)
        if self._actual_target_sim_info_id is not None:
            writer.write_uint64(self.ACTUAL_SIM_ID, self._actual_target_sim_info_id)
        return seedling

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if self._target_option == SituationGoalSimTargetingOptions.PlayerChoice:
            if self._situation is not None and not self._select_sims_outside_of_situation:
                target = self._get_target_sim_info_from_resolver(resolver)
                if target is None:
                    return False
                sim = target.get_sim_instance()
                if not self._situation.is_sim_in_situation(sim):
                    return False
            if not self._target_tests.run_tests(resolver):
                return False
        elif self._get_target_sim_info_from_resolver(resolver) is not self._required_target_sim_info:
            return False
        return super()._run_goal_completion_tests(sim_info, event, resolver)

    def get_actual_target_sim_info(self):
        if self._actual_target_sim_info_id is None:
            return
        return services.sim_info_manager().get(self._actual_target_sim_info_id)

    def get_required_target_sim_info(self):
        return self._required_target_sim_info

    def _get_target_sim_info_from_resolver(self, resolver):
        actual_target_sim_list = resolver.get_participants(ParticipantType.TargetSim)
        if not actual_target_sim_list:
            actual_target_sim_list = set(obj for obj in resolver.get_participants(ParticipantType.Object) if obj.is_sim)
        target_sim_info = next(iter(actual_target_sim_list), None)
        return target_sim_info

    def get_gsi_name(self):
        if self._required_target_sim_info is None:
            return super().get_gsi_name()
        return super().get_gsi_name() + ' ' + str(self._required_target_sim_info)

    def force_complete(self, target_sim=None, score_override=None):
        self._actual_target_sim_info_id = target_sim.sim_info.id
        self._score_override = score_override
        self._on_goal_completed()

class SituationGoalRanInteractionOnTargetedSim(SituationGoalTargetedSim):
    INSTANCE_TUNABLES = {'_goal_test': event_testing.tests_with_data.TunableParticipantRanInteractionTest(locked_args={'participant': ParticipantType.Actor, 'tooltip': None})}

    @classmethod
    def can_be_given_as_goal(cls, actor, situation, inherited_target_sim_info=None, **kwargs):
        result = super(SituationGoalRanInteractionOnTargetedSim, cls).can_be_given_as_goal(actor, situation, inherited_target_sim_info=inherited_target_sim_info, **kwargs)
        if not result:
            return result
        return TestResult.TRUE

    def setup(self):
        super().setup()
        services.get_event_manager().register_tests(self, (self._goal_test,))

    def _decommision(self):
        services.get_event_manager().unregister_tests(self, (self._goal_test,))
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        if not resolver(self._goal_test):
            return False
        result = super()._run_goal_completion_tests(sim_info, event, resolver)
        if result:
            target_sim_info = self._get_target_sim_info_from_resolver(resolver)
            self._actual_target_sim_info_id = None if target_sim_info is None else target_sim_info.id
        return result

class SituationGoalRelationshipChangeTargetedSim(SituationGoalTargetedSim):
    INSTANCE_TUNABLES = {'_goal_test': TunableRelationshipTest(description='\n                The relationship state that this goal will complete when\n                obtained.\n                ', locked_args={'subject': ParticipantType.Actor, 'tooltip': None, 'target_sim': ParticipantType.TargetSim, 'num_relations': 0}), '_relationship_pretest': TunableRelationshipTest(description="\n                The pretest of the relationship.  Only sim's who match this\n                relationship test when the test begins are valid to have their\n                relationship change complete the test.\n                ", locked_args={'subject': ParticipantType.Actor, 'tooltip': None, 'target_sim': ParticipantType.TargetSim, 'num_relations': 0})}

    @classmethod
    def _can_sim_pass_test(cls, target_sim_info, actor_sim_info, inherited_target_sim_info):
        if not super(SituationGoalRelationshipChangeTargetedSim, cls)._can_sim_pass_test(target_sim_info, actor_sim_info, inherited_target_sim_info):
            return False
        resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
        return resolver(cls._relationship_pretest)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._possible_sims = set()

    def setup(self):
        super().setup()
        services.get_event_manager().register_single_event(self, event_testing.test_events.TestEvent.PrerelationshipChanged)
        services.get_event_manager().register_single_event(self, event_testing.test_events.TestEvent.RelationshipChanged)

    def _decommision(self):
        services.get_event_manager().unregister_single_event(self, event_testing.test_events.TestEvent.PrerelationshipChanged)
        services.get_event_manager().unregister_single_event(self, event_testing.test_events.TestEvent.RelationshipChanged)
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        target_sim_info = self._get_target_sim_info_from_resolver(resolver)
        if target_sim_info is None:
            return False
        target_sim_id = target_sim_info.id
        if event == event_testing.test_events.TestEvent.PrerelationshipChanged:
            if resolver(self._relationship_pretest):
                self._possible_sims.add(target_sim_id)
            else:
                self._possible_sims.discard(target_sim_id)
            return False
        if target_sim_id not in self._possible_sims:
            return False
        self._possible_sims.discard(target_sim_id)
        if not resolver(self._goal_test):
            return False
        result = super()._run_goal_completion_tests(sim_info, event, resolver)
        if result:
            self._actual_target_sim_info_id = target_sim_id
        return result

class SituationGoalEventRanSuccessfullyTargetedSim(SituationGoalTargetedSim):
    INSTANCE_TUNABLES = {'test_events_to_score': TunableMapping(description='\n            A mapping of test event -> score achieved when successfully ran.\n            ', key_type=TunableEnumEntry(description='\n                The event to listen to for goal completion.\n                ', tunable_type=TestEvent, default=TestEvent.Invalid), value_type=TunableTuple(description='\n                A tuple of the score to award and other checks to make on the \n                event before it satisfies the goal.\n                ', score=Tunable(description='\n                    The score the goal results in when completed.\n                    ', tunable_type=int, default=100), status=TunableEnumEntry(description='\n                    The status of the goal result. This will only change the \n                    visual when removing this goal from the list of goals.\n                    ', tunable_type=UiSituationGoalStatus, default=UiSituationGoalStatus.COMPLETED), interaction=OptionalTunable(description='\n                    When turned on there will be a test to verify that the \n                    interaction sending the associated test event is the same\n                    as the tuned interaction.\n                    ', tunable=TunableReference(description='\n                        The interaction to require the event to come from in\n                        order for it to satisfy the goal.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)))))}

    @classmethod
    def _can_sim_pass_test(cls, target_sim_info, actor_sim_info, inherited_target_sim_info):
        return True

    def setup(self):
        super().setup()
        for test_event in self.test_events_to_score:
            services.get_event_manager().register_single_event(self, test_event)

    def _decommision(self):
        for test_event in self.test_events_to_score:
            services.get_event_manager().unregister_single_event(self, test_event)
        super()._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        result = super()._run_goal_completion_tests(sim_info, event, resolver)
        if not result:
            return False
        event_score = self.test_events_to_score.get(event, None)
        if event_score.interaction is not None and event_score.interaction is not resolver.interaction.affordance:
            return False
        if event_score is not None:
            self._score_override = event_score.score
            self._goal_status_override = event_score.status
        return True
