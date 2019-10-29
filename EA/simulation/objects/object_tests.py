import collectionsimport functoolsimport itertoolsfrom broadcasters.environment_score.environment_score_types import EnvironmentScoreTypefrom event_testing import TargetIdTypesfrom event_testing.resolver import RESOLVER_PARTICIPANTfrom event_testing.results import TestResult, TestResultNumericfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_test, TestEventfrom interactions import ParticipantType, ParticipantTypeSingle, ParticipantTypeActorTargetSim, ParticipantTypeSingleSimfrom objects import ALL_HIDDEN_REASONSfrom objects.components.inventory_enums import InventoryTypefrom objects.components.types import STORED_AUDIO_COMPONENTfrom sims4.math import MAX_INT32, Operatorfrom sims4.resources import Typesfrom sims4.tuning.geometric import TunableDistanceSquaredfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableThreshold, TunableReference, TunableVariant, Tunable, OptionalTunable, TunableTuple, TunableFactory, TunableList, TunableSet, TunablePackSafeReference, TunableInterval, TunableEnumFlags, TunableEnumWithFilter, TunableOperator, TunableResourceKeyfrom singletons import EMPTY_SETfrom tag import Tag, TunableTagfrom tunable_utils.tunable_object_generator import TunableObjectGeneratorVariantimport enumimport event_testing.test_baseimport objects.components.inventory_enumsimport routingimport servicesimport simsimport sims4import statistics.moodimport taglogger = sims4.log.Logger('ObjectTests', default_owner='bosee')
class TagTestType(enum.Int):
    CONTAINS_ANY_TAG_IN_SET = 1
    CONTAINS_ALL_TAGS_IN_SET = 2
    CONTAINS_NO_TAGS_IN_SET = 3

class StateTestType(enum.Int):
    CONTAINS_ANY_STATE_IN_SET = 1
    CONTAINS_ALL_STATES_IN_SET = 2
    CONTAINS_NO_STATE_IN_SET = 3

class ObjectCriteriaTestEvents(enum.Int):
    AllObjectEvents = 0
    OnExitBuildBuy = TestEvent.OnExitBuildBuy
    ObjectStateChange = TestEvent.ObjectStateChange
    ItemCrafted = TestEvent.ItemCrafted
    OnInventoryChanged = TestEvent.OnInventoryChanged

class ObjectTypeFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'actual_object': TunablePackSafeReference(description='\n            The object we want to test ownership of', manager=services.definition_manager())}

    def __call__(self, obj):
        if self.actual_object is None:
            return False
        return obj.definition.id == self.actual_object.id

    def get_all_objects(self, object_manager):
        if self.actual_object is None:
            return EMPTY_SET
        return frozenset(obj for obj in object_manager.values() if obj.definition.id == self.actual_object.id)

class ObjectTagFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'tag_set': TunableSet(TunableEnumEntry(description='\n                    What tag to test for.\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID, pack_safe=True)), 'test_type': TunableEnumEntry(description='\n                How to test the tags in the tag set against the objects on the lot.\n                ', tunable_type=TagTestType, default=TagTestType.CONTAINS_ANY_TAG_IN_SET)}

    def __call__(self, obj):
        if obj.is_sim:
            return False
        else:
            object_tags = set(obj.get_tags())
            if self.test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
                if object_tags & self.tag_set:
                    return True
                return False
            elif self.test_type == TagTestType.CONTAINS_ALL_TAGS_IN_SET:
                if object_tags & self.tag_set == self.tag_set:
                    return True
                return False
            elif self.test_type == TagTestType.CONTAINS_NO_TAGS_IN_SET:
                if not object_tags & self.tag_set:
                    return True
                return False
        return False
        logger.error('ObjectTagFactory recieved unrecognized TagTestType {}, defaulting to False', self.test_type, owner='tingyul')
        return False

    def get_all_objects(self, object_manager):
        objects_matching_any_tag = set()
        if self.test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
            for tag in self.tag_set:
                matching_objects = object_manager.get_objects_matching_tags((tag,))
                if matching_objects is None:
                    pass
                else:
                    objects_matching_any_tag.update(matching_objects)
        elif self.test_type == TagTestType.CONTAINS_ALL_TAGS_IN_SET:
            objects_matching_any_tag = object_manager.get_objects_matching_tags(self.tag_set)
            if objects_matching_any_tag is None:
                return EMPTY_SET
        else:
            if self.test_type == TagTestType.CONTAINS_NO_TAGS_IN_SET:
                return set(obj for obj in object_manager.values() if obj.is_sim or not set(obj.get_tags() & self.tag_set))
            logger.error('ObjectTagFactory recieved unrecognized TagTestType {}, defaulting to False', self.test_type, owner='msantander')
        objects_matching_any_tag = set(obj for obj in objects_matching_any_tag if not obj.is_sim)
        return objects_matching_any_tag

class ObjectTrendingFactory(HasTunableSingletonFactory, AutoFactoryInit):

    def __call__(self, obj):
        if obj.is_sim:
            return False
        object_tags = set(obj.get_tags())
        trend_tags = set(services.trend_service().get_current_trend_tags())
        return trend_tags & object_tags

    def get_all_objects(self, object_manager):
        objects_matching_any_tag = set()
        trend_tags = services.trend_service().get_current_trend_tags()
        for tag in trend_tags:
            matching_objects = object_manager.get_objects_matching_tags((tag,))
            if matching_objects:
                objects_matching_any_tag.update(matching_objects)
        return set(obj for obj in objects_matching_any_tag if not obj.is_sim)

class CraftedWithSkillFactory(TunableFactory):

    @staticmethod
    def factory(crafted_object, skill, skill_to_test):
        return skill is skill_to_test

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(skill_to_test=TunableReference(services.statistic_manager(), description='Skills needed to pass amount on.'), description='This option tests for an item craft with the selected skill', **kwargs)

class CraftActualItemFactory(TunableFactory):

    @staticmethod
    def factory(crafted_object, skill, items_to_check):
        item_ids = [definition.id for definition in items_to_check]
        return crafted_object.definition.id in item_ids

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(items_to_check=TunableList(TunableReference(services.definition_manager(), description='Object that qualifies for this check.')), description='This option tests crafted item against a list of possible items', **kwargs)

class CraftTaggedItemFactory(TunableFactory):

    @staticmethod
    def factory(crafted_object, skill, tag_set, test_type, **kwargs):
        object_tags = crafted_object.get_tags()
        if test_type == TagTestType.CONTAINS_ANY_TAG_IN_SET:
            return object_tags & tag_set
        if test_type == TagTestType.CONTAINS_ALL_TAGS_IN_SET:
            return object_tags & tag_set == tag_set
        elif test_type == TagTestType.CONTAINS_NO_TAGS_IN_SET:
            return not object_tags & tag_set
        return False

    FACTORY_TYPE = factory
    DEFAULT_DESCRIPTION = "This option tests crafted item's tags against a list of possible tags"

    def __init__(self, description=DEFAULT_DESCRIPTION, **kwargs):
        super().__init__(tag_set=TunableSet(TunableEnumEntry(tag.Tag, tag.Tag.INVALID, pack_safe=True, description='What tag to test for'), description='The tag of objects we want to test ownership of'), test_type=TunableEnumEntry(TagTestType, TagTestType.CONTAINS_ANY_TAG_IN_SET, description='How to test the tags in the tag set against the objects on the lot.'), description=description, **kwargs)

class BasicStateCheckFactory(TunableFactory):
    TAG_TYPE = 1
    DEFINITION_TYPE = 2

    @staticmethod
    def factory(tested_object, state_set, test_type, object_requirement, **kwargs):
        if tested_object.state_component is None:
            return False
        if object_requirement.type == BasicStateCheckFactory.TAG_TYPE:
            if not object_requirement.tag(tested_object, None):
                return False
        elif object_requirement.type == BasicStateCheckFactory.DEFINITION_TYPE and tested_object.definition is not object_requirement.definition:
            return False
        object_states = set(tested_object.state_component.values())
        if object_requirement is not None and test_type == StateTestType.CONTAINS_ANY_STATE_IN_SET:
            return object_states & state_set
        if test_type == StateTestType.CONTAINS_ALL_STATES_IN_SET:
            return object_states & state_set == state_set
        elif test_type == StateTestType.CONTAINS_NO_STATE_IN_SET:
            return object_states & state_set == 0
        return False

    FACTORY_TYPE = factory

    def __init__(self, **kwargs):
        super().__init__(description="\n            This option tests crafted item's tags against a list of possible\n            tags.", state_set=TunableSet(TunableReference(description='\n                What state to test for.', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE))), test_type=TunableEnumEntry(description='\n                How to test the states in the state set against the objects in\n                the inventory.', tunable_type=StateTestType, default=StateTestType.CONTAINS_ANY_STATE_IN_SET), object_requirement=TunableVariant(tag=TunableTuple(tag=CraftTaggedItemFactory(description='\n                        The object must have this tag.\n                        '), locked_args={'type': BasicStateCheckFactory.TAG_TYPE}), definition=TunableTuple(definition=TunableReference(description='\n                        The object must have this definition.\n                        ', manager=services.definition_manager()), locked_args={'type': BasicStateCheckFactory.DEFINITION_TYPE}), locked_args={'any_object': None}, default='any_object'), **kwargs)

class ObjectIdPairTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n            Who or what to apply this test to\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Actor), 'target': TunableEnumEntry(description='\n            Who or what to use for the comparison\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantType.Object), 'threshold': TunableThreshold(description='\n            The comparison to perform against the value. The test passes if \n            the sum of two ids modded 100 passes the comparison.')}

    def get_expected_args(self):
        return {'actors': self.actor, 'targets': self.target}

    @cached_test
    def __call__(self, actors, targets):
        source = next(iter(actors), None)
        target = next(iter(targets), None)
        randomized_source = source.id*48271 % MAX_INT32 if source is not None else 0
        randomized_target = target.id*48271 % MAX_INT32 if target is not None else 0
        test_percent = (randomized_source + randomized_target) % 100
        if not self.threshold.compare(test_percent):
            return TestResult(False, 'Tested {} against value {} and failed.', test_percent, self.threshold.value, tooltip=self.tooltip)
        return TestResult.TRUE

class TunableObjectStateValueThreshold(TunableThreshold):

    def __init__(self, **kwargs):

        def threshold_callback(instance_class, tunable_name, source, threshold):
            threshold_value = threshold.value
            if hasattr(threshold_value, 'value'):
                threshold.value = threshold_value.value

        super().__init__(value=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue', **kwargs), callback=threshold_callback)

class ObjectPurchasedTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.ObjectAdd,)
    FACTORY_TUNABLES = {'test_type': TunableVariant(description='\n            The object we want to test for.\n            ', object=ObjectTypeFactory.TunableFactory(), tag_set=ObjectTagFactory.TunableFactory(), locked_args={'any_object': None}, default='any_object'), 'value_threshold': TunableThreshold(description="\n            The condition the object's value (in Simoleons) is required to\n            satisfy in order for the test to pass.\n            "), 'use_depreciated_value': Tunable(description='\n            If checked, the value consideration for purchased object will at its\n            depreciated amount.\n            ', tunable_type=bool, default=False)}

    @property
    def value(self):
        return self.value_threshold.value

    def get_expected_args(self):
        return {'obj': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, obj=None):
        if obj is None:
            return TestResultNumeric(False, 'ObjectPurchasedTest: Object is None, normal during zone load.', current_value=0, goal_value=self.value_threshold.value, is_money=True)
        if self.test_type is not None and not self.test_type(obj):
            return TestResultNumeric(False, 'ObjectPurchasedTest: Invalid object type: {}', obj, current_value=0, goal_value=self.value_threshold.value, is_money=True)
        obj_value = obj.depreciated_value if self.use_depreciated_value else obj.catalog_value
        if not self.value_threshold.compare(obj_value):
            return TestResultNumeric(False, 'ObjectPurchasedTest: Incorrect or invalid value object purchased for test: {}, value: {}', obj, obj_value, current_value=obj_value, goal_value=self.value_threshold.value, is_money=True)
        return TestResult.TRUE

class ObjectScoringPreferenceTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'require': Tunable(description="\n            The Sim's preference is required to be True or required to be False.\n            ", tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {'affordance': ParticipantType.Affordance, 'targets': ParticipantType.Object, 'context': ParticipantType.InteractionContext}

    @cached_test
    def __call__(self, affordance=None, targets=None, context=None):
        preference = affordance.autonomy_preference.preference or affordance.super_affordance.autonomy_preference.preference
        if preference is not None:
            for target in targets:
                is_object_scoring_preferred = context.sim.is_object_use_preferred(preference.tag, target)
                if is_object_scoring_preferred != self.require:
                    return TestResult(False, 'Object preference disallows this interaction.', tooltip=self.tooltip)
            return TestResult.TRUE
        logger.error('A preference tunable test is set on {}, but preference tuning is unset of the affordance.', affordance)
        return TestResult.TRUE

class ObjectEnvironmentScoreTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': "\n            Test the object's environment score for a particular mood againts a threshold.\n            ", 'sim_participant': OptionalTunable(description='\n            An Optional Sim to test Environment Score against. If disabled, the\n            Environment Score will not take into acount any Trait modifiers\n            relative to the Sim. If enabled, Trait modifiers will be taken into\n            account.\n            ', tunable=TunableEnumEntry(tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.TargetSim)), 'object_to_test': TunableEnumEntry(description='\n            The object particiant we want to check the environment score of.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'environment_score_type': TunableVariant(description='\n            The type of environment score to test against. This can be mood\n            based, positive scoring, or negative scoring.\n            ', mood_scoring=TunableTuple(description="\n                Test for a particular mood's environment score on the object.\n                ", mood_to_check=statistics.mood.Mood.TunableReference(description="\n                    The mood to check the participant's environment scoring.\n                    "), threshold=TunableThreshold(description="\n                    The threshold for this mood's scoring to pass.\n                    "), locked_args={'scoring_type': EnvironmentScoreType.MOOD_SCORING}), positive_scoring=TunableTuple(description="\n                Test for the object's positive environment scoring.\n                ", threshold=TunableThreshold(description='\n                    The threshold for negative scoring to pass.\n                    '), locked_args={'scoring_type': EnvironmentScoreType.POSITIVE_SCORING}), negative_scoring=TunableTuple(description="\n                Test for the object's negative environment scoring.\n                ", threshold=TunableThreshold(description='\n                    The threshold for positive scoring to pass.\n                    '), locked_args={'scoring_type': EnvironmentScoreType.NEGATIVE_SCORING}), default='mood_scoring'), 'ignore_emotional_aura': Tunable(description='\n            Whether or not this test cares if Emotional Aura is\n            Enabled/Disabled. If this is checked and the emotional aura is\n            disabled (EmotionEnvironment_Disabled is on the object), then\n            there will be no mood scoring and the test will fail if\n            checking moods. If unchecked, any mood scoring will always\n            affect this test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        expected_args = {'objects_to_test': self.object_to_test}
        if self.sim_participant is not None:
            expected_args['sim'] = self.sim_participant
        return expected_args

    @cached_test
    def __call__(self, objects_to_test=None, sim=None):
        if objects_to_test is None:
            return TestResult(False, 'No Object for this affordance.', tooltip=self.tooltip)
        for target in objects_to_test:
            (mood_scores, negative_score, positive_score, _) = target.get_environment_score(sim, ignore_disabled_state=self.ignore_emotional_aura)
            if self.environment_score_type.scoring_type == EnvironmentScoreType.MOOD_SCORING:
                mood_score = mood_scores.get(self.environment_score_type.mood_to_check, 0.0)
                if not self.environment_score_type.threshold.compare(mood_score):
                    return TestResult(False, 'Object does not meet environment score requirements for mood {}.'.format(self.environment_score_type.mood_to_check), tooltip=self.tooltip)
                    if self.environment_score_type.scoring_type == EnvironmentScoreType.POSITIVE_SCORING:
                        if not self.environment_score_type.threshold.compare(positive_score):
                            return TestResult(False, 'Object does not meet positive environment score requirements.', tooltip=self.tooltip)
                            if self.environment_score_type.scoring_type == EnvironmentScoreType.NEGATIVE_SCORING and not self.environment_score_type.threshold.compare(negative_score):
                                return TestResult(False, 'Object does not meet negative environment score requirements.', tooltip=self.tooltip)
                    elif self.environment_score_type.scoring_type == EnvironmentScoreType.NEGATIVE_SCORING and not self.environment_score_type.threshold.compare(negative_score):
                        return TestResult(False, 'Object does not meet negative environment score requirements.', tooltip=self.tooltip)
            elif self.environment_score_type.scoring_type == EnvironmentScoreType.POSITIVE_SCORING:
                if not self.environment_score_type.threshold.compare(positive_score):
                    return TestResult(False, 'Object does not meet positive environment score requirements.', tooltip=self.tooltip)
                    if self.environment_score_type.scoring_type == EnvironmentScoreType.NEGATIVE_SCORING and not self.environment_score_type.threshold.compare(negative_score):
                        return TestResult(False, 'Object does not meet negative environment score requirements.', tooltip=self.tooltip)
            elif self.environment_score_type.scoring_type == EnvironmentScoreType.NEGATIVE_SCORING and not self.environment_score_type.threshold.compare(negative_score):
                return TestResult(False, 'Object does not meet negative environment score requirements.', tooltip=self.tooltip)
        return TestResult.TRUE

class CraftedItemTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.ItemCrafted,)
    UNIQUE_TARGET_TRACKING_AVAILABLE = True
    TAG_CHECKLIST_TRACKING_AVAILABLE = True
    FACTORY_TUNABLES = {'skill_or_item': TunableVariant(description='\n            Whether to test for a specific item or use of a skill for the item.\n            ', crafted_with_skill=CraftedWithSkillFactory(), crafted_actual_item=CraftActualItemFactory(), crafted_tagged_item=CraftTaggedItemFactory(), default='crafted_with_skill'), 'quality_threshold': OptionalTunable(description='\n            If enabled, require the item to match a certain quality threshold.\n            ', tunable=TunableObjectStateValueThreshold(description='\n                The quality threshold to satisfy.\n                ')), 'masterwork_threshold': OptionalTunable(description='\n            If enabled, require the item to match a certain masterwork\n            threshold.\n            ', tunable=TunableObjectStateValueThreshold(description='\n                The masterwork threshold to satisfy.\n                '))}

    def get_expected_args(self):
        return {'crafted_object': event_testing.test_constants.FROM_EVENT_DATA, 'skill': event_testing.test_constants.FROM_EVENT_DATA, 'quality': event_testing.test_constants.FROM_EVENT_DATA, 'masterwork': event_testing.test_constants.FROM_EVENT_DATA}

    @cached_test
    def __call__(self, crafted_object=None, skill=None, quality=None, masterwork=None):
        if crafted_object is None:
            return TestResult(False, 'CraftedItemTest: Object created is None, normal during zone load.')
        match = self.skill_or_item(crafted_object, skill)
        if not match:
            return TestResult(False, 'CraftedItemTest: Object created either with wrong skill or was not being checked.')
        if self.masterwork_threshold is not None:
            if masterwork is None:
                return TestResult(False, 'CraftedItemTest: Looking for a masterwork and object masterwork state was None.')
            if not self.masterwork_threshold.compare(masterwork.value):
                return TestResult(False, 'CraftedItemTest: Object does not match masterwork state level desired.')
        if self.quality_threshold is not None:
            if quality is None:
                return TestResult(False, 'CraftedItemTest: Item quality is None.')
            if not self.quality_threshold.compare(quality.value):
                return TestResult(False, 'CraftedItemTest: Item is not of desired quality.')
        return TestResult.TRUE

    def get_target_id(self, crafted_object=None, skill=None, quality=None, masterwork=None, id_type=None):
        if crafted_object is None:
            return
        if id_type == TargetIdTypes.DEFAULT or id_type == TargetIdTypes.DEFINITION:
            return crafted_object.definition.id
        if id_type == TargetIdTypes.INSTANCE:
            return crafted_object.id
        logger.error('Unique target ID type: {} is not supported for test: {}', id_type, self)

    def get_tags(self, crafted_object=None, skill=None, quality=None, masterwork=None):
        if crafted_object is None:
            return ()
        return crafted_object.get_tags()

class CountTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):

    class _TunableParticipantCountThreshold(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'participant': TunableObjectGeneratorVariant(description="\n                The participant whose count is used as the threshold's value.\n                "), 'comparison': TunableOperator(description='\n                The comparison to perform against the value.\n                ', default=Operator.GREATER_OR_EQUAL)}
        needs_resolver = True

        def compare(self, source_value, resolver):
            participants = self.participant.get_objects(resolver)
            return self.comparison(source_value, len(participants))

    FACTORY_TUNABLES = {'participant': TunableObjectGeneratorVariant(description='\n            The participant that is being counted.\n            '), 'threshold': TunableVariant(description='\n            The value to compare the participant count to.\n            ', from_value=TunableThreshold(), from_count=_TunableParticipantCountThreshold.TunableFactory(), default='from_value')}

    def get_expected_args(self):
        return {'resolver': RESOLVER_PARTICIPANT}

    @cached_test
    def __call__(self, *, resolver):
        participants = self.participant.get_objects(resolver)
        if getattr(self.threshold, 'needs_resolver', False):
            compare_fn = functools.partial(self.threshold.compare, resolver=resolver)
        else:
            compare_fn = self.threshold.compare
        if not compare_fn(len(participants)):
            return TestResult(False, 'Does not have the required number of participants.', tooltip=self.tooltip)
        return TestResult.TRUE

class ExistenceTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant for which to check existence.\n            ', tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'exists': Tunable(description='\n            When checked, require the specified participant to exist. When\n            unchecked, require the specified participant to not exist.\n            ', tunable_type=bool, default=True), 'require_instantiated': Tunable(description="\n            If checked, the participant will also be checked for instantiation.\n            This is helpful when the participant might be a SimInfo (e.g.\n            StoredSim) and we just want to check if it exists and don't care if\n            the Sim is actually instantiated.\n            ", tunable_type=bool, default=True), 'allow_hidden_sim_status': Tunable(description="\n            If checked then we will ignore hidden Sim status such that they will count as existing even though they\n            have been hidden.  Use this in conjunction with Require Instantiated in order to determine the Sim's actual\n            instantiated status. \n            ", tunable_type=bool, default=False), 'require_instantiatable': Tunable(description='\n            If checked, the specified participant must be instantiatable. This\n            is generally true for all Sims at LOD above MINIMUM.\n            ', tunable_type=bool, default=True)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    def _exists(self, obj):
        if obj is None:
            return False
        if self.participant == ParticipantType.StoredSimOrNameData:
            return True
        if obj.is_sim:
            if self.require_instantiatable and not obj.can_instantiate_sim:
                return False
            elif self.require_instantiated:
                allow_hidden_flags = 0
                if self.allow_hidden_sim_status:
                    allow_hidden_flags = ALL_HIDDEN_REASONS
                if not obj.is_instanced(allow_hidden_flags=allow_hidden_flags):
                    return False
            return True
        return not obj.is_hidden() and obj.id in services.object_manager()

    @cached_test
    def __call__(self, test_targets=()):
        if self.exists:
            if not (test_targets and all(self._exists(obj) for obj in test_targets)):
                return TestResult(False, 'Participant {} does not exist', self.participant, tooltip=self.tooltip)
        elif any(self._exists(obj) for obj in test_targets):
            return TestResult(False, 'Participant {} exists', self.participant, tooltip=self.tooltip)
        return TestResult.TRUE

class InventoryTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    PARTICIPANT_INVENTORY = 0
    GLOBAL_OBJECT_INVENTORY = 1
    HIDDEN_INVENTORY = 2
    TAGGED_ITEM_TEST = 0
    ITEM_DEFINITION_TEST = 1
    PARTICIPANT_TYPE_TEST = 2
    ITEM_STATE_TEST = 3
    test_events = (TestEvent.OnInventoryChanged,)
    FACTORY_TUNABLES = {'inventory_location': TunableVariant(description='\n            Who owns the inventory. Either look in the inventory of a \n            participant or specify an object inventory type directly.\n            \n            If participant returns multiple inventory owners, the test will \n            pass only if ALL of those owners pass the inventory content test.\n            ', participant_inventory=TunableTuple(inventory=TunableEnumEntry(description='\n                    The owner of the inventory\n                    ', tunable_type=ParticipantType, default=ParticipantType.Actor), locked_args={'location_type': PARTICIPANT_INVENTORY}), object_inventory_type=TunableTuple(inventory=TunableEnumEntry(description='\n                    Check the global Object inventory that has the specified type.\n                    EX: check in the global fridge inventory that exists for all\n                    fridges\n                    ', tunable_type=objects.components.inventory_enums.InventoryType, default=objects.components.inventory_enums.InventoryType.UNDEFINED), locked_args={'location_type': GLOBAL_OBJECT_INVENTORY}), hidden_inventory_objects=TunableTuple(inventory=TunableEnumEntry(description='\n                    Check in the hidden inventory for objects that can go into the\n                    specified inventory type. EX: check that there are mailbox\n                    objects in the hidden inventory\n                    ', tunable_type=objects.components.inventory_enums.InventoryType, default=objects.components.inventory_enums.InventoryType.UNDEFINED), locked_args={'location_type': HIDDEN_INVENTORY}), default='participant_inventory'), 'contents_check': TunableVariant(description='\n            Checks to run on each object of the specified inventory\n            ', has_object_with_tag=CraftTaggedItemFactory(locked_args={'content_check_type': TAGGED_ITEM_TEST}), has_object_with_def=TunableTuple(definition=TunablePackSafeReference(description='\n                    The object definition to look for inside inventory.\n                    ', manager=services.definition_manager()), locked_args={'content_check_type': ITEM_DEFINITION_TEST}), has_object_of_participant_type=TunableTuple(description='\n                Participant type we want to test if its in the selected\n                inventory.\n                ', participant=TunableEnumEntry(description='\n                    Which participant of the interaction do we want to validate\n                    on the inventory. \n                    ', tunable_type=ParticipantType, default=ParticipantType.Object), locked_args={'content_check_type': PARTICIPANT_TYPE_TEST}), has_object_with_states=BasicStateCheckFactory(locked_args={'content_check_type': ITEM_STATE_TEST}), locked_args={'has_anything': None}, default='has_anything'), 'required_count': TunableThreshold(description='\n            The inventory must have a tunable threshold of objects that\n            pass the contents check test.\n            \n            EX: test is object definition of type pizza. required count is enabled\n            and has a threshold of >= 5. That means this test will pass if you\n            have 5 or more pizzas in your inventory. To check if any objects\n            exist, use required count >= 1\n            ', value=Tunable(int, 1, description='The value of a threshold.'), default=sims4.math.Threshold(1, sims4.math.Operator.GREATER_OR_EQUAL.function))}

    def get_expected_args(self):
        arguments = {}
        if self.inventory_location.location_type == InventoryTest.PARTICIPANT_INVENTORY:
            arguments['inventory_owners'] = self.inventory_location.inventory
        if self.contents_check.content_check_type == self.PARTICIPANT_TYPE_TEST:
            arguments['content_check_participant'] = self.contents_check.participant
        return arguments

    @cached_test
    def __call__(self, inventory_owners=None, content_check_participant=None):
        inventories = []
        location_type = self.inventory_location.location_type
        if not inventory_owners:
            if location_type == InventoryTest.GLOBAL_OBJECT_INVENTORY:
                inventories = services.active_lot().get_object_inventories(self.inventory_location.inventory)
            else:
                hidden_inventories = services.active_lot().get_object_inventories(objects.components.inventory_enums.InventoryType.HIDDEN)
                inventory = []
                for hidden_inventory in hidden_inventories:
                    for obj in hidden_inventory:
                        if obj.can_go_in_inventory_type(self.inventory_location.inventory):
                            inventory.append(obj)
                inventories.append(inventory)
            if not inventories:
                return TestResult(False, 'Inventory {} does not exist or has no items', self.inventory_location, tooltip=self.tooltip)
        for inventory_owner in inventory_owners:
            if inventory_owner.is_sim:
                if inventory_owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'Participant {} is not an instantiated sim.', inventory_owner, tooltip=self.tooltip)
                inventory_owner = inventory_owner.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            inventory = inventory_owner.inventory_component
            if inventory is None:
                return TestResult(False, 'Participant {} does not have an inventory', inventory_owner, tooltip=self.tooltip)
            inventories.append(inventory)
        for inv in inventories:
            count = 0
            contents_check = self.contents_check
            if contents_check is None:
                count = len(inv)
            else:
                content_check_type = contents_check.content_check_type
                for item in inv:
                    item_definition_id = item.definition.id
                    if content_check_type == self.ITEM_DEFINITION_TEST:
                        if item_definition_id == contents_check.definition.id:
                            count += item.stack_count()
                    elif content_check_type == self.TAGGED_ITEM_TEST:
                        if self.contents_check(item, None):
                            count += item.stack_count()
                    elif content_check_type == self.PARTICIPANT_TYPE_TEST:
                        for check_participant in content_check_participant:
                            if item_definition_id == check_participant.definition.id:
                                count += item.stack_count()
                    elif content_check_type == self.ITEM_STATE_TEST:
                        if self.contents_check(item):
                            count += item.stack_count()
                    else:
                        logger.error('Unsupported content check type {} in Inventory Test', content_check_type, owner='yshan')
                        break
            if not self.required_count.compare(count):
                return TestResultNumeric(False, 'Inventory {} does not have required number of objects in it', inv, tooltip=self.tooltip, current_value=count, goal_value=self.required_count.value, is_money=False)
        return TestResultNumeric(True, current_value=count, goal_value=self.required_count.value, is_money=False)

    def goal_value(self):
        return self.required_count.value

class InInventoryTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant to test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'inventory_types': TunableSet(description='\n            Inventory types to test against. If this is any, the test will\n            consider ALL inventory types.\n            ', tunable=TunableEnumEntry(description='\n                The inventory type to test.\n                ', tunable_type=InventoryType, default=InventoryType.UNDEFINED, invalid_enums=(InventoryType.UNDEFINED,))), 'negate': Tunable(description='\n            If enabled, we will check that the participant IS NOT in any of the\n            specified inventory types. If disabled, we will check that the\n            participant IS in at least one of the specified inventory types.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'objs': self.participant}

    @cached_test
    def __call__(self, objs):
        for obj in objs:
            if not obj.is_in_inventory():
                if not self.negate:
                    return TestResult(False, 'Failed InInventory test because participant is not in an inventory.', tooltip=self.tooltip)
                    inventoryitem_component = obj.inventoryitem_component
                    current_inventory_type = inventoryitem_component.current_inventory_type
                    if not self.inventory_types:
                        if self.negate:
                            return TestResult(False, 'Failed InInventory test. Participant is unexpectedly in an inventory.', tooltip=self.tooltip)
                            if current_inventory_type in self.inventory_types == self.negate:
                                return TestResult(False, "Failed InInventory test. Participant's current inventory type does not match expected tuning.", tooltip=self.tooltip)
                    elif current_inventory_type in self.inventory_types == self.negate:
                        return TestResult(False, "Failed InInventory test. Participant's current inventory type does not match expected tuning.", tooltip=self.tooltip)
            else:
                inventoryitem_component = obj.inventoryitem_component
                current_inventory_type = inventoryitem_component.current_inventory_type
                if not self.inventory_types:
                    if self.negate:
                        return TestResult(False, 'Failed InInventory test. Participant is unexpectedly in an inventory.', tooltip=self.tooltip)
                        if current_inventory_type in self.inventory_types == self.negate:
                            return TestResult(False, "Failed InInventory test. Participant's current inventory type does not match expected tuning.", tooltip=self.tooltip)
                elif current_inventory_type in self.inventory_types == self.negate:
                    return TestResult(False, "Failed InInventory test. Participant's current inventory type does not match expected tuning.", tooltip=self.tooltip)
        return TestResult.TRUE

class ObjectRelationshipTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'sims': TunableEnumEntry(description='\n            The Sim(s) to test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'targets': TunableEnumEntry(description='\n            The object(s) to test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'relationship_status': TunableVariant(description="\n            Whether the object cannot have a relationship with the sim, or the\n            sim and object's relationship value is within a tuned range.\n            \n            For test on relationship range:\n            If a sim does not have a relationship with the object and\n            use_default_value_if_no_relationship is checked, the relationship \n            value used will be the initial value of the relationship statistic\n            used to track relationships on the object. If sim doesn't have a\n            relationship and use_default_value_if_no_relationship is NOT checked,\n            the test will fail (so you can use that to check if a relationship\n            exists).\n            ", relationship_range=TunableTuple(use_default_value_if_no_relationship=Tunable(description="\n                    If checked, the initial value of the relationship stat will\n                    be used if the sim and object do not already have a\n                    relationship. If unchecked, the test will fail if the sim\n                    and object don't have a relationship.\n                    ", tunable_type=bool, default=False), value_interval=TunableInterval(tunable_type=float, default_lower=-100, default_upper=100)), locked_args={'no_relationship_exists': None}, default='relationship_range'), 'can_add_relationship': OptionalTunable(Tunable(description='\n            If checked, this object must be able to add a new relationship.  If\n            unchecked, this object must not be able to add any more\n            relationships.\n            ', tunable_type=bool, default=True))}

    def get_expected_args(self):
        return {'sims': self.sims, 'targets': self.targets}

    @cached_test
    def __call__(self, sims, targets):
        for sim in sims:
            for target in targets:
                relationship_component = target.objectrelationship_component
                if relationship_component is None:
                    return TestResult(False, 'Target {} has no object relationship component attached.', target, tooltip=self.tooltip)
                has_relationship = relationship_component.has_relationship(sim.id)
                if self.relationship_status is None:
                    if has_relationship:
                        return TestResult(False, 'Target {} has a relationship with Sim {} but is required not to.', target, sim, tooltip=self.tooltip)
                else:
                    if self.relationship_status.use_default_value_if_no_relationship or not has_relationship:
                        return TestResult(False, 'Target {} does not have a relationship with Sim {} and test does not allow default values.', target, sim, tooltip=self.tooltip)
                    relationship_value = relationship_component.get_relationship_value(sim.id)
                    if relationship_value < self.relationship_status.value_interval.lower_bound or relationship_value > self.relationship_status.value_interval.upper_bound:
                        return TestResult(False, "Target {}'s relationship with Sim {} is {}, which is not within range [{}, {}]", target, sim, relationship_value, self.relationship_status.value_interval.upper_bound, self.relationship_status.value_interval.lower_bound, tooltip=self.tooltip)
                if self.can_add_relationship is not None and self.can_add_relationship != relationship_component._can_add_new_relationship:
                    return TestResult(False, "Target {}'s ability to add new relationships is {} but the requirement is {} .", target, relationship_component._can_add_new_relationship, self.can_add_relationship, tooltip=self.tooltip)
        return TestResult.TRUE

class CustomNameTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The subject who is the object of this test.', tunable_type=ParticipantType, default=ParticipantType.Object), 'has_custom_name': OptionalTunable(Tunable(description='\n            If checked, the subject must have a custom name set. If unchecked, it cannot have a custom name set.', tunable_type=bool, default=True)), 'has_custom_description': OptionalTunable(Tunable(description='\n            If checked, the subject must have a custom description set. If unchecked, it cannot have a custom description set.', tunable_type=bool, default=True))}

    def get_expected_args(self):
        return {'targets': self.participant}

    @cached_test
    def __call__(self, targets=()):
        for target in targets:
            if target.is_sim:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'Target is not an instanced sim {}.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if self.has_custom_name is not None and target.has_custom_name() != self.has_custom_name:
                return TestResult(False, "Target's custom name fails requirements.", tooltip=self.tooltip)
            if self.has_custom_description is not None and target.has_custom_description() != self.has_custom_description:
                return TestResult(False, "Target's custom description fails requirements.", tooltip=self.tooltip)
        return TestResult.TRUE

class InUseTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):

    class Candidates(enum.Int):
        NON_ACTORS = 0
        NON_ACTOR_HOUSEHOLD_MEMBERS = 1
        NON_ACTOR_NON_HOUSEHOLD_MEMBERS = 2
        PICKED_SIM = 3
        NOT_ACTORS_OR_ENSEMBLE = 4

    FACTORY_TUNABLES = {'targets': TunableEnumFlags(description='\n            Targets to check whether in use.\n            ', enum_type=ParticipantType, default=ParticipantType.Object), 'negate': Tunable(description='\n            If unchecked, this test will pass when the object is in use.\n            If checked, this test will pass when the object is not in use.\n            \n            If a number using range is specified, then if checked the test will\n            pass when the number using is outside the specified range.  Either\n            too many or too few.\n            ', tunable_type=bool, default=False), 'candidates': TunableEnumEntry(description='\n            Which sims will be considered users of the target.\n            ', tunable_type=Candidates, default=Candidates.NON_ACTORS), 'number_using': OptionalTunable(description='\n            An optional interval to specify an inclusive range of valid sims\n            that must be using the target(s) Too few or too many, and the test\n            will fail.\n            ', tunable=TunableInterval(tunable_type=int, default_lower=1, default_upper=1000, minimum=0))}

    def get_expected_args(self):
        return {'actors': ParticipantType.Actor, 'targets': self.targets, 'picked_sim': ParticipantType.PickedSim}

    def advanced_test(self, sim, actors):
        if sim.sim_info in actors:
            return False
        is_in_household = any(actor.household is sim.household for actor in actors)
        should_be_in_household = self.candidates == self.Candidates.NON_ACTOR_HOUSEHOLD_MEMBERS
        return is_in_household == should_be_in_household

    def actor_or_group_test(self, sim, actors):
        if sim.sim_info in actors:
            return False
        for actor in actors:
            if sim in services.ensemble_service().get_ensemble_sims_for_rally(actor.get_sim_instance()):
                return False
        return True

    @cached_test
    def __call__(self, actors=None, targets=None, picked_sim=None):
        for target in targets:
            if target.is_part:
                target = target.part_owner
            all_users = target.get_users()
            sim_users = target.get_users(sims_only=True)
            if self.number_using is not None:
                if self.candidates == self.Candidates.PICKED_SIM:
                    num_using = sum(sim.sim_info in picked_sim for sim in sim_users)
                elif self.candidates == self.Candidates.NON_ACTORS:
                    num_using = sum(sim.sim_info not in actors for sim in sim_users)
                else:
                    num_using = sum(self.advanced_test(sim, actors) for sim in sim_users)
                correct_count = self.number_using.lower_bound <= num_using <= self.number_using.upper_bound
                if correct_count ^ self.negate:
                    return TestResult.TRUE
                return TestResult(False, 'InUseTest: Number of users required to be {} {} and {}, but the actual number of users is {}.', 'without' if self.negate else 'within', self.number_using.lower_bound, self.number_using.upper_bound, num_using, tooltip=self.tooltip)
            if self.candidates == self.Candidates.PICKED_SIM:
                has_users = any(sim.sim_info in picked_sim for sim in sim_users)
            elif self.candidates == self.Candidates.NON_ACTORS:
                has_users = any(sim.sim_info not in actors for sim in sim_users)
            elif self.candidates == self.Candidates.NOT_ACTORS_OR_ENSEMBLE:
                has_users = any(self.actor_or_group_test(sim, actors) for sim in sim_users)
            else:
                has_users = any(self.advanced_test(sim, actors) for sim in sim_users)
            if len(all_users) > len(sim_users):
                has_users = True
            if has_users or has_users ^ self.negate:
                return TestResult.TRUE
        return TestResult(False, 'Failed in_use test because object {} in use', 'is' if self.negate else "isn't", tooltip=self.tooltip)

class HasFreePartTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'targets': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'part_definition': TunableReference(description='\n            The part definition to check against.\n            ', manager=services.object_part_manager())}

    def get_expected_args(self):
        return {'actor': ParticipantType.Actor, 'targets': self.targets}

    def _base_tests(self, target):
        test_result = TestResult.TRUE
        target_parts = None
        if target is None:
            logger.error('Trying to call HasPartFreeTest on {} which is None', target)
            test_result = TestResult(False, 'Target({}) does not exist', self.targets)
            return (test_result, target_parts)
        if target.is_part:
            target = target.part_owner
        target_parts = target.parts
        if target_parts is None:
            logger.warn('Trying to call HasPartFreeTest on {} which has no parts. This is a tuning error.', target)
            test_result = TestResult(False, 'Failed has_part_free test because object has no parts at all', tooltip=self.tooltip)
        return (test_result, target_parts)

    @cached_test
    def __call__(self, actor=None, targets=None):
        if actor is None:
            logger.error('Trying to call HasPartFreeTest with no actor.', actor)
            return TestResult(False, 'Actor does not exist for the HasPartFreeTest')
        sim_info = next(iter(actor), None)
        sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        test_result = TestResult(False, 'Failed has_part_free test because no targets exist.', tooltip=self.tooltip)
        for target in targets:
            (test_result, target_parts) = self._base_tests(target)
            if test_result:
                if not any(part.may_reserve(sim) for part in target_parts if part.part_definition is self.part_definition):
                    return TestResult(False, 'Failed has_part_free test because object has no free parts of the tuned definition', tooltip=self.tooltip)
                return TestResult.TRUE
        return test_result

class HasParentObjectTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'targets': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'negate': Tunable(description="\n            If set to True, the test will pass if targets DON'T have parent.\n            ", tunable_type=bool, default=False), 'parent_object': OptionalTunable(description='\n            If enabled the parent of the object has to be the specified \n            participant to pass/fail the test.\n            ', tunable=TunableEnumEntry(description='\n                Who or what to apply this test to.\n                ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor))}

    def get_expected_args(self):
        expected_args = {'targets': self.targets}
        if self.parent_object is not None:
            expected_args['parent_objects'] = self.parent_object
        return expected_args

    @cached_test
    def __call__(self, targets=None, parent_objects=None):
        for target in targets:
            target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) if target.is_sim else target
            if parent_objects is None:
                if self.negate:
                    if target.parent is not None:
                        return TestResult(False, 'Parent test fail because object {} has parent'.format(target), tooltip=self.tooltip)
                elif target.parent is None:
                    return TestResult(False, "Parent test fail because object {} doesn't have parent".format(target), tooltip=self.tooltip)
            else:
                if target.parent is not None and target.parent.is_sim:
                    test_parent = target.parent.sim_info
                else:
                    test_parent = target.parent
                if self.negate:
                    if target.parent is not None:
                        for parent in parent_objects:
                            if test_parent is parent:
                                return TestResult(False, 'Parent test fail because object {} is parented to {}', target, test_parent, tooltip=self.tooltip)
                else:
                    if target.parent is None:
                        return TestResult(False, "Parent test fail because object {} doesn't have parent".format(target), tooltip=self.tooltip)
                    for parent in parent_objects:
                        if test_parent is not parent:
                            return TestResult(False, 'Parent test fail because object {} is not parented to {}', target, test_parent, tooltip=self.tooltip)
        return TestResult.TRUE

class HasObjectOfTypeAsChildTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'targets': TunableEnumEntry(description='\n            The target(s) that must have an object of the specified type as a \n            child in order for the test to pass. \n            \n            NOTE: if you pass in an object that has parts that contain an\n            object of the specified type this will return True. You want to \n            specify the exact part to test for a child of the correct type.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'object_type_tags': TunableList(description='\n            A list of the type of object tags to check for.\n            ', tunable=TunableEnumWithFilter(description='\n                The tag that the object must have in order for it to count for the\n                test.\n                ', tunable_type=Tag, filter_prefixes=['func'], default=Tag.INVALID, pack_safe=True)), 'negate': Tunable(description='\n            If set to True, the test will pass if the subroot index we are\n            looking for has no children.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'targets': self.targets}

    @cached_test
    def __call__(self, targets=()):
        if not targets:
            return TestResult(False, 'Trying to test for an associated booth seat when the target to test is None', tooltip=self.tooltip)
        for target in targets:
            for child in target.children:
                if child.is_prop:
                    pass
                elif child.has_any_tag(self.object_type_tags):
                    break
            return TestResult(False, 'Specified target object {} does not have a child with the tag {}', target, self.object_type_tags, tooltip=self.tooltip)
        return TestResult.TRUE

class HasChildObjectOnPartTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'targets': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'subroot_index': OptionalTunable(description='\n            If enabled we will look at a specific subroot index.  Otherwise we\n            will look at parts that do not have a subroot index.\n            ', tunable=Tunable(description='\n                The subroot index/suffix associated with the part we want to\n                look at.\n                ', tunable_type=int, default=0, needs_tuning=False), enabled_by_default=True), 'negate': Tunable(description='\n            If set to True, the test will pass if the subroot index we are\n            looking for has no children.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'targets': self.targets}

    @cached_test
    def __call__(self, targets=()):
        if not targets:
            return TestResult(False, 'HasChildObjectOnPartTest: No test targets given.', tooltip=self.tooltip)
        found_match = False
        for target in targets:
            if target.is_part:
                target = target.part_owner
            for part in target.parts:
                if part.subroot_index is None or self.subroot_index is None:
                    if not part.subroot_index is not None:
                        if self.subroot_index is not None:
                            pass
                        elif part.children:
                            if not self.negate:
                                found_match = True
                                break
                                if self.negate:
                                    found_match = True
                                    break
                        elif self.negate:
                            found_match = True
                            break
                elif part.subroot_index != self.subroot_index:
                    pass
                elif part.children:
                    if not self.negate:
                        found_match = True
                        break
                        if self.negate:
                            found_match = True
                            break
                elif self.negate:
                    found_match = True
                    break
                if part.children:
                    if not self.negate:
                        found_match = True
                        break
                        if self.negate:
                            found_match = True
                            break
                elif self.negate:
                    found_match = True
                    break
            if found_match:
                break
        if not found_match:
            if self.negate:
                return TestResult(False, 'HasChildObjectOnPartTest: No part at subroot {} found without children.', self.subroot_index, tooltip=self.tooltip)
            return TestResult(False, 'HasChildObjectOnPartTest: No part at subroot {} found with children.', self.subroot_index, tooltip=self.tooltip)
        return TestResult.TRUE

class HasInUsePartTest(HasFreePartTest):

    @cached_test
    def __call__(self, actor=None, targets=None):
        for target in targets:
            (test_result, target_parts) = self._base_tests(target)
            if test_result:
                if not any(part.in_use for part in target_parts if part.part_definition is self.part_definition):
                    test_result = TestResult(False, 'Failed has_part_in_use test because object has no parts in use of the tuned definition', tooltip=self.tooltip)
                else:
                    return TestResult.TRUE
        return test_result

class ObjectHasNoChildrenTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'targets': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'check_part_owner': Tunable(description='\n            If enabled and target of tests is a part, the test will be run\n            on the part owner instead.\n            ', tunable_type=bool, default=False), 'consider_bb_only_children': Tunable(description='\n            If this is true then objects that are BB_ONLY children will count\n            for the purposes of this test. \n            \n            Example: The campfire is allowed to have chairs slotted into it \n            that are BB_ONLY children. If this is not true then this test will\n            fail.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'targets': self.targets}

    @cached_test
    def __call__(self, targets=()):
        for target in targets:
            if target.is_part:
                target = target.part_owner
            if self.check_part_owner and any(not slot.empty for slot in target.get_runtime_slots_gen()):
                return TestResult(False, 'ObjectHasNoChildrenTest: Object found in slot', tooltip=self.tooltip)
            if self.consider_bb_only_children:
                for _ in target.get_all_children_gen():
                    return TestResult(False, 'ObjectHasNoChildrenTest: Child object found in object {}', target, tooltip=self.tooltip)
        return TestResult.TRUE

class IsCarryingObjectTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The subject of this test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'object_type': TunableVariant(object_reference=TunableReference(description='\n                A type of object required to be carried.\n                ', manager=services.definition_manager()), object_tag=TunableEnumEntry(description='\n                A tag to test the target object for.\n                ', tunable_type=Tag, default=Tag.INVALID), default='object_reference'), 'negate': Tunable(description='\n            If checked the test will fail if the user is carrying the object.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=None):
        for target in test_targets:
            sim = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if sim is None:
                return TestResult(False, 'IsCarryingObjectTest: {} is not an instanced sim.', target, tooltip=self.tooltip)
            is_carrying = sim.posture_state.is_carrying(self.object_type)
            if is_carrying and self.negate:
                return TestResult(False, 'IsCarryingObjectTest: {} is carrying {}.', sim.full_name, self.object_type, tooltip=self.tooltip)
            if is_carrying or not self.negate:
                return TestResult(False, 'IsCarryingObjectTest: {} is not carrying {}.', sim.full_name, self.object_type, tooltip=self.tooltip)
        return TestResult.TRUE

class HasHeadParentedObjectTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant who will be verified if it has an object attached\n            to its head.\n            ', tunable_type=ParticipantTypeActorTargetSim, default=ParticipantTypeActorTargetSim.Actor), 'negate': Tunable(description="\n            If enabled test will pass if the participant doesn't have an object\n            set as head.\n            ", tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets):
        for participant in test_targets:
            participant_sim = participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if self.negate:
                if participant_sim.current_object_set_as_head is not None:
                    return TestResult(False, 'Participant {} does have object {} parented', participant_sim, participant_sim.current_object_set_as_head(), tooltip=self.tooltip)
                    if participant_sim.current_object_set_as_head is None:
                        return TestResult(False, 'Participant {} has no object parented to sims head', participant_sim, tooltip=self.tooltip)
            elif participant_sim.current_object_set_as_head is None:
                return TestResult(False, 'Participant {} has no object parented to sims head', participant_sim, tooltip=self.tooltip)
        return TestResult.TRUE

class ConsumableTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject of the test. This is the consumable object.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'is_consumable': Tunable(description='\n            If checked, the subject must be a consumable, if unchecked, the\n            subject must not be a consumable.\n            ', tunable_type=bool, default=True), 'bites_left': TunableTuple(description='\n            A check that tests against the number of bites left before the\n            subject is completely consumed.\n            ', value=Tunable(description='\n                The number of bites to test against.\n                ', tunable_type=int, default=1), operator=TunableOperator(description='\n                The operator to use for the comparison.\n                ', default=sims4.math.Operator.EQUAL))}

    def get_expected_args(self):
        return {'subject': self.subject}

    @cached_test
    def __call__(self, subject=None, target=None):
        subject = next(iter(subject))
        consumable_component = subject.consumable_component
        if consumable_component is None and self.is_consumable:
            return TestResult(False, 'Object {} is not a consumable but is expected to be.', subject, tooltip=self.tooltip)
        if consumable_component is not None and not self.is_consumable:
            return TestResult(False, 'Object {} is a consumable but is expected not to be.', subject, tooltip=self.tooltip)
        bites_left_in_subject = consumable_component.bites_left()
        threshold = sims4.math.Threshold(self.bites_left.value, self.bites_left.operator)
        if not threshold.compare(bites_left_in_subject):
            return TestResult(False, 'Object {} is expected to have {} {} bites left, but actually has {} bites left.', subject, self.bites_left.operator, self.bites_left.value, bites_left_in_subject, tooltip=self.tooltip)
        return TestResult.TRUE

class CanSeeObjectTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):

    def get_expected_args(self):
        return {'sim_info_list': ParticipantType.Actor, 'target_list': ParticipantType.Object}

    @cached_test
    def __call__(self, sim_info_list=None, target_list=None):
        if sim_info_list is None:
            return TestResult(False, 'There are no actors.', tooltip=self.tooltip)
        if target_list is None:
            return TestResult(False, "Target object doesn't exist.", tooltip=self.tooltip)
        for sim_info in sim_info_list:
            sim = sim_info.get_sim_instance()
            if sim is None:
                return TestResult(False, '{} is not instanced..'.format(sim_info), tooltip=self.tooltip)
            for obj in target_list:
                if not sim.can_see(obj):
                    return TestResult(False, "{} can't see {}.".format(sim, obj), tooltip=self.tooltip)
        return TestResult.TRUE

class GameTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The subject of this game test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'is_sim_turn': OptionalTunable(description="\n            Whether it must or must not be the participant's turn in this game.\n            ", tunable=Tunable(tunable_type=bool, default=True)), 'number_of_players': OptionalTunable(description='\n            The number of players required for this interaction to run.\n            ', tunable=TunableInterval(tunable_type=int, default_lower=0, default_upper=0, minimum=0)), 'is_winner': OptionalTunable(description='\n            Whether the participant must be the winner or loser of this game.\n            ', tunable=Tunable(tunable_type=bool, default=True)), 'participant_has_high_score': OptionalTunable(description='\n            If enabled, the participant must be either the member or non-member\n            of the highest score team. If disabled, ignore this state.\n            ', tunable=Tunable(tunable_type=bool, default=True)), 'high_score_comparison': OptionalTunable(description='\n            If enabled, compare the statistic value with game high score.\n            ', tunable=TunableTuple(comparison=TunableOperator(description='\n                    The operator to use for the comparison.\n                    Specifics: Stat Value <Operator> Game High Score.\n                    ', default=sims4.math.Operator.GREATER), stat=TunableReference(description='\n                    The stat we are comparing to high score.\n                    ', manager=services.statistic_manager()))), 'high_score_exist': OptionalTunable(description='\n            If enabled, require the game to persist high score and has\n            high score set. If disabled, ignore this state.\n            ', tunable=Tunable(tunable_type=bool, default=True)), 'can_join': OptionalTunable(description='\n            If enabled, require the current game to be either joinable or non-\n            joinable.  If disabled, ignore joinability.\n            ', tunable=Tunable(tunable_type=bool, default=True)), 'can_join_autonomously_after_user_directed': OptionalTunable(description="\n            If enabled, require the current game to be either autonomously \n            joinable or non-joinable after at least one of the player in the\n            game join by user direction. If disabled, ignore this state.\n            \n            ex. In bowling game, we don't want autonomous Sim to join the game\n            if the last sim that join the game is user directed. In this case,\n            enabled this filter.\n            ", tunable=Tunable(tunable_type=bool, default=True)), 'current_game_rule': OptionalTunable(description='\n            If enabled, require the game currently being played to be the same \n            with this tuned game rule value. The test will fail if no game has \n            been started. If disabled, ignore this state.\n            ', tunable=TunableReference(description='\n                The game rule to be used for checking current game.\n                ', manager=services.get_instance_manager(sims4.resources.Types.GAME_RULESET), class_restrictions=('GameRules',))), 'require_challenge_availability': Tunable(description='\n            If checked, require that:\n             * The participant is currently playing and is a challenger\n             * No challenge is ongoing\n            ', tunable_type=bool, default=False), 'requires_setup': OptionalTunable(description='\n            If enabled, require the game to either be set up or not set up.  If\n            disabled, ignore this state.\n            ', tunable=Tunable(tunable_type=bool, default=True)), 'game_over': OptionalTunable(description='\n            If enabled, require the game to have either ended or not ended.  If\n            disabled, ignore this state. A game is considered to be over if\n            there is either no active game, or if a winning team has been\n            chosen.\n            ', tunable=Tunable(tunable_type=bool, default=True))}

    def get_expected_args(self):
        return {'participants': self.participant, 'actor': ParticipantType.Actor, 'target': ParticipantType.TargetSim, 'objects': ParticipantType.Object, 'context': ParticipantType.InteractionContext}

    @cached_test
    def __call__(self, participants, actor, target, objects, context):
        game = None
        for obj in objects:
            if obj.game_component is not None:
                game = obj.game_component
                target_object = obj
        if game is None:
            sim_infos = actor + target
            for sim_info in sim_infos:
                if sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, 'GameTest: Cannot run game test on uninstantiated sim.', tooltip=self.tooltip)
                sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                for si in sim.si_state:
                    target_group = si.get_participant(ParticipantType.SocialGroup)
                    target_object = target_group.anchor if target_group is not None else None
                    if target_object is not None and target_object.game_component is not None:
                        game = target_object.game_component
                        break
                break
        if game is None:
            return TestResult(False, 'GameTest: Not able to find a valid Game.', tooltip=self.tooltip)
        for participant in participants:
            if not participant.is_sim:
                return TestResult(False, 'GameTest: The participant is not a sim.', tooltip=self.tooltip)
            if participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                return TestResult(False, 'GameTest: The participant is not an instantiated sim.', tooltip=self.tooltip)
            sim = participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if self.current_game_rule is not None:
                if game.current_game is None:
                    return TestResult(False, 'GameTest: Cannot check current game rule because no game has been started.', tooltip=self.tooltip)
                if game.current_game.guid64 != self.current_game_rule.guid64:
                    return TestResult(False, 'GameTest: Current game is not the same with tuned current game rule.', tooltip=self.tooltip)
            if self.is_sim_turn is not None and game.is_sim_turn(sim) != self.is_sim_turn:
                return TestResult(False, 'GameTest: The participant does not fulfill the turn requirement.', tooltip=self.tooltip)
            if self.number_of_players is not None:
                player_num = game.number_of_players
                if not (self.number_of_players.lower_bound <= player_num and player_num <= self.number_of_players.upper_bound):
                    return TestResult(False, 'GameTest: Number of players required to be withing {} and {}, but the actual number of players is {}.', self.number_of_players.lower_bound, self.number_of_players.upper_bound, player_num, tooltip=self.tooltip)
            if self.is_winner is not None:
                if game.winning_team is not None:
                    in_winning_team = sim in game.winning_team.players
                    if self.is_winner != in_winning_team:
                        return TestResult(False, "GameTest: Sim's win status is not correct.", tooltip=self.tooltip)
                else:
                    return TestResult(False, 'GameTest: Game is over and no win status specified for this test.', tooltip=self.tooltip)
            if self.participant_has_high_score is not None:
                if game.high_score is None and game.current_game is None:
                    return TestResult(False, 'GameTest: Cannot test participant high score status because no high score and no game has been started.', tooltip=self.tooltip)
                in_winning_team = True if game.high_score is None else sim.id in game.high_score_sim_ids
                if self.participant_has_high_score != in_winning_team:
                    return TestResult(False, 'GameTest: Participant has high score is not correct.', tooltip=self.tooltip)
            if self.high_score_comparison is not None and game.high_score is not None:
                stat = sim.get_statistic(self.high_score_comparison.stat)
                if stat is None:
                    return TestResult(False, 'GameTest: Failed to find statistic {} in Sim {}.', self.high_score_comparison.stat, sim, tooltip=self.tooltip)
                threshold = sims4.math.Threshold(game.high_score, self.high_score_comparison.comparison)
                if not threshold.compare(stat.get_value()):
                    operator_symbol = Operator.from_function(self.high_score_comparison.comparison).symbol
                    return TestResult(False, 'GameTest: Failed comparison check: Stat Value ({}) {} Game High Score ({}).', stat.get_value(), operator_symbol, game.high_score, tooltip=self.tooltip)
            if self.high_score_exist is not None:
                high_score_exist = False if game.high_score is None else True
                if self.high_score_exist != high_score_exist:
                    return TestResult(False, 'GameTest: Game high score status is not correct.', tooltip=self.tooltip)
            if self.can_join is not None and game.is_joinable(sim) != self.can_join:
                return TestResult(False, "GameTest: Sim's join status is not correct.", tooltip=self.tooltip)
            if self.can_join_autonomously_after_user_directed is not None and game.is_joinable_autonomously_after_user_directed(context) != self.can_join_autonomously_after_user_directed:
                return TestResult(False, "GameTest: Sim's join autonomously status is not correct.", tooltip=self.tooltip)
            if self.require_challenge_availability and game.challenge_sims is not None and sim not in game.challenge_sims:
                return TestResult(False, 'GameTest: Sim is not available as a challenger', tooltip=self.tooltip)
            if self.requires_setup is not None:
                if game.current_game is None:
                    return TestResult(False, 'GameTest: Cannot test setup conditions because no game has been started.', tooltip=self.tooltip)
                if game.requires_setup != self.requires_setup:
                    return TestResult(False, "GameTest: Game's setup requirements do not match this interaction's setup requirements.", tooltip=self.tooltip)
            if self.game_over is not None and game.game_has_ended != self.game_over:
                return TestResult(False, "GameTest: Game's GameOver state does not match this interaction's GameOver state requirements.", tooltip=self.tooltip)
        return TestResult.TRUE

class ObjectOwnershipTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = (TestEvent.ObjectAdd,)

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.is_owner and value.is_not_owner:
            logger.error('Object Ownership: Is Owner and Is Not Owner is set. Test will always fail. Source: {}', source)
        if value.creator and value.test_household_owner:
            logger.error('Object Ownership: Creator and Test Household Owner is set. See comments on Creator. Source: {}', source)

    FACTORY_TUNABLES = {'sim': TunableEnumEntry(description='\n            Presumed Owner.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor, invalid_enums=(ParticipantType.Invalid,)), 'test_object': TunableEnumEntry(description='\n            Object to test ownership of.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object, invalid_enums=(ParticipantType.Invalid,)), 'is_owner': Tunable(description='\n            If checked, the test will only pass if the Sim owns the object.\n            ', tunable_type=bool, default=True), 'is_not_owner': Tunable(description='\n            If checked, the test will only pass if the Sim does not own the\n            object.\n            ', tunable_type=bool, default=False), 'creator': OptionalTunable(description='\n            If disabled, the test disregards who created the object.\n            \n            If this is enabled, Test Household Owner must be unchecked, as\n            crafters are on a per-Sim basis and not a per-household basis.\n            ', disabled_name='ignore', enabled_name='check_creator', tunable=Tunable(description='\n                Test whether or not the specified Sim is the creator of the object.\n                \n                If checked, pass if Sim is creator. If unchecked, fail if Sim is creator.\n                ', tunable_type=bool, default=True)), 'test_household_owner': Tunable(description="\n            If checked, the test considers a Sim as owning the object if the\n            Sim's household owns it. If unchecked, the Sim must individually\n            own the object. That is, the object must have an Ownable Component\n            and the Sim is set as the owner.\n            ", tunable_type=bool, default=True), 'consider_renter_as_household_owner': Tunable(description='\n            If checked, unowned objects are considered owned by the renter of\n            the current lot. If unchecked, the objects remain as considered\n            unowned.\n            \n            If this is checked, Test Household Owner must be checked, as this\n            option operates at the household level and not on a Sim level.\n            ', tunable_type=bool, default=True), 'must_be_owned': Tunable(description='\n            If checked, the test will only pass if someone owns this object.\n            If unchecked, the test will only pass if nobody owns this object.\n\n            This tunable is only considered if Is Owner and Is Not Owner are\n            not checked.\n            ', tunable_type=bool, default=True), 'verify_tunable_callback': _verify_tunable_callback}

    def get_expected_args(self):
        return {'test_targets': self.sim, 'objs': self.test_object}

    @cached_test
    def __call__(self, test_targets, objs):
        current_zone_id = services.current_zone_id()
        for obj in objs:
            target_obj = obj
            for target in test_targets:
                target_sim = target
                if self.test_household_owner:
                    owner_id = target_obj.get_household_owner_id()
                    sim_id = target_sim.household.id
                    if self.consider_renter_as_household_owner and (owner_id or target_sim.is_renting_zone(current_zone_id)):
                        owner_id = sim_id
                else:
                    owner_id = target_obj.get_sim_owner_id()
                    sim_id = target_sim.sim_id
                    if self.creator is not None:
                        is_creator = obj.crafting_component is not None and obj.get_crafting_process().crafter_sim_id == sim_id
                        if self.creator != is_creator:
                            return TestResult(False, "Sim didn't meet creator requirement. Required creator: {}", self.creator, tooltip=self.tooltip)
                if self.is_owner:
                    if sim_id != owner_id:
                        return TestResult(False, 'Sim does not own this object.', tooltip=self.tooltip)
                elif self.is_not_owner:
                    if sim_id == owner_id:
                        return TestResult(False, 'Sim owns this object.', tooltip=self.tooltip)
                elif self.must_be_owned:
                    if not owner_id:
                        return TestResult(False, 'This object is not owned.', tooltip=self.tooltip)
                        if owner_id:
                            return TestResult(False, 'This object already has an owner.', tooltip=self.tooltip)
                elif owner_id:
                    return TestResult(False, 'This object already has an owner.', tooltip=self.tooltip)
        return TestResult.TRUE
ObjectCriteriaSingleObjectSpecificTest = collections.namedtuple('ObjectCriteriaSingleObjectSpecificTest', ('subject_type', 'target'))
class _RadiusFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'radius_actor': TunableEnumEntry(description='\n            The actor whose position, with the radius, defines the\n            area within which the object is valid.\n            ', tunable_type=ParticipantType, default=ParticipantTypeSingle.Object), 'radius': TunableDistanceSquared(description="\n            The radius, with the radius actor's position, that defines\n            the area within which the object is valid.\n            ", default=5.0)}

    def get_expected_args(self):
        return {'positional_relationship_participants': self.radius_actor}

    def evaluate(self, obj, participants=None):
        if participants is not None:
            for radius_actor_object in participants:
                delta = obj.position - radius_actor_object.position
                if delta.magnitude_squared() > self.radius:
                    return False
        return True

class _TaggedObjectOnSameLevelFactory(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The participant to test against. \n            ', tunable_type=ParticipantType, default=ParticipantTypeSingle.Object), 'tag': TunableTag(description='\n            A single tag to find an object matching to test against the participant. \n            ')}

    def get_expected_args(self):
        return {'positional_relationship_participants': self.subject}

    def evaluate(self, obj, participants=None):
        if participants is None:
            return False
        for participant in participants:
            for tagged_obj in services.object_manager().get_objects_with_tag_gen(self.tag):
                if tagged_obj.level == participant.level:
                    return True
        return False

class ObjectCriteriaTest(AutoFactoryInit, HasTunableSingletonFactory, event_testing.test_base.BaseTest):
    TARGET_OBJECTS = 0
    ALL_OBJECTS = 1

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.desired_state_threshold is not None:
            threshold_value = value.desired_state_threshold.value
            if threshold_value.state is None or not hasattr(threshold_value, 'value'):
                logger.error('invalid state value in desired state threshold for {}: {}', source, tunable_name)

    FACTORY_TUNABLES = {'verify_tunable_callback': _verify_tunable_callback, 'subject_specific_tests': TunableVariant(all_objects=TunableTuple(locked_args={'subject_type': ALL_OBJECTS}, quantity=TunableThreshold(description='\n                        The number of objects that meet the tuned critera needed to pass this\n                        test. quantity is run after a list of matching objects is created\n                        using the tuned criteria.\n                        ', default=sims4.math.Threshold(1, sims4.math.Operator.GREATER_OR_EQUAL.function), value=Tunable(float, 1, description='The value of a threshold.')), total_value=OptionalTunable(TunableThreshold(description='\n                        If set, the total monetary value of all the objects that meet the tuned \n                        criteria needed in order to pass this test. total_value is run after \n                        a list of matching objects is created using the tuned criteria.\n                        '))), single_object=TunableTuple(locked_args={'subject_type': TARGET_OBJECTS}, target=TunableEnumEntry(description='\n                        If set this test will loop through the specified participants and\n                        run the object identity and criteria tests on them instead of all\n                        of the objects on the lot.\n                        ', tunable_type=ParticipantType, default=ParticipantType.Object)), default='all_objects'), 'identity_test': TunableVariant(description='\n            Which test to run on the object in order to determine \n            if it matches or not.\n            ', definition_id=ObjectTypeFactory.TunableFactory(), tags=ObjectTagFactory.TunableFactory(), trending=ObjectTrendingFactory.TunableFactory(), locked_args={'no_identity_test': None}, default='no_identity_test'), 'positional_relationship_test': TunableVariant(description='\n            The type of positional relationship test to run on the object with respect to \n            another object.\n            ', radius_test=_RadiusFactory.TunableFactory(), tagged_object_on_same_level_test=_TaggedObjectOnSameLevelFactory.TunableFactory(), locked_args={'no_positional_relationship_test': None}, default='no_positional_relationship_test'), 'owned': Tunable(description="\n            If checked will test if the object is owned by the active \n            household. If unchecked it doesn't matter who owns the object or\n            if it is owned at all.\n            ", tunable_type=bool, default=True), 'sim_ownership': OptionalTunable(description='\n            If enabled, test whether or not the object is owned by the active \n            Sim.  If checked, test will pass if the Sim owns the object.\n            ', tunable=Tunable(tunable_type=bool, default=True)), 'on_active_lot': Tunable(description="\n            If checked, test whether or not the object is on the active\n            lot. If unchecked the object can be either on the active lot or\n            in the open streets area, we don't really care.\n            ", tunable_type=bool, default=False), 'desired_state_threshold': OptionalTunable(TunableThreshold(description='\n            A state threshold that the object must satisfy for this test to pass', value=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'))), 'test_events': TunableList(description='\n            The list of events that trigger this instance of the tuned test on.\n            \n            If you pick ObjectStateChange, the test will be registered with\n            EventManager for every ObjectStateValue managed by ObjectState\n            controlling the desired_state_threshold. E.g. if the test cares\n            about BrokenState_Broken, we will register tolisten for events for\n            state changes of BrokenState_Broken, BrokenState_Unbroken,\n            BrokenState_Repairing, etc.\n            ', tunable=TunableEnumEntry(tunable_type=ObjectCriteriaTestEvents, default=ObjectCriteriaTestEvents.AllObjectEvents), set_default_as_first_entry=True), 'use_depreciated_values': Tunable(description='\n            If checked, the value consideration for each checked object will at its depreciated amount.\n            This affects the "All Objects" test type, changing the total value considered to be at the\n            non-depreciated amount.\n            ', tunable_type=bool, default=False), 'value': OptionalTunable(description='\n            A threshold test for the monetary value of a single object in order for it\n            to be considered.\n            ', tunable=TunableTuple(threshold=TunableThreshold(), value_to_check=TunableVariant(locked_args={'catalog_value': lambda x: x.catalog_value, 'current_value': lambda x: x.current_value, 'depreciated_value': lambda x: x.depreciated_value}, default='catalog_value'))), 'completed': Tunable(description='\n            If checked, any craftable object (such as a painting) must be finished\n            for it to be considered.\n            ', tunable_type=bool, default=False)}
    __slots__ = ('test_events', 'subject_specific_tests', 'identity_test', 'positional_relationship_test', 'owned', 'sim_ownership', 'on_active_lot', 'desired_state_threshold', 'use_depreciated_values', 'value', 'completed')

    def __init__(self, *args, **kwargs):
        super().__init__(**kwargs)
        test_events = self.test_events
        if test_events[0] == ObjectCriteriaTestEvents.AllObjectEvents:
            self.test_events = (TestEvent.OnExitBuildBuy, TestEvent.ObjectStateChange, TestEvent.ItemCrafted, TestEvent.OnInventoryChanged)

    @property
    def allow_failfast_tests(self):
        return False

    def get_test_events_to_register(self):
        events = tuple(event for event in self.test_events if event != TestEvent.ObjectStateChange)
        return events

    def get_custom_event_registration_keys(self):
        keys = []
        if self.desired_state_threshold is not None:
            for value in self.desired_state_threshold.value.state.values:
                keys.append((TestEvent.ObjectStateChange, value))
        return keys

    def get_expected_args(self):
        expected_args = {}
        if self.positional_relationship_test is not None:
            expected_args.update(self.positional_relationship_test.get_expected_args())
        if self.subject_specific_tests.subject_type == self.TARGET_OBJECTS:
            expected_args['target_objects'] = self.subject_specific_tests.target
        return expected_args

    def object_meets_criteria(self, obj, active_household_id, active_sim_id, current_zone, positional_relationship_participants=None):
        if self.owned and obj.get_household_owner_id() != active_household_id:
            return False
        if self.sim_ownership and obj.get_sim_owner_id() != active_sim_id:
            return False
        if self.on_active_lot and not obj.is_on_active_lot():
            return False
        if self.positional_relationship_test is not None and not self.positional_relationship_test.evaluate(obj, participants=positional_relationship_participants):
            return False
        if self.completed and obj.crafting_component is not None:
            crafting_process = obj.get_crafting_process()
            if not crafting_process.is_complete:
                return False
        if self.desired_state_threshold is not None:
            desired_state = self.desired_state_threshold.value.state
            if not obj.has_state(desired_state):
                return False
            if not self.desired_state_threshold.compare_value(obj.get_state(desired_state)):
                return False
            elif self.value is not None:
                obj_value = self.value.value_to_check(obj)
                if not self.value.threshold.compare(obj_value):
                    return False
        elif self.value is not None:
            obj_value = self.value.value_to_check(obj)
            if not self.value.threshold.compare(obj_value):
                return False
        return True

    def get_total_value_and_number_of_matches(self, active_household_id, active_sim_id, current_zone, objects_to_test, positional_relationship_participants):
        number_of_matches = 0
        total_value = 0
        for obj in objects_to_test:
            if self.object_meets_criteria(obj, active_household_id, active_sim_id, current_zone, positional_relationship_participants):
                number_of_matches += 1
                total_value += obj.depreciated_value if self.use_depreciated_values else obj.catalog_value
        return (total_value, number_of_matches)

    @cached_test
    def __call__(self, target_objects=None, positional_relationship_participants=None):
        active_household_id = services.active_household_id()
        active_sim_id = services.active_sim_info().id if services.active_sim_info() is not None else 0
        current_zone = services.current_zone()
        if target_objects is not None:
            if self.identity_test is None:
                objects_to_test = target_objects
            else:
                objects_to_test = [obj for obj in target_objects if self.identity_test(obj)]
        elif self.identity_test is None:
            objects_to_test = services.object_manager().values()
        else:
            objects_to_test = self.identity_test.get_all_objects(services.object_manager())
        if self.positional_relationship_test is not None:
            positional_relationship_objects = []
            try:
                for positional_relationship_participant in positional_relationship_participants:
                    if positional_relationship_participant is None:
                        logger.warn('Positional Relationship Test requires non-empty participant Values. {} is None. ', self.positional_relationship_participant, owner='shipark')
                    else:
                        sim_info = sims.sim_info.SimInfo
                        if isinstance(positional_relationship_participant, sim_info):
                            positional_relationship_object = positional_relationship_participant.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                            positional_relationship_objects.append(positional_relationship_object)
                        else:
                            positional_relationship_objects.append(positional_relationship_participant)
            except TypeError:
                logger.error('{} is an invalid participant for the Positional Relationship Test.', self.positional_relationship_participant, owner='shipark')
        else:
            positional_relationship_objects = positional_relationship_participants
        (total_value, number_of_matches) = self.get_total_value_and_number_of_matches(active_household_id, active_sim_id, current_zone, objects_to_test, positional_relationship_objects)
        if self.subject_specific_tests.subject_type == self.ALL_OBJECTS:
            if not self.subject_specific_tests.quantity.compare(number_of_matches):
                return TestResultNumeric(False, 'There are {} matches when {} matches are needed for the object criteria tuning', number_of_matches, self.subject_specific_tests.quantity.value, current_value=number_of_matches, goal_value=self.subject_specific_tests.quantity.value, is_money=False, tooltip=self.tooltip)
            if self.subject_specific_tests.total_value is not None and not self.subject_specific_tests.total_value.compare(total_value):
                return TestResultNumeric(False, 'The total value is {} when it needs to be {} for the object criteria tuning', total_value, self.subject_specific_tests.total_value.value, current_value=total_value, goal_value=self.subject_specific_tests.total_value.value, is_money=True, tooltip=self.tooltip)
        elif target_objects and number_of_matches != len(target_objects):
            return TestResult(False, "All of the specified targets don't meet the object criteria tuning.", tooltip=self.tooltip)
        return TestResult.TRUE

    def goal_value(self):
        if self.subject_specific_tests.total_value is not None:
            return self.subject_specific_tests.total_value.value
        return self.subject_specific_tests.quantity.value

    @property
    def is_goal_value_money(self):
        return self.subject_specific_tests.total_value is not None

class SituationObjectComparisonTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'identity_test': TunableVariant(description='\n            Which test to run on the object in order to determine \n            if it matches or not.\n            ', definition_id=ObjectTypeFactory.TunableFactory(), tags=ObjectTagFactory.TunableFactory(), locked_args={'no_identity_test': None}, default='no_identity_test'), 'owned': Tunable(description="\n            If checked will test if the object is owned by the active \n            household. If unchecked it doesn't matter who owns the object or\n            if it is owned at all.\n            ", tunable_type=bool, default=True), 'on_active_lot': Tunable(description="\n            If checked, test whether or not the object is on the active\n            lot. If unchecked the object can be either on the active lot or\n            in the open streets area, we don't really care.\n            ", tunable_type=bool, default=False), 'situation': TunableReference(description='\n            The situation that we want to check for the running number of.\n            ', manager=services.situation_manager()), 'comparison': TunableOperator(description='\n            The operator that we will use to compare the number of situations\n            running to the number of objects that pass our criteria.\n            Specifics: Situation Count <Operator> Object Count\n            ', default=sims4.math.Operator.GREATER_OR_EQUAL)}

    def get_expected_args(self):
        return {}

    def object_meets_criteria(self, obj, active_household_id, current_zone):
        if self.owned and obj.get_household_owner_id() != active_household_id:
            return False
        elif self.on_active_lot and not obj.is_on_active_lot():
            return False
        return True

    @cached_test
    def __call__(self):
        object_count = 0
        active_household_id = services.active_household_id()
        current_zone = services.current_zone()
        for obj in services.object_manager().values():
            if not self.identity_test is None:
                pass
            if self.object_meets_criteria(obj, active_household_id, current_zone):
                object_count += 1
        situation_count = len(services.get_zone_situation_manager().get_situations_by_type(self.situation))
        threshold = sims4.math.Threshold(object_count, self.comparison)
        if not threshold.compare(situation_count):
            operator_symbol = Operator.from_function(self.comparison).symbol
            return TestResult(False, 'Failed Situation Object Comparison Check: Situations ({}) {} Objects ({})', situation_count, operator_symbol, object_count, tooltip=self.tooltip)
        return TestResult.TRUE

class ObjectRoutableSurfaceTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'sims': TunableEnumEntry(description='\n            The Sim we are going to check being on an object.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor, invalid_enums=(ParticipantTypeSingleSim.Invalid,)), 'identity_test': TunableVariant(description='\n            Which test to run on the object in order to determine \n            if it matches or not.\n            ', definition_id=ObjectTypeFactory.TunableFactory(), tags=ObjectTagFactory.TunableFactory(), locked_args={'no_identity_test': None}, default='no_identity_test')}
    BOUNDS_RADIUS = 0.1
    QUADTREE_FILTER = 32

    def get_expected_args(self):
        return {'sims': self.sims}

    @cached_test
    def __call__(self, sims=tuple()):
        object_manager = services.object_manager()
        zone = services.current_zone()
        quadtree = zone.sim_quadtree
        for sim_info in sims:
            sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            position = sim.position
            if sim.routing_surface.type != routing.SurfaceType.SURFACETYPE_OBJECT:
                return TestResult(False, 'Sim {} is not routing on an object.', sim, tooltip=self.tooltip)
            surface_id = routing.SurfaceIdentifier(sim.routing_surface.primary_id, sim.routing_surface.secondary_id, routing.SurfaceType.SURFACETYPE_WORLD)
            bounds = sims4.geometry.QtCircle(sims4.math.Vector2(position.x, position.z), ObjectRoutableSurfaceTest.BOUNDS_RADIUS)
            nearby_surfaces = quadtree.query(bounds=bounds, surface_id=surface_id, filter=ObjectRoutableSurfaceTest.QUADTREE_FILTER)
            for surface_info in nearby_surfaces:
                obj_id = surface_info[0][2]
                obj = object_manager.get(obj_id)
                if obj is None:
                    pass
                elif self.identity_test is None or self.identity_test(obj):
                    break
            return TestResult(False, 'Failed to find surface that matched object criteria for Sim {}', sim, tooltip=self.tooltip)
        return TestResult.TRUE

class DefinitionIdFilter(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'definition': TunableReference(description='\n            The object must have this definition.\n            ', manager=services.definition_manager())}

    def __call__(self, other_definition):
        if self.definition.id != other_definition.id:
            return TestResult(False, 'Definition ids do not match. Testing for {} against {}.', self.definition, other_definition)
        return TestResult.TRUE

class SoundMatchesStoredAudioComponentTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'sound': TunableResourceKey(description='\n            The propx to compare. \n            ', resource_types=(Types.PROPX,)), 'participant': TunableEnumEntry(description='\n            The participant of the interaction whose stored audio component\n            will be compared against the sound. \n            ', tunable_type=ParticipantType, default=ParticipantType.Object)}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets):
        for target in test_targets:
            stored_audio_component = target.get_component(STORED_AUDIO_COMPONENT)
            if stored_audio_component is None:
                return TestResult(False, 'Test participant does not have a stored audio component enabled.', tooltip=self.tooltip)
            if stored_audio_component.sound != self.sound:
                snippet = stored_audio_component.music_track_snippet
                if not snippet is None:
                    if snippet.fixed_length_audio != self.sound and snippet.looping_audio != self.sound:
                        return TestResult(False, "The specified sound does not match any sound stored in the Participant's StoredAudioComponent.", tooltip=self.tooltip)
                return TestResult(False, "The specified sound does not match any sound stored in the Participant's StoredAudioComponent.", tooltip=self.tooltip)
        return TestResult.TRUE
