import collectionsimport mathfrom audio.primitive import TunablePlayAudiofrom event_testing.resolver import SingleObjectResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom objects.components.state import TunableStateValueReferencefrom objects.components.types import VEHICLE_COMPONENTfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import TunableMapping, TunableLotDescription, TunableRegionDescription, HasTunableReference, TunableWorldDescription, TunableReference, TunableList, TunableFactory, TunableTuple, TunableVariant, Tunable, OptionalTunablefrom situations.ambient.walkby_tuning import SchedulingWalkbyDirectorimport event_testing.state_testsimport objects.object_testsimport servicesimport sims4.logimport situations.ambient.walkby_tuninglogger = sims4.log.Logger('LotTuning')
class LotTuning(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.lot_tuning_manager()):
    INSTANCE_TUNABLES = {'walkby': situations.ambient.walkby_tuning.WalkbyTuning.TunableReference(allow_none=True), 'walkby_schedule': SchedulingWalkbyDirector.TunableReference(allow_none=True), 'audio_sting': OptionalTunable(description='\n                If enabled then the specified audio sting will play at the end\n                of the camera lerp when the lot is loaded.\n                ', tunable=TunablePlayAudio(description='\n                    The sound to play at the end of the camera lerp when the\n                    lot is loaded.\n                    ')), 'track_premade_status': Tunable(description="\n            If enabled, the lot will be flagged as no longer premade when the\n            player enters buildbuy on the lot or drops items/lots/rooms from\n            the gallery. Otherwise, the lot is still considered premade.\n            If disabled, the game won't care if this lot is premade or not.\n            \n            For example, the retail lots that were shipped with EP01 will track\n            the premade status so we know if objects should automatically be\n            set for sale.\n            ", tunable_type=bool, default=False)}

class LotTuningMaps:
    LOT_TO_LOTTUNING_MAP = TunableMapping(description="\n            Mapping of Lot Description ID to lot tuning. This is a reference to \n            a specific lot in one of our regions. e.g. Goth's mansion lot.\n            ", key_name='Lot Description ID', key_type=TunableLotDescription(pack_safe=True), value_name='Lot Tuning', value_type=LotTuning.TunablePackSafeReference())
    STREET_TO_LOTTUNING_MAP = TunableMapping(description='\n            Mapping of Street Description ID to lot tuning. Street and world\n            are analogous terms. e.g. suburbs street in Garden District.\n            \n            This represents the tuning for all lots within this street that does\n            not have a specific LotTuning specified for itself in the \n            LOT_TO_LOTTUNING_MAP.\n            ', key_name='Street Description ID', key_type=TunableWorldDescription(pack_safe=True), value_name='Lot Tuning', value_type=LotTuning.TunablePackSafeReference())
    REGION_TO_LOTTUNING_MAP = TunableMapping(description='\n            Mapping of Region Description ID to spawner tuning. Region and \n            neighborhood are analogous terms. e.g. Garden District.\n            \n            This represents the tuning for all lots in the region that does\n            not have a specific LotTuning specified for itself in either the \n            LOT_TO_LOTTUNING_MAP or via STREET_TO_LOTTUNING_MAP.\n            ', key_name='Region Description ID', key_type=TunableRegionDescription(pack_safe=True), value_name='Lot Tuning', value_type=LotTuning.TunablePackSafeReference())

    @classmethod
    def get_lot_tuning(cls):
        current_zone = services.current_zone()
        lot = current_zone.lot
        if lot is None:
            logger.warn('Attempting to get LotTuning when the current zone does not have a lot.', owner='manus')
            return
        (world_description_id, lot_description_id) = services.get_world_and_lot_description_id_from_zone_id(current_zone.id)
        lot_tuning = cls.LOT_TO_LOTTUNING_MAP.get(lot_description_id)
        if lot_tuning is not None:
            return lot_tuning
        lot_tuning = cls.STREET_TO_LOTTUNING_MAP.get(world_description_id, None)
        if lot_tuning is not None:
            return lot_tuning
        neighborhood_id = current_zone.neighborhood_id
        if neighborhood_id == 0:
            logger.warn('Attempting to get LotTuning when the current zone does not have a neighborhood.', owner='manus')
            return
        neighborhood_proto_buff = services.get_persistence_service().get_neighborhood_proto_buff(neighborhood_id)
        region_id = neighborhood_proto_buff.region_id
        lot_tuning = cls.REGION_TO_LOTTUNING_MAP.get(region_id, None)
        return lot_tuning

class AllItems(TunableFactory):

    @staticmethod
    def factory(_):
        return sims4.math.POS_INFINITY

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(description='\n                Process all of the objects on the lot.\n                ')

class StatisticValue(TunableFactory):

    @staticmethod
    def factory(lot, statistic):
        statistic_value = lot.get_stat_value(statistic)
        if statistic_value is None:
            return 0
        return math.floor(statistic_value)

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(statistic=TunableReference(description='\n                The statistic on the lot that will be used to determine the\n                number of objects to process.\n                If the statistic is not found then the number 0 is used instead.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), description='\n                Return the value of a statistic on the lot.  If the statistic\n                is not found then the number 0 is used instead.\n                ')

class StatisticDifference(TunableFactory):

    @staticmethod
    def factory(lot, statistic_1, statistic_2):
        statistic_1_value = lot.get_stat_value(statistic_1)
        if statistic_1_value is None:
            statistic_1_value = 0
        statistic_2_value = lot.get_stat_value(statistic_2)
        if statistic_2_value is None:
            statistic_2_value = 0
        return math.floor(abs(statistic_1_value - statistic_2_value))

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(statistic_1=TunableReference(description='\n                The first statistic that will be used with the second statistic\n                in order to discover the number of objects on the lot to\n                process.\n                \n                If the statistic is not found then the number 0 is use instead.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), statistic_2=TunableReference(description='\n                The second statistic that will be used with the first statistic\n                in order to discover the number of objects on the lot to\n                process.\n                \n                If the statistic is not found then the number 0 is use instead.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), description='\n                Return the difference between two different statistics and use\n                that as the amount of objects to process.\n                If the statistics cannot be found the value 0 is used instead.\n                ')

class SetState(TunableFactory):

    @staticmethod
    def factory(obj, _, state):
        if obj.state_component and obj.has_state(state.state):
            obj.set_state(state.state, state, immediate=True)

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(state=TunableStateValueReference(description='\n                An state that we want to set the object to.\n                '), description='\n                Change the state of an object to the tuned state.\n                ')

class DestroyObject(TunableFactory):

    @staticmethod
    def factory(obj, _):
        GlobalLotTuningAndCleanup.objects_to_destroy.add(obj)

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(description='\n                Destroy the object.\n                ')

class CleanupVehicle(TunableFactory):

    @staticmethod
    def factory(obj, _):
        vehicle_component = obj.get_component(VEHICLE_COMPONENT)
        household_owner_id = obj.get_household_owner_id()
        if vehicle_component is not None and (household_owner_id is None or household_owner_id == 0) and not obj.interaction_refs:
            GlobalLotTuningAndCleanup.objects_to_destroy.add(obj)

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(*args, description="\n            Cleanup a vehicle that isn't being used by destroying it.\n            ", **kwargs)

class ConstantAmount(TunableFactory):

    @staticmethod
    def factory(_, amount):
        return amount

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(amount=Tunable(description='\n                A constant amount to change the statistic by.\n                ', tunable_type=float, default=0.0), description='\n                A constant amount.\n                ')

class StatisticBased(TunableFactory):

    @staticmethod
    def factory(lot, statistic, multiplier):
        statistic_value = lot.get_stat_value(statistic)
        if statistic_value is None:
            return 0
        return statistic_value*multiplier

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(statistic=TunableReference(description="\n                A statistic on the lot who's value will be used as the amount\n                to modify a statistic.\n                If no value is found the number 0 is used.\n                ", manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), multiplier=Tunable(description='\n                A multiplier on the statistic value of the statistic on the lot.\n                ', tunable_type=float, default=1.0), description='\n                An amount that is based on the statistic value of a statistic\n                on the lot.\n                ')

class StatisticChange(TunableFactory):

    @staticmethod
    def factory(obj, lot, statistic, amount):
        obj.add_statistic_component()
        stat_instance = obj.get_stat_instance(statistic)
        if stat_instance is None:
            return
        stat_change = amount(lot)
        stat_instance.add_value(stat_change)

    FACTORY_TYPE = factory

    def __init__(self, *args, **kwargs):
        super().__init__(statistic=TunableReference(description='\n                The statistic to be changed on the object.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), amount=TunableVariant(constant=ConstantAmount(), statistic_based=StatisticBased(), description='\n                The amount to modify the statistic by.\n                '), description='\n                Modify the statistic value of an object.\n                ')

class GlobalLotTuningAndCleanup:
    OBJECT_COUNT_TUNING = TunableMapping(description='\n        Mapping between statistic and a set of tests that are run over the\n        objects on the lot on save.  The value of the statistic is set to the\n        number of objects that pass the tests.\n        ', key_type=TunableReference(description='\n            The statistic on the lot that will be set the value of the number\n            of objects that pass the test set that it is mapped to.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), pack_safe=True), value_type=TunableTestSet(description='\n            Test set that will be run on all objects on the lot to determine\n            what the value of the key statistic should be set to.\n            '))
    SET_STATISTIC_TUNING = TunableList(description='\n        A list of statistics and values that they will be set to on the lot\n        while saving it when the lot was running.\n        \n        These values are set before counting by tests on objects.\n        ', tunable=TunableTuple(statistic=TunableReference(description='\n                The statistic that will have its value set.\n                ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), amount=Tunable(description='\n                The value that the statistic will be set to.\n                ', tunable_type=float, default=0.0)))
    OBJECT_CLEANUP_TUNING = TunableList(description='\n        A list of actions to take when spinning up a zone in order to fix it\n        up based on statistic values that the lot has.\n        ', tunable=TunableTuple(count=TunableVariant(all_items=AllItems(), statistic_value=StatisticValue(), statistic_difference=StatisticDifference(), default='all_items', description='\n                    The maximum number of items that will have the action run\n                    on them. \n                '), possible_actions=TunableList(description='\n                The different possible actions that can be taken on objects on\n                the lot if tests pass.\n                ', tunable=TunableTuple(actions=TunableList(description='\n                        A group of actions to be taken on the object.\n                        ', tunable=TunableVariant(set_state=SetState(), destroy_object=DestroyObject(), statistic_change=StatisticChange(), cleanup_vehicle=CleanupVehicle(), default='set_state', description='\n                                The actual action that will be performed on the\n                                object if test passes.\n                            ')), tests=TunableTestSet(description='\n                        Tests that if they pass the object will be under\n                        consideration for this action being done on them.\n                        ')))))
    objects_to_destroy = None
    _count_tuning_optimizer = None

    @classmethod
    def _get_stat_count_optimizer(cls):
        if cls._count_tuning_optimizer is None:
            cls._count_tuning_optimizer = ObjectCountTuningOptimizer(cls.OBJECT_COUNT_TUNING)
        return cls._count_tuning_optimizer

    @classmethod
    def calculate_object_quantity_statistic_values(cls, lot):
        for set_statatistic in cls.SET_STATISTIC_TUNING:
            lot.set_stat_value(set_statatistic.statistic, set_statatistic.amount)
        new_statistic_values = collections.defaultdict(int)
        stat_counter = cls._get_stat_count_optimizer()
        for obj in services.object_manager().values():
            if obj.is_sim:
                pass
            elif not obj.is_on_active_lot():
                pass
            else:
                stat_counter.increment_statistics(obj, new_statistic_values)
        for (statistic, value) in new_statistic_values.items():
            lot.set_stat_value(statistic, value)

    @classmethod
    def cleanup_objects(cls, lot=None):
        if lot is None:
            logger.error('Lot is None when trying to run lot cleanup.', owner='jjacobson')
            return
        cls.objects_to_destroy = set()
        for cleanup in GlobalLotTuningAndCleanup.OBJECT_CLEANUP_TUNING:
            items_to_cleanup = cleanup.count(lot)
            if items_to_cleanup == 0:
                pass
            else:
                items_cleaned_up = 0
                for obj in services.object_manager().values():
                    if items_cleaned_up >= items_to_cleanup:
                        break
                    if obj.is_sim:
                        pass
                    else:
                        resolver = SingleObjectResolver(obj)
                        run_action = False
                        for possible_action in cleanup.possible_actions:
                            if possible_action.tests.run_tests(resolver):
                                for action in possible_action.actions:
                                    action(obj, lot)
                                    run_action = True
                        if run_action:
                            items_cleaned_up += 1
        for obj in cls.objects_to_destroy:
            obj.destroy(source=lot, cause='Cleaning up the lot')
        cls.objects_to_destroy = None

class ObjectCountTuningOptimizer:

    def __init__(self, tuning):
        self._tag_to_test_mapping = None
        self._state_to_test_mapping = None
        self._relevant_tags = None
        self.analyze_tuning(tuning)

    def analyze_tuning(self, tuning):
        self._tag_to_test_mapping = collections.defaultdict(list)
        self._state_to_test_mapping = collections.defaultdict(list)
        self._relevant_tags = set()
        ObjectCriteriaTest = objects.object_tests.ObjectCriteriaTest
        StateTest = event_testing.state_tests.StateTest
        for (statistic, test_set) in tuning.items():
            for test_list in test_set:
                for test in test_list:
                    if isinstance(test, ObjectCriteriaTest):
                        subject_specific_tests = test.subject_specific_tests
                        if subject_specific_tests.subject_type == ObjectCriteriaTest.ALL_OBJECTS:
                            logger.error("Object count criteria test can not use type 'All Objects'")
                        elif subject_specific_tests.target != ParticipantType.Object:
                            logger.error('Object count criteria test must target ParticipantType.Object, not {}', subject_specific_tests.single_object.target)
                        elif not hasattr(test, 'identity_test'):
                            logger.error('Object count criteria test must have tags')
                        else:
                            identity_test_tags = test.identity_test.tag_set
                            for tag in identity_test_tags:
                                self._tag_to_test_mapping[tag].append((test_set, statistic))
                            self._relevant_tags.update(identity_test_tags)
                            if isinstance(test, StateTest):
                                if test.who != ParticipantType.Object:
                                    logger.error('Object count state test must target ParticipantType.Object, not {}', test.who)
                                elif test.fallback_behavior != StateTest.ALWAYS_FAIL:
                                    logger.error("Object count state test must use 'Always Fail'")
                                else:
                                    state = test.value.state
                                    self._state_to_test_mapping[state].append((test_set, statistic))
                                    logger.error('Object count tuning only supports tag-based object criteria tests and state tests, not {}', test)
                            else:
                                logger.error('Object count tuning only supports tag-based object criteria tests and state tests, not {}', test)
                    elif isinstance(test, StateTest):
                        if test.who != ParticipantType.Object:
                            logger.error('Object count state test must target ParticipantType.Object, not {}', test.who)
                        elif test.fallback_behavior != StateTest.ALWAYS_FAIL:
                            logger.error("Object count state test must use 'Always Fail'")
                        else:
                            state = test.value.state
                            self._state_to_test_mapping[state].append((test_set, statistic))
                            logger.error('Object count tuning only supports tag-based object criteria tests and state tests, not {}', test)
                    else:
                        logger.error('Object count tuning only supports tag-based object criteria tests and state tests, not {}', test)

    def increment_statistics(self, obj, statistic_values):
        tests_to_run = collections.defaultdict(TestSetStats)
        tags = {t for t in self._relevant_tags if obj.definition.has_build_buy_tag(t)}
        if tags:
            for tag in tags:
                test_list = self._tag_to_test_mapping[tag]
                for (test_set, statistic) in test_list:
                    test_set_stats = tests_to_run[id(test_set)]
                    test_set_stats.test_set = test_set
                    test_set_stats.stats.append(statistic)
        state_component = obj.state_component
        if state_component is not None:
            for (state, test_list) in self._state_to_test_mapping.items():
                if state_component.has_state(state):
                    for (test_set, statistic) in test_list:
                        test_set_stats = tests_to_run[id(test_set)]
                        test_set_stats.test_set = test_set
                        test_set_stats.stats.append(statistic)
        if not tests_to_run:
            return
        resolver = SingleObjectResolver(obj)
        incremented_statistics = set()
        for test_set_stats in tests_to_run.values():
            if test_set_stats.test_set.run_tests(resolver):
                for statistic in test_set_stats.stats:
                    if statistic not in incremented_statistics:
                        statistic_values[statistic] += 1
                        incremented_statistics.add(statistic)

class TestSetStats:
    __slots__ = ('test_set', 'stats')

    def __init__(self):
        self.test_set = None
        self.stats = []
