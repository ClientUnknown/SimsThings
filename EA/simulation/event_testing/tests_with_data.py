from careers.career_enums import CareerCategoryfrom clock import interval_in_sim_minutesfrom date_and_time import create_time_spanfrom event_testing import TargetIdTypesfrom event_testing.results import TestResult, TestResultNumericfrom event_testing.test_events import TestEvent, cached_testfrom interactions import ParticipantType, ParticipantTypeActorTargetSimfrom interactions.utils.outcome import OutcomeResultfrom objects import ALL_HIDDEN_REASONSfrom objects.object_tests import TagTestTypefrom sims4.tuning.tunable import TunableEnumEntry, TunableVariant, TunableReference, TunableList, TunableSingletonFactory, TunableThreshold, OptionalTunable, Tunable, TunableSimMinute, TunableSet, TunableFactory, TunableTuple, AutoFactoryInit, HasTunableSingletonFactory, TunableEnumWithFilterfrom singletons import EMPTY_SETfrom tag import Tagimport build_buyimport enumimport event_testing.test_baseimport event_testing.test_eventsimport servicesimport sims4.resourcesimport snippetslogger = sims4.log.Logger('TestsWithEventData')
class InteractionTestEvents(enum.Int):
    InteractionComplete = event_testing.test_events.TestEvent.InteractionComplete
    InteractionStart = event_testing.test_events.TestEvent.InteractionStart
    InteractionUpdate = event_testing.test_events.TestEvent.InteractionUpdate

class ParticipantRanInteractionTest(event_testing.test_base.BaseTest):
    UNIQUE_TARGET_TRACKING_AVAILABLE = True
    UNIQUE_POSTURE_TRACKING_AVAILABLE = True
    TAG_CHECKLIST_TRACKING_AVAILABLE = True
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'description': 'Check to see if the Sim ran an affordance as a particular actor', 'participant': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='This is the role the sim in question should be to pass.'), 'affordances': TunableSet(description="\n            The Sim must have run either any affordance or have a proxied affordance\n            in this list or Affordance Lists, or an interaction matching\n            one of the tags in this tunable's Tags field.\n            ", tunable=TunableReference(services.affordance_manager(), pack_safe=True)), 'affordance_lists': TunableSet(description="\n            The Sim must have run either any affordance or have a proxied affordance\n            in Affordances or these Affordance Lists, or an interaction matching\n            one of the tags in this tunable's Tags field.\n            ", tunable=snippets.TunableAffordanceListReference()), 'interaction_outcome': OptionalTunable(TunableEnumEntry(OutcomeResult, OutcomeResult.NONE), description="The interaction's outcome must match the outcome tuned here to pass this test."), 'running_time': OptionalTunable(TunableSimMinute(description='\n            Amount of time in sim minutes that this interaction needs to\n            have been running for for this test to pass true. This time is how\n            long the interaction has been in the SI State.\n            \n            If your setting this, you probably want Test Event to be set to\n            InteractionUpdate.\n            ', default=10, minimum=0)), 'skill_tags': TunableSet(description='\n            Skill tags to check against skill attached to the interaction,\n            determined by if the interaction identifies it in skill  \n            loot data, or if it is an associated skill in the outcome.\n            \n            If you are setting this and are not using affordances or lists \n            for filtering, you probably want to ensure that you set\n            interaction tags that are more or equally restrictive to either \n            one of Interaction_Super or Interaction_Mixer.  And do not\n            use Interaction_All, unless you really want to trigger \n            for both mixers and super interactions.\n            ', tunable=TunableEnumWithFilter(tunable_type=Tag, default=Tag.INVALID, invalid_enums=Tag.INVALID, filter_prefixes=('skill',))), 'target_filters': TunableTuple(description='\n            Restrictions on the target of this interaction.\n            ', object_tags=OptionalTunable(description='\n                Object tags for limiting test success to a subset of target \n                objects.\n                ', tunable=TunableTuple(description='\n                    Target object tags and how they are tested.\n                    ', tag_set=TunableSet(description='\n                        A set of tags to test the target object for.\n                        ', tunable=TunableEnumEntry(description='\n                            A tag to test the target object for.\n                            ', tunable_type=Tag, default=Tag.INVALID)), test_type=TunableEnumEntry(description='\n                        How to test the tags in the tag set against the \n                        target object.\n                        ', tunable_type=TagTestType, default=TagTestType.CONTAINS_ANY_TAG_IN_SET)))), 'tags': TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='\n                The Sim must have run either an interaction matching one of these Tags \n                or an affordance from the list of Affordances in this tunable.\n                '), 'test_event': TunableEnumEntry(description='\n            The event that we want to trigger this instance of the tuned\n            test on.\n            InteractionStart: Triggers when the interaction starts.\n            InteractionComplete: Triggers when the interaction ends. This is best\n            used with a one shot interaction. It will not get called if an interaction\n            is canceled. If you have a Sim parked in an interaction that you can\n            only exit via cancel, you will not hit this.\n            InteractionUpdate: Triggers on a 15 sim minute cadence from the\n            start of the interaction.  If the interaction ends before a cycle\n            is up it does not trigger.  Do not use this for short interactions\n            as it has a possibility of never getting an update for an\n            interaction.\n            \n            \n            ', tunable_type=InteractionTestEvents, default=InteractionTestEvents.InteractionComplete), 'consider_user_cancelled_as_failure': Tunable(description='\n            If True, test will consider the interaction outcome to be Failure if\n            canceled by the user.\n            ', tunable_type=bool, default=True), 'consider_all_cancelled_as_failure': Tunable(description="\n            If True, test will consider the interaction outcome to be Failure if\n            canceled for any reason. If this box is checked and\n            consider_user_cancelled_as_failure is not checked, user cancel's\n            will still be treated as failures.\n            ", tunable_type=bool, default=False)}
    __slots__ = ('participant_type', '_affordances', '_affordance_lists', '_all_affordances', 'interaction_outcome', 'running_time', 'tags', 'object_tags', 'skill_tags', 'test_events', 'consider_user_cancelled_as_failure', 'consider_all_cancelled_as_failure')

    def __init__(self, participant, affordances, affordance_lists, interaction_outcome, running_time, skill_tags, target_filters, tags, test_event, consider_user_cancelled_as_failure, consider_all_cancelled_as_failure, **kwargs):
        super().__init__(**kwargs)
        self.participant_type = participant
        self._affordances = set(affordances)
        self._affordance_lists = affordance_lists
        self._all_affordances = None
        self.interaction_outcome = interaction_outcome
        if running_time is not None:
            self.running_time = interval_in_sim_minutes(running_time)
        else:
            self.running_time = None
        self.skill_tags = skill_tags
        self.tags = tags
        self.object_tags = target_filters.object_tags
        if test_event == InteractionTestEvents.InteractionUpdate:
            self.test_events = (test_event, InteractionTestEvents.InteractionComplete)
        else:
            self.test_events = (test_event,)
        self.consider_user_cancelled_as_failure = consider_user_cancelled_as_failure
        self.consider_all_cancelled_as_failure = consider_all_cancelled_as_failure

    def get_expected_args(self):
        return {'sims': event_testing.test_constants.SIM_INSTANCE, 'interaction': event_testing.test_constants.FROM_EVENT_DATA}

    @property
    def affordances(self):
        self._update_all_affordances()
        return set(self._all_affordances)

    def _update_all_affordances(self):
        if self._all_affordances is None:
            self._all_affordances = set(self._affordances)
            for affordance_list in self._affordance_lists:
                self._all_affordances.update(affordance_list)

    @cached_test
    def __call__(self, sims=None, interaction=None):
        if interaction is None:
            return TestResult(False, 'No interaction found, this is normal during zone load.')
        self._update_all_affordances()
        for sim_info in sims:
            participant_type = interaction.get_participant_type(sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS))
            if participant_type is None:
                return TestResult(False, 'Failed participant check: {} is not an instanced sim.', sim_info)
            if participant_type != self.participant_type:
                return TestResult(False, 'Failed participant check: {} != {}', participant_type, self.participant_type)
            tag_match = len(self.tags & interaction.get_category_tags()) > 0 if self.tags else False
            if tag_match or interaction.affordance in self._all_affordances or not (hasattr(interaction.affordance, 'proxied_affordance') and interaction.affordance.proxied_affordance in self._all_affordances):
                return TestResult(False, 'Failed affordance check: {} not in {}', interaction.affordance, self._all_affordances)
            if self.skill_tags:
                interaction_skill = interaction.get_associated_skill()
                if interaction_skill is None or len(self.skill_tags & set(interaction_skill.tags)) == 0:
                    return TestResult(False, 'Failed skill check: interaction does utilize a skill with specified tags {}.', self.skill_tags)
            if self.object_tags is not None and not self.target_matches_object_tags(interaction):
                return TestResult(False, "Target of interaction didn't match object tag requirement.")
            if self.interaction_outcome is not None:
                if self.consider_user_cancelled_as_failure and interaction.has_been_user_canceled and self.interaction_outcome != OutcomeResult.FAILURE:
                    return TestResult(False, 'Failed outcome check: interaction canceled by user treated as Failure')
                if self.consider_all_cancelled_as_failure and interaction.has_been_canceled and self.interaction_outcome != OutcomeResult.FAILURE:
                    return TestResult(False, 'Failed outcome check: interaction canceled and treated as Failure')
                if self.interaction_outcome == OutcomeResult.SUCCESS:
                    if interaction.global_outcome_result == OutcomeResult.FAILURE:
                        return TestResult(False, 'Failed outcome check: interaction({}) failed when OutcomeResult Success or None required.', interaction.affordance)
                elif self.interaction_outcome != interaction.global_outcome_result:
                    return TestResult(False, 'Failed outcome check: interaction({}) result {} not {}', interaction.affordance, interaction.global_outcome_result, self.interaction_outcome)
            else:
                if self.consider_user_cancelled_as_failure and interaction.has_been_user_canceled:
                    return TestResult(False, 'Failed outcome check: interaction canceled by user treated as Failure')
                if self.consider_all_cancelled_as_failure and interaction.has_been_canceled:
                    return TestResult(False, 'Failed outcome check: interaction canceled, and treated as Failure')
            running_time = interaction.consecutive_running_time_span
            if self.running_time is not None and running_time < self.running_time:
                return TestResult(False, 'Failed hours check: {} < {}', running_time, self.running_time)
        return TestResult.TRUE

    def get_test_events_to_register(self):
        return ()

    def get_custom_event_registration_keys(self):
        self._update_all_affordances()
        keys = []
        for test_event in self.test_events:
            keys.extend([(test_event, affordance) for affordance in self._all_affordances])
            keys.extend([(test_event, tag) for tag in self.tags])
            keys.extend([(test_event, skill_tag) for skill_tag in self.skill_tags])
        return keys

    def get_target_id(self, sims=None, interaction=None, id_type=None):
        if interaction is None or interaction.target is None:
            return
        if id_type == TargetIdTypes.DEFAULT or id_type == TargetIdTypes.DEFINITION:
            if interaction.target.is_sim:
                return interaction.target.id
            return interaction.target.definition.id
        if id_type == TargetIdTypes.INSTANCE:
            return interaction.target.id
        if id_type == TargetIdTypes.HOUSEHOLD:
            if not interaction.target.is_sim:
                logger.error('Unique target ID type: {} is not supported for test: {} with an object as target.', id_type, self)
                return
            return interaction.target.household.id
        if id_type == TargetIdTypes.PICKED_ITEM_ID:
            picked_items = interaction.interaction_parameters.get('picked_item_ids', EMPTY_SET)
            if len(picked_items) > 1:
                logger.error('Using PICKED_ITEM_ID on interaction {} that has more than one picked items.', interaction)
            for target_id in picked_items:
                return target_id
            logger.error('Using PICKED_ITEM_ID on interaction {} that has no picked items.', interaction)
            return
        logger.error('Unsupported TargetIdType {} for Test {}', id_type, self)

    def get_posture_id(self, sims=None, interaction=None):
        if interaction is None or interaction.sim is None or interaction.sim.posture is None:
            return
        return interaction.sim.posture.guid64

    def get_tags(self, sims=None, interaction=None):
        if interaction is None:
            return ()
        return interaction.interaction_category_tags

    def target_matches_object_tags(self, interaction=None):
        if interaction is None or interaction.target is None or interaction.target.is_sim:
            return False
        object_id = interaction.target.definition.id
        target_object_tags = set(build_buy.get_object_all_tags(object_id))
        if self.object_tags.test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
            return target_object_tags & self.object_tags.tag_set
        if self.object_tags.test_type == TagTestType.CONTAINS_ALL_TAGS_IN_SET:
            return target_object_tags & self.object_tags.tag_set == self.object_tags.tag_set
        elif self.object_tags.test_type == TagTestType.CONTAINS_NO_TAGS_IN_SET:
            return not target_object_tags & self.object_tags.tag_set
        return False
TunableParticipantRanInteractionTest = TunableSingletonFactory.create_auto_factory(ParticipantRanInteractionTest)
class ParticipantStartedInteractionTest(event_testing.test_base.BaseTest):
    test_events = (event_testing.test_events.TestEvent.InteractionStart,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'description': 'Check to see if the Sim started an affordance as a particular actor', 'participant': TunableEnumEntry(ParticipantType, ParticipantType.Actor, description='This is the role the sim in question should be to pass.'), 'affordances': TunableList(TunableReference(services.affordance_manager()), description="The Sim must have started either any affordance in this list or an interaction matching one of the tags in this tunable's Tags field."), 'tags': TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='The Sim must have run either an interaction matching one of these Tags or an affordance from the list of Affordances in this tunable.')}

    def __init__(self, participant, affordances, tags, **kwargs):
        super().__init__(**kwargs)
        self.participant_type = participant
        self.affordances = affordances
        self.tags = tags

    def get_test_events_to_register(self):
        return ()

    def get_custom_event_registration_keys(self):
        keys = [(TestEvent.InteractionStart, affordance) for affordance in self.affordances]
        keys.extend([(TestEvent.InteractionStart, tag) for tag in self.tags])
        return keys

    def get_expected_args(self):
        return {'sims': event_testing.test_constants.SIM_INSTANCE, 'interaction': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, sims=None, interaction=None):
        if interaction is None:
            return TestResult(False, 'No interaction found, this is normal during zone load.')
        for sim_info in sims:
            participant_type = interaction.get_participant_type(sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS))
            if participant_type is None:
                return TestResult(False, 'Failed participant check: {} is not an instanced sim.', sim_info)
            if participant_type != self.participant_type:
                return TestResult(False, 'Failed participant check: {} != {}', participant_type, self.participant_type)
            tag_match = len(self.tags & interaction.get_category_tags()) > 0 if self.tags else False
            if tag_match or interaction.affordance not in self.affordances:
                return TestResult(False, 'Failed affordance check: {} not in {}', interaction.affordance, self.affordances)
        return TestResult.TRUE

    def validate_tuning_for_objective(self, objective):
        if self.tags or not self.affordances:
            logger.error('Error in objective {}. No tags and affordances tuned.', objective)
TunableParticipantStartedInteractionTest = TunableSingletonFactory.create_auto_factory(ParticipantStartedInteractionTest)
class AwayActionTestEvents(enum.Int):
    AwayActionStart = event_testing.test_events.TestEvent.AwayActionStart
    AwayActionStop = event_testing.test_events.TestEvent.AwayActionStop

class ParticipantRanAwayActionTest(event_testing.test_base.BaseTest):
    UNIQUE_TARGET_TRACKING_AVAILABLE = True
    UNIQUE_POSTURE_TRACKING_AVAILABLE = False
    TAG_CHECKLIST_TRACKING_AVAILABLE = False
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'description': 'Check to see if the Sim ran an away action', 'participant': TunableEnumEntry(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor, description='This is the role the sim in question should be to pass.'), 'away_actions': TunableSet(description='\n            The Sim must have run an away action in this set\n            ', tunable=TunableReference(services.get_instance_manager(sims4.resources.Types.AWAY_ACTION), pack_safe=True)), 'test_event': TunableEnumEntry(description='\n            The event that we want to trigger this instance of the tuned\n            test on.\n            AwayActionStart: Triggers when the away action starts.\n            AwayActionStop: Triggers when the away action stops.\n            ', tunable_type=AwayActionTestEvents, default=AwayActionTestEvents.AwayActionStop)}
    __slots__ = ('participant_type', '_away_actions', 'test_events')

    def __init__(self, participant, away_actions, test_event, **kwargs):
        super().__init__(**kwargs)
        self.participant_type = participant
        self._away_actions = away_actions
        self.test_events = (test_event,)

    def get_expected_args(self):
        return {'sims': event_testing.test_constants.SIM_INSTANCE, 'away_action': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, sims=None, away_action=None):
        if away_action is None:
            return TestResult(False, 'No away_action found')
        for sim_info in sims:
            correct_sim_info = away_action.get_participant(self.participant_type)
            if correct_sim_info is not sim_info:
                return TestResult(False, 'Failed participant check: {} != {}', correct_sim_info, sim_info)
            if type(away_action) not in self._away_actions:
                return TestResult(False, 'Failed away action check: {} not in {}', away_action, self._away_actions)
        return TestResult.TRUE

    def get_test_events_to_register(self):
        return ()

    def get_custom_event_registration_keys(self):
        keys = []
        for test_event in self.test_events:
            keys.extend([(test_event, away_action) for away_action in self._away_actions])
        return keys

    def get_target_id(self, sims=None, away_action=None, id_type=None):
        if away_action is None or away_action.target is None:
            return
        if id_type == TargetIdTypes.DEFAULT or id_type == TargetIdTypes.DEFINITION:
            if away_action.target.is_sim:
                return away_action.target.id
            return away_action.target.definition.id
        if id_type == TargetIdTypes.INSTANCE:
            return away_action.target.id
        if id_type == TargetIdTypes.HOUSEHOLD:
            if not away_action.target.is_sim:
                logger.error('Unique target ID type: {} is not supported for test: {} with an object as target.', id_type, self)
                return
            else:
                return away_action.target.household.id
TunableParticipantRanAwayActionTest = TunableSingletonFactory.create_auto_factory(ParticipantRanAwayActionTest)
class SkillTestFactory(TunableFactory):

    @staticmethod
    def factory(skill_used, tags, skill_to_test):
        return skill_used is skill_to_test

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(skill_to_test=TunableReference(services.statistic_manager(), description='The skill used to earn the Simoleons, if applicable.'), **kwargs)

class TagSetTestFactory(TunableFactory):

    @staticmethod
    def factory(skill_used, tags, tags_to_test):
        if tags is None:
            return False
        return len(set(tags) & tags_to_test) > 0

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(tags_to_test=TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='The tags on the object for selling.'), **kwargs)

class SimoleonsEarnedTest(event_testing.test_base.BaseTest):
    test_events = (event_testing.test_events.TestEvent.SimoleonsEarned,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'description': 'Require the participant(s) to (each) earn a specific amount of Simoleons for a skill or tag on an object sold.', 'event_type_to_test': TunableVariant(skill_to_test=SkillTestFactory(), tags_to_test=TagSetTestFactory(), description='Test a skill for an event or tags on an object.'), 'threshold': TunableThreshold(description='Amount in Simoleons required to pass'), 'household_fund_threshold': OptionalTunable(description='\n            Restricts test success based on household funds.\n            ', tunable=TunableTuple(description='\n                Household fund threshold and moment of evaluation.\n                ', threshold=TunableThreshold(description='\n                    Amount of simoleons in household funds required to pass.\n                    '), test_before_earnings=Tunable(description='\n                    If True, threshold will be evaluated before funds were \n                    updated with earnings.\n                    ', tunable_type=bool, default=False)))}

    def __init__(self, event_type_to_test, threshold, household_fund_threshold, **kwargs):
        super().__init__(**kwargs)
        self.event_type_to_test = event_type_to_test
        self.threshold = threshold
        self.household_fund_threshold = household_fund_threshold

    def get_expected_args(self):
        return {'sims': event_testing.test_constants.SIM_INSTANCE, 'amount': event_testing.test_constants.FROM_EVENT_DATA, 'skill_used': event_testing.test_constants.FROM_EVENT_DATA, 'tags': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, sims=None, amount=None, skill_used=None, tags=None):
        if amount is None:
            return TestResultNumeric(False, 'SimoleonsEarnedTest: amount is none, valid during zone load.', current_value=0, goal_value=self.threshold.value, is_money=True)
        if not self.threshold.compare(amount):
            return TestResultNumeric(False, 'SimoleonsEarnedTest: not enough Simoleons earned.', current_value=amount, goal_value=self.threshold.value, is_money=True)
        if self.event_type_to_test is not None and not self.event_type_to_test(skill_used, tags):
            return TestResult(False, '\n                    SimoleonsEarnedTest: the skill used to earn Simoleons does\n                    not match the desired skill or tuned tags do not match\n                    object tags.\n                    ')
        if self.household_fund_threshold is not None:
            for sim_info in sims:
                household = services.household_manager().get_by_sim_id(sim_info.sim_id)
                if household is None:
                    return TestResult(False, "Couldn't find household for sim {}", sim_info)
                household_funds = household.funds.money
                if self.household_fund_threshold.test_before_earnings:
                    household_funds -= amount
                if not self.household_fund_threshold.threshold.compare(household_funds):
                    return TestResult(False, 'Threshold test on household funds failed for sim {}', sim_info)
        return TestResult.TRUE

    def goal_value(self):
        return self.threshold.value
TunableSimoleonsEarnedTest = TunableSingletonFactory.create_auto_factory(SimoleonsEarnedTest)
class FamilyAspirationTriggerTest(event_testing.test_base.BaseTest):
    test_events = (event_testing.test_events.TestEvent.FamilyTrigger,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'description': '\n            This is a special test used to receive the completion of a Familial\n            Aspiration. To properly use this test, one would create a Familial\n            Aspiration with an objective test on it, and tune the family\n            members who would care to receive it. Then create a new Aspiration\n            for the family members to receive it, and use this test to tune the\n            Familial Aspiration you created as the sender.\n        ', 'aspiration_trigger': TunableReference(description='\n            If this aspiration is completed because a family member completed\n            the corresponding trigger, the test will pass.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='AspirationFamilialTrigger'), 'target_family_relationships': TunableSet(description='\n            These relationship bits will get an event message upon Aspiration\n            completion that they can test for.\n            ', tunable=TunableReference(manager=services.relationship_bit_manager(), pack_safe=True))}

    def __init__(self, aspiration_trigger, target_family_relationships, **kwargs):
        super().__init__(**kwargs)
        self.aspiration_trigger = aspiration_trigger
        self.target_family_relationships = target_family_relationships

    def get_expected_args(self):
        return {'sim_infos': ParticipantType.Actor, 'trigger': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, sim_infos=None, trigger=None):
        if trigger is None:
            if sim_infos is not None:
                for sim_info in sim_infos:
                    for relationship in sim_info.relationship_tracker:
                        for relationship_bit in self.target_family_relationships:
                            if relationship.has_bit(sim_info.sim_id, relationship_bit):
                                target_sim_info = relationship.get_other_sim_info(sim_info.sim_id)
                                if target_sim_info is None:
                                    pass
                                else:
                                    target_aspiration_tracker = target_sim_info.aspiration_tracker
                                    if target_aspiration_tracker is not None and target_aspiration_tracker.milestone_completed(self.aspiration_trigger):
                                        return TestResult.TRUE
            return TestResult(False, 'FamilyAspirationTriggerTest: No valid sims with the aspiration found.')
        if self.aspiration_trigger.guid64 == trigger.guid64:
            return TestResult.TRUE
        return TestResult(False, 'FamilyAspirationTriggerTest: Tuned trigger {} does not match event trigger {}.', self.aspiration_trigger, trigger)
TunableFamilyAspirationTriggerTest = TunableSingletonFactory.create_auto_factory(FamilyAspirationTriggerTest)
class WhimCompletedTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (event_testing.test_events.TestEvent.WhimCompleted,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'whim_to_check': OptionalTunable(description='\n            Define them whim that is to be completed in order to pass the test.\n            ', tunable=TunableReference(description='\n                This is the whim to check for matching the completed whim,\n                resulting in passing test.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL)), enabled_name='Specific_Whim', disabled_name='Any_Whim')}

    def get_expected_args(self):
        return {'whim_completed': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, whim_completed=None):
        if whim_completed is None:
            return TestResult(False, 'WhimCompletedTest: Whim is empty, valid during zone load.')
        if self.whim_to_check is not None and self.whim_to_check.guid64 != whim_completed.guid64:
            return TestResult(False, 'WhimCompletedTest: Tuned whim to check {} does not match completed whim {}.', self.whim_to_check, whim_completed)
        return TestResult.TRUE
TunableWhimCompletedTest = TunableSingletonFactory.create_auto_factory(WhimCompletedTest)
class OffspringCreatedTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (event_testing.test_events.TestEvent.OffspringCreated,)
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'description': 'This test checks for a tuned number of offspring to have been created upon\n        the moment of the DeliverBabySuperInteraction completion.', 'offspring_threshold': TunableThreshold(description='\n            The comparison of amount of offspring created to the number desired.\n            ')}

    def get_expected_args(self):
        return {'offspring_created': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, offspring_created=None):
        if offspring_created is None:
            return TestResult(False, 'OffspringCreatedTest: Offspring count is empty, valid during zone load.')
        if not self.offspring_threshold.compare(offspring_created):
            return TestResult(False, 'OffspringCreatedTest: Not the desired amount of offspring created. {} {}', offspring_created, self.offspring_threshold)
        return TestResult.TRUE

class GenerationTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (event_testing.test_events.TestEvent.GenerationCreated,)
    FACTORY_TUNABLES = {'generation_threshold': TunableThreshold(description='\n            A household is considered only if at least one Sim in it satisfies\n            this threshold.\n            '), 'household_threshold': OptionalTunable(description='\n            If enabled, then this test must pass for the specified number of\n            households. If disabled, then this test must pass for the active\n            household only.\n            ', tunable=TunableThreshold(description="\n                Require a certain number of households to have at least one Sim\n                satisfying 'generation_threshold'.\n                "))}

    def get_expected_args(self):
        return {}

    def goal_value(self):
        if self.household_threshold is not None:
            return self.household_threshold.value
        return self.generation_threshold.value

    @cached_test
    def __call__(self):
        if self.household_threshold is None:
            active_household = services.active_household()
            generation_count = max(sim_info.generation for sim_info in active_household) if active_household is not None else 0
            if not self.generation_threshold.compare(generation_count):
                return TestResultNumeric(False, 'Generation Test: max generation is {}', generation_count, current_value=generation_count, goal_value=self.goal_value())
        else:
            household_count = sum(1 for household in services.household_manager().get_all() if household.hidden or any(self.generation_threshold.compare(sim_info.generation) for sim_info in household))
            if not self.household_threshold.compare(household_count):
                return TestResultNumeric(False, 'Generation Test: household count is {}', household_count, current_value=household_count, goal_value=self.goal_value())
        return TestResult.TRUE

class CareerAttendenceTest(event_testing.test_base.BaseTest):
    test_events = (event_testing.test_events.TestEvent.WorkdayComplete,)
    USES_DATA_OBJECT = True
    USES_EVENT_DATA = True
    FACTORY_TUNABLES = {'description': 'After a work day completes, did your sim work a desired of hours, earn a tuned amount (total over lifetime),                            at a specific or any career. Note: any career (leaving career untuned) means it checks against total of all of them.', 'career_to_test': TunableReference(manager=services.get_instance_manager(sims4.resources.Types.CAREER)), 'career_category': TunableEnumEntry(CareerCategory, CareerCategory.Invalid, description='Category the specified career is required to be in order to pass validation'), 'simoleons_earned': TunableThreshold(description='Amount in Simoleons required to pass'), 'hours_worked': TunableThreshold(description='Amount in hours required to pass')}

    def __init__(self, career_to_test, career_category, simoleons_earned, hours_worked, **kwargs):
        super().__init__(**kwargs)
        self.career_to_test = career_to_test
        self.simoleons_earned = simoleons_earned
        self.hours_worked = hours_worked
        self.career_category = career_category

    def get_expected_args(self):
        return {'career': event_testing.test_constants.FROM_EVENT_DATA, 'data': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, career=None, data=None, objective_guid64=None):
        if career is None:
            return TestResult(False, 'Career provided is None, valid during zone load.')
        total_money_made = 0
        total_time_worked = 0
        if self.career_to_test is not None:
            if not isinstance(career, self.career_to_test):
                return TestResult(False, '{} does not match tuned value {}', career, self.career_to_test)
            career_data = data.get_career_data(career)
            total_money_made = career_data.get_money_earned()
            total_time_worked = career_data.get_hours_worked()
            relative_start_values = data.get_starting_values(objective_guid64)
            if relative_start_values is not None:
                money = 0
                time = 1
                total_money_made -= relative_start_values[money]
                total_time_worked -= relative_start_values[time]
        for career_data in data.get_all_career_data().values():
            if self.career_category == CareerCategory.Invalid:
                total_money_made += career_data.get_money_earned()
                total_time_worked += career_data.get_hours_worked()
        if not self.simoleons_earned.compare(total_money_made):
            return TestResultNumeric(False, 'CareerAttendenceTest: not the desired amount of Simoleons.', current_value=total_money_made, goal_value=self.simoleons_earned.value, is_money=True)
        if not self.hours_worked.compare(total_time_worked):
            return TestResultNumeric(False, 'CareerAttendenceTest: not the desired amount of time worked.', current_value=total_time_worked, goal_value=self.hours_worked.value, is_money=False)
        return TestResult.TRUE

    def save_relative_start_values(self, objective_guid64, data_object):
        if self.career_to_test is not None:
            return
        career_name = self.career_to_test.__name__
        start_money = data_object.get_career_data_by_name(career_name).get_money_earned()
        start_time = data_object.get_career_data_by_name(career_name).get_hours_worked()
        data_object.set_starting_values(objective_guid64, [start_money, start_time])
TunableCareerAttendenceTest = TunableSingletonFactory.create_auto_factory(CareerAttendenceTest)
class TotalRelationshipBitTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.AddRelationshipBit,)
    USES_DATA_OBJECT = True
    FACTORY_TUNABLES = {'description': 'Gate availability by a relationship status.', 'use_current_relationships': Tunable(bool, False, description='Use the current number of relationships held at this bit rather than the total number ever had.'), 'relationship_bits': TunableSet(TunableReference(services.relationship_bit_manager(), description='The relationship bit that will be checked.', class_restrictions='RelationshipBit')), 'num_relations': TunableThreshold(description='Number of Sims with specified relationships required to pass.')}

    def __init__(self, use_current_relationships, relationship_bits, num_relations, **kwargs):
        super().__init__(**kwargs)
        self.use_current_relationships = use_current_relationships
        self.relationship_bits = relationship_bits
        self.num_relations = num_relations

    def get_expected_args(self):
        return {'data_object': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, data_object=None, objective_guid64=None):
        current_relationships = 0
        for relationship_bit in self.relationship_bits:
            if self.use_current_relationships:
                current_relationships += data_object.get_current_total_relationships(relationship_bit)
            else:
                current_relationships += data_object.get_total_relationships(relationship_bit)
        relative_start_value = data_object.get_starting_values(objective_guid64)
        if relative_start_value is not None:
            relations = 0
            current_relationships -= relative_start_value[relations]
        if not self.num_relations.compare(current_relationships):
            return TestResultNumeric(False, 'TotalRelationshipBitTest: Not enough relationships.', current_value=current_relationships, goal_value=self.num_relations.value, is_money=False)
        else:
            return TestResult.TRUE

    def save_relative_start_values(self, objective_guid64, data_object):
        current_relationships = 0
        for relationship_bit in self.relationship_bits:
            if self.use_current_relationships:
                current_relationships += data_object.get_current_total_relationships(relationship_bit)
            else:
                current_relationships += data_object.get_total_relationships(relationship_bit)
        data_object.set_starting_values(objective_guid64, [current_relationships])

    def validate_tuning_for_objective(self, objective):
        if not self.relationship_bits:
            logger.error('Error in objective {}. No relationship bits tuned.', objective)

    def goal_value(self):
        return self.num_relations.value
TunableTotalRelationshipBitTest = TunableSingletonFactory.create_auto_factory(TotalRelationshipBitTest)
class TotalTravelTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.SimTravel,)
    USES_DATA_OBJECT = True
    FACTORY_TUNABLES = {'description': 'Gate availability by a relationship status.', 'number_of_unique_lots': Tunable(description='\n            The number of unique lots that this account has traveled to in order for this test to pass.', tunable_type=int, default=0)}

    def __init__(self, number_of_unique_lots, **kwargs):
        super().__init__(**kwargs)
        self.number_of_unique_lots = number_of_unique_lots

    def get_expected_args(self):
        return {'data_object': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, sims=None, data_object=None, objective_guid64=None):
        zones_traveled = data_object.get_zones_traveled()
        relative_start_value = data_object.get_starting_values(objective_guid64)
        if relative_start_value is not None:
            zones = 0
            zones_traveled -= relative_start_value[zones]
        if zones_traveled >= self.number_of_unique_lots:
            return TestResult.TRUE
        else:
            return TestResultNumeric(False, 'TotalTravelTest: Not enough zones traveled to.', current_value=zones_traveled, goal_value=self.number_of_unique_lots, is_money=False)

    def save_relative_start_values(self, objective_guid64, data_object):
        zones_traveled = data_object.get_zones_traveled()
        data_object.set_starting_values(objective_guid64, [zones_traveled])

    def goal_value(self):
        return self.number_of_unique_lots
TunableTotalTravelTest = TunableSingletonFactory.create_auto_factory(TotalTravelTest)
class TotalSimoleonsEarnedByTagTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.SimoleonsEarned,)
    USES_DATA_OBJECT = True
    FACTORY_TUNABLES = {'description': 'Test for the total simoleons earned by selling objects tagged with tag_to_test.', 'tag_to_test': TunableEnumEntry(Tag, Tag.INVALID, description='The tags on the objects for selling.'), 'threshold': TunableThreshold(description='Amount in Simoleons required to pass')}

    def __init__(self, tag_to_test, threshold, **kwargs):
        super().__init__(**kwargs)
        self.tag_to_test = tag_to_test
        self.threshold = threshold

    def get_expected_args(self):
        return {'data_object': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, data_object=None, objective_guid64=None):
        total_simoleons_earned = data_object.get_total_tag_simoleons_earned(self.tag_to_test)
        relative_start_value = data_object.get_starting_values(objective_guid64)
        if relative_start_value is not None:
            simoleons = 0
            total_simoleons_earned -= relative_start_value[simoleons]
        if self.threshold.compare(total_simoleons_earned):
            return TestResult.TRUE
        else:
            return TestResultNumeric(False, 'TotalSimoleonsEarnedByTagTest: Not enough Simoleons earned on tag{}.', self.tag_to_test, current_value=total_simoleons_earned, goal_value=self.threshold.value, is_money=True)

    def save_relative_start_values(self, objective_guid64, data_object):
        total_simoleons_earned = data_object.get_total_tag_simoleons_earned(self.tag_to_test)
        data_object.set_starting_values(objective_guid64, [total_simoleons_earned])

    def validate_tuning_for_objective(self, objective):
        if self.tag_to_test is Tag.INVALID:
            logger.error('Error in objective {}. Tag is INVALID.', objective)
        if self.threshold.value == 0:
            logger.error('Error in objective {}. Threshold is 0.', objective)

    def goal_value(self):
        return self.threshold.value
TunableTotalSimoleonsEarnedByTagTest = TunableSingletonFactory.create_auto_factory(TotalSimoleonsEarnedByTagTest)
class TotalTimeElapsedByTagTest(event_testing.test_base.BaseTest):
    test_events = (TestEvent.InteractionComplete, TestEvent.InteractionUpdate)
    USES_DATA_OBJECT = True
    FACTORY_TUNABLES = {'description': 'Test for the total amount of time that interactions with tag_to_test has elapsed.', 'tag_to_test': TunableEnumEntry(Tag, Tag.INVALID, description='The tag on the interactions.'), 'length_of_time': TunableSimMinute(1, description='The total length of time that should be checked against.')}

    def __init__(self, tag_to_test, length_of_time, **kwargs):
        super().__init__(**kwargs)
        self.tag_to_test = tag_to_test
        self.length_of_time = interval_in_sim_minutes(length_of_time)

    def get_test_events_to_register(self):
        return ()

    def get_custom_event_registration_keys(self):
        return [(TestEvent.InteractionComplete, self.tag_to_test), (TestEvent.InteractionUpdate, self.tag_to_test)]

    def get_expected_args(self):
        return {'data_object': event_testing.test_constants.FROM_DATA_OBJECT, 'objective_guid64': event_testing.test_constants.OBJECTIVE_GUID64}

    @cached_test
    def __call__(self, data_object=None, objective_guid64=None):
        total_time_elapsed = data_object.get_total_tag_interaction_time_elapsed(self.tag_to_test)
        relative_start_value = data_object.get_starting_values(objective_guid64)
        if relative_start_value is not None:
            time = 0
            total_time_elapsed -= interval_in_sim_minutes(relative_start_value[time])
        if total_time_elapsed >= self.length_of_time:
            return TestResult.TRUE
        else:
            return TestResultNumeric(False, 'TotalTimeElapsedByTagTest: Not enough time elapsed on tag{}.', self.tag_to_test, current_value=total_time_elapsed.in_hours(), goal_value=self.length_of_time.in_hours(), is_money=False)

    def save_relative_start_values(self, objective_guid64, data_object):
        total_time_elapsed = data_object.get_total_tag_interaction_time_elapsed(self.tag_to_test)
        data_object.set_starting_values(objective_guid64, [int(total_time_elapsed.in_minutes())])

    def validate_tuning_for_objective(self, objective):
        if self.tag_to_test is Tag.INVALID:
            logger.error('Error in objective {}. Tag is INVALID.', objective)

    def goal_value(self):
        return self.length_of_time.in_hours()
TunableTotalTimeElapsedByTagTest = TunableSingletonFactory.create_auto_factory(TotalTimeElapsedByTagTest)
class InMultipleMoodsTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.MoodChange,)
    USES_DATA_OBJECT = True
    FACTORY_TUNABLES = {'required_moods': TunableList(description='\n            The moods that a Sim is required to have gone through within a \n            time frame.\n            ', tunable=TunableReference(description='\n                A mood that the Sim is required to have gone through with in a\n                time limit.\n                ', manager=services.get_instance_manager(sims4.resources.Types.MOOD)), unique_entries=True), 'time_limit': TunableSimMinute(description='\n            The amount of time that the Sim must have gone through all of the\n            previous moods in.\n            ', minimum=1, default=60)}

    def get_expected_args(self):
        return {'data_object': event_testing.test_constants.FROM_DATA_OBJECT}

    @cached_test
    def __call__(self, data_object=None):
        required_time = services.time_service().sim_now + create_time_span(minutes=-1*self.time_limit)
        for mood in self.required_moods:
            last_time_in_mood = data_object.get_last_time_in_mood(mood)
            if not last_time_in_mood is None:
                if last_time_in_mood < required_time:
                    return TestResult(False, 'Sim has not been in mood {} within the last {} Sim Minutes', mood, self.time_limit)
            return TestResult(False, 'Sim has not been in mood {} within the last {} Sim Minutes', mood, self.time_limit)
        return TestResult.TRUE
