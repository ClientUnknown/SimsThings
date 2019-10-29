import operatorfrom event_testing.resolver import DoubleSimResolverfrom event_testing.results import TestResultfrom event_testing.tests import TunableTestSetfrom gsi_handlers.greeting_handlers import GreetingRequestDatafrom interactions import ParticipantTypeSingleSimfrom interactions.constraints import TunableConefrom interactions.utils.loot_basic_op import BaseLootOperationfrom interactions.utils.reactions import TunableReactionMixer, TunableReactionSifrom relationships.relationship_bit import RelationshipBitfrom sims4.tuning.tunable import TunableTuple, Tunable, TunableList, TunableVariant, TunableReference, TunableEnumEntry, TunableSet, OptionalTunablefrom singletons import DEFAULTfrom tag import Tagimport enumimport gsi_handlersimport servicesimport sims4.logimport sims4.tuninglogger = sims4.log.Logger('Greetings', default_owner='rmccord')BRANCH = 'branch'LEAF = 'leaf'debug_add_greeted_rel_bit = True
class GreetingType(enum.Int):
    GREETING_GROUP = ...
    GREETING_TARGETED = ...

def add_greeted_rel_bit(a_sim_info, b_sim_info):
    if not debug_add_greeted_rel_bit:
        return
    a_sim_info.relationship_tracker.add_relationship_bit(b_sim_info.id, Greetings.GREETED_RELATIONSHIP_BIT, send_rel_change_event=False)

def remove_greeted_rel_bit(a_sim_info, b_sim_info):
    a_sim_info.relationship_tracker.remove_relationship_bit(b_sim_info.id, Greetings.GREETED_RELATIONSHIP_BIT, send_rel_change_event=False)

class TunableTestedGreeting(metaclass=sims4.tuning.instances.HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SNIPPET)):
    INSTANCE_SUBCLASSES_ONLY = True
    INSTANCE_TUNABLES = {'tests': TunableTestSet(description='\n            Tunable tests that run between the actor and target Sim. If the\n            test set passes, we either play a greeting or run through another\n            instance with tests.\n            '), 'context_testing': OptionalTunable(TunableTuple(description="\n            If enabled, advanced testing will be performed based on the social\n            interaction that led to this greeting.\n            \n            First, the Prohibited Interaction Tags are checked and we fail the\n            test if the source interaction contains one or more of them.\n            \n            Second, the Context Override Interaction Tags are checked, and we\n            immediately pass if the source interaction contains one or more of\n            them.\n            \n            Third, the Context Test Set is run, and determines the final result.\n            \n            Example: User does a mean social, but has positive rel, and we don't\n            want them to hug the target. So we put the tag for MeanSocials in\n            the prohibited tags to fail the hug greeting.\n            \n            Example: User does a mean social, but has positive rel, and we want\n            them to play a glare greeting. So we move the rel test to the\n            context test set, and put tags for MeanSocials in the context\n            override tags so that it ignores the rel test.\n            ", context_test_set=OptionalTunable(description='\n                If tuned, tunable tests that run between the actor and target\n                Sim. If the test set passes, we either play a greeting or run\n                through another instance with tests.\n                \n                These are essentially tests that would live in the regular\n                tests but we want them to be ignored if a particular\n                interaction is triggering the greeting.\n                \n                If no tests are tuned, we will treat this as a test failure.\n                \n                These tests will NOT run if Context Override Interaction Tags\n                are tuned and the source interaction has one of them. This will\n                cause these tests to auto-pass (even if this tunable is \n                disabled).\n                ', tunable=TunableTestSet(), enabled_name='allow_based_on_tests', disabled_name='allow_only_with_tags'), context_override_interaction_tags=TunableSet(description='\n                Interaction Category Tags that, if the source interaction\n                contains one or more of them, will ignore the context test set.\n                ', tunable=TunableEnumEntry(description='\n                    These tag values are used for testing the source\n                    interaction that started a greeting.\n                    ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True)), prohibited_interaction_tags=TunableSet(description='\n                Interaction Category Tags that, if the source interaction\n                contains one or more of them, will fail this Tested Greeting\n                and move to the next.\n                ', tunable=TunableEnumEntry(description='\n                    These tag values are used for testing the source\n                    interaction that started a greeting.\n                    ', tunable_type=Tag, default=Tag.INVALID, pack_safe=True))))}

    @classmethod
    def test(cls, resolver, source_interaction=None):
        result = TestResult.TRUE
        if cls.context_testing is not None:
            if source_interaction is None:
                return TestResult(False, 'Context-Tested Greeting does not have a source interaction.')
            interaction_tags = set(source_interaction.get_category_tags())
            prohibited_tags = interaction_tags & cls.context_testing.prohibited_interaction_tags
            if prohibited_tags:
                return TestResult(False, 'Context-Tested Greeting has prohibited tags {} that exist in {}', prohibited_tags, source_interaction)
            override_tags = interaction_tags & cls.context_testing.context_override_interaction_tags
            if not override_tags:
                if cls.context_testing.context_test_set is not None:
                    result = cls.context_testing.context_test_set.run_tests(resolver, resolver.skip_safe_tests)
                    if not result:
                        return TestResult(False, 'Context-Test Result: {}', result)
                else:
                    return TestResult(False, 'Context-Test Greeting has disabled context tests and interaction has none of the override tags')
        return result & cls.tests.run_tests(resolver, resolver.skip_safe_tests)

    @classmethod
    def _run_greeting(cls, sim, resolver, **kwargs):
        raise NotImplementedError

    def __new__(cls, sim, resolver, source_interaction=None, gsi_data=None, **kwargs):
        result = cls.test(resolver, source_interaction=source_interaction)
        if gsi_data is not None:
            gsi_data.add_test_result(cls, result)
        if result:
            if cls.tests_or_greeting.leaf_or_branch == BRANCH:
                for node in cls.tests_or_greeting.child_nodes:
                    result = node(sim, resolver, source_interaction=source_interaction, gsi_data=gsi_data, **kwargs)
                    if result:
                        return result
            elif cls.tests_or_greeting.leaf_or_branch == LEAF:
                result = cls._run_greeting(sim, resolver, source_interaction=source_interaction, **kwargs)
                if gsi_data is not None:
                    gsi_data.chosen_greeting = result.interaction
        return result

class TunableTestedGreetingGroup(TunableTestedGreeting):
    INSTANCE_TUNABLES = {'tests_or_greeting': TunableVariant(description="\n            Either play a greeting if the tests pass, or reference another\n            TunableTestedGreetingGroup that will perform it's behavior if the\n            tests pass.\n            ", tests=TunableTuple(description='\n                Child TunableTestedGreetingGroup nodes that run if the tests pass.\n                ', child_nodes=TunableList(description='\n                    A list of children to run through as children of this branch.\n                    If any one passes, it will not process any more children.\n                    ', tunable=TunableReference(description='\n                        A child node that represents a set of tests to run as\n                        well as child nodes or a greeting.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TunableTestedGreetingGroup',), pack_safe=True)), locked_args={'leaf_or_branch': BRANCH}), greeting=TunableTuple(description='\n                A mixer reaction greeting.\n                ', mixer=TunableReactionMixer(description='\n                    Mixer reactions that Sims can play before socializing. This\n                    particular reaction works well with Social Mixers because we\n                    can guarantee that the Sim will greet the target within social\n                    constraints. Just remember to override the super affordance to\n                    a social super interaction.\n                    ', get_affordance={'pack_safe': True}), locked_args={'leaf_or_branch': LEAF}))}

    @classmethod
    def _run_greeting(cls, sim, resolver, source_interaction=None, **kwargs):
        return cls.tests_or_greeting.mixer(sim, resolver, **kwargs)

class TunableTestedGreetingTargeted(TunableTestedGreeting):
    INSTANCE_TUNABLES = {'tests_or_greeting': TunableVariant(description="\n            Either play a greeting if the tests pass, or reference another\n            TunableTestedGreetingTargeted that will perform it's behavior if the\n            tests pass.\n            ", tests=TunableTuple(description='\n                Child TunableTestedGreetingTargeted nodes that run if the tests pass.\n                ', child_nodes=TunableList(description='\n                    A list of children to run through as children of this branch.\n                    If any one passes, it will not process any more children.\n                    ', tunable=TunableReference(description='\n                        A child node that represents a set of tests to run as\n                        well as child nodes or a greeting.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TunableTestedGreetingTargeted',), pack_safe=True)), locked_args={'leaf_or_branch': BRANCH}), greeting=TunableTuple(description='\n                ', si=TunableReactionSi(description='\n                    Super reactions that allow the Sim to play an SI before\n                    socializing. These can be Social Super Interactions which work\n                    well so that we guarantee the Sim is within social constraints.\n                    Since these can be touching socials, you can have a social\n                    super interaction that uses a jig group.\n                    ', get_affordance={'pack_safe': True}, get_priority={'enable_priority': False}), locked_args={'leaf_or_branch': LEAF}))}

    @classmethod
    def _run_greeting(cls, sim, resolver, source_interaction=None, **kwargs):
        if source_interaction is None:
            source = DEFAULT
            priority = DEFAULT
        else:
            source = source_interaction.source
            priority = source_interaction.priority
        return cls.tests_or_greeting.si(sim, resolver, source=source, priority=priority, **kwargs)

class GreetingLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'greeting_type': TunableEnumEntry(description='\n            The type of greeting we want to push.\n            ', tunable_type=GreetingType, default=GreetingType.GREETING_GROUP), 'greeting_target': TunableEnumEntry(description='\n            The participant to be targeted by the pushed interaction.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.TargetSim)}

    def __init__(self, *args, greeting_type, greeting_target, **kwargs):
        super().__init__(*args, **kwargs)
        self.greeting_type = greeting_type
        self.greeting_target = greeting_target

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if subject is None:
            logger.error('Attempting to play a reaction on a None subject for participant {}. Loot: {}', self.subject, self, owner='rmccord')
            return
        if not subject.is_sim:
            logger.error('Attempting to play a reaction on subject: {}, that is not a Sim. Loot: {}', self.subject, self, owner='rmccord')
            return
        target_sim_info = resolver.get_participant(self.greeting_target)
        greeting_resolver = DoubleSimResolver(subject, target_sim_info)
        subject_sim = subject.get_sim_instance()
        if subject_sim is None:
            return
        target_sim = target_sim_info.get_sim_instance()
        if self.greeting_type == GreetingType.GREETING_TARGETED:
            try_push_targeted_greeting_for_sim(subject_sim, target_sim, greeting_resolver)
        elif self.greeting_type == GreetingType.GREETING_GROUP:
            try_push_group_greeting_for_sim(subject_sim, target_sim, greeting_resolver)

class GreetingsSatisfyContraintTuning:
    CONE_CONSTRAINT = TunableCone(min_radius=0.7, max_radius=4, angle=sims4.math.PI, description=' Cone constraint sim must\n        satisfy before running greeting social. \n        \n        This is intersected with facing, line of sight and adjustment\n        constraint which is also done through code.\n        ')

class Greetings:
    GROUP_GREETINGS = TunableList(description='\n        Group greetings play on the Sim relative to a target Sim. These\n        greetings are only played on the actor. The PickedSim participant type\n        will contain all Sims that should greet the actor in return, so you can\n        make a reaction that greets the actor and push it from interactions in\n        this list.\n        ', tunable=TunableTuple(description='\n            Prioritized greetings. Place content that is pack specific at a\n            higher priority.\n            ', priority=Tunable(description='\n                The relative priority of this affordance compared to\n                other affordances in this list.\n                ', tunable_type=int, default=0), tests_and_greetings=TunableReference(description='\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TunableTestedGreetingGroup',), pack_safe=True)))
    TARGETED_GREETINGS = TunableList(description='\n        Targeted greetings play between two Sims and are only available in the\n        scenario that the actor wants to socialize with a target Sim that is\n        not already socializing. These can be touching socials like hugging or\n        hi fives.\n        ', tunable=TunableTuple(description='\n            Prioritized greetings. Place content that is pack specific at a\n            higher priority.\n            ', priority=Tunable(description='\n                The relative priority of this affordance compared to\n                other affordances in this list.\n                ', tunable_type=int, default=0), tests_and_greetings=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('TunableTestedGreetingTargeted',), pack_safe=True)))
    GREETED_RELATIONSHIP_BIT = RelationshipBit.TunableReference(description='\n        The relationship bit between greeted Sims.\n        ')

def _try_push_greeting_for_sim(sim, target_sim, resolver, prioritized_greetings, source_interaction=None, **kwargs):
    for prioritized_greeting in sorted(prioritized_greetings, key=operator.attrgetter('priority'), reverse=True):
        result = prioritized_greeting.tests_and_greetings(sim, resolver, source_interaction=source_interaction, **kwargs)
        if result:
            return result
    return TestResult(False, 'Could not find a valid Reaction Mixer for actor: {}, target: {}', sim, target_sim)

def try_push_group_greeting_for_sim(sim, target_sim, resolver, source_interaction=None, **kwargs):
    greeting_request_data = GreetingRequestData(sim.id, target_sim.id, 'GROUP', source_interaction=source_interaction)
    result = _try_push_greeting_for_sim(sim, target_sim, resolver, Greetings.GROUP_GREETINGS, source_interaction=source_interaction, gsi_data=greeting_request_data, **kwargs)
    if gsi_handlers.greeting_handlers.archiver.enabled:
        gsi_handlers.greeting_handlers.archive_greeting_request(sim.id, target_sim.id, greeting_request_data)
    return result

def try_push_targeted_greeting_for_sim(sim, target_sim, resolver, source_interaction=None, **kwargs):
    greeting_request_data = GreetingRequestData(sim.id, target_sim.id, 'TARGETED', source_interaction=source_interaction)
    result = _try_push_greeting_for_sim(sim, target_sim, resolver, Greetings.TARGETED_GREETINGS, source_interaction=source_interaction, gsi_data=greeting_request_data, **kwargs)
    if gsi_handlers.greeting_handlers.archiver.enabled:
        gsi_handlers.greeting_handlers.archive_greeting_request(sim.id, target_sim.id, greeting_request_data)
    return result
