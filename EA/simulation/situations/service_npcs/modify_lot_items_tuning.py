from collections import defaultdictfrom event_testing.resolver import SingleObjectResolver, GlobalResolverfrom event_testing.statistic_tests import StatThresholdTestfrom event_testing.tests import CompoundTestListfrom interactions import ParticipantTypefrom objects.components.inventory_elements import InventoryTransferFakePerform, DeliverBillFakePerformfrom objects.components.state import TunableStateValueReferencefrom objects.components.types import VEHICLE_COMPONENTfrom sims4.tuning.tunable import HasTunableFactory, TunableList, TunableTuple, AutoFactoryInit, TunableVariant, TunableSingletonFactory, TunableSimMinute, HasTunableSingletonFactoryfrom zone_tests import ZoneTestimport event_testing.resultsimport event_testing.state_testsimport event_testing.test_baseimport event_testing.test_eventsimport event_testing.testsimport objects.object_testsimport seasonsimport servicesimport world.world_tests
class TimeElapsedZoneTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'minutes_passed': TunableSimMinute(description='\n            This test will pass when the minutes passed is greater than the\n            number minutes since last loading into zone.\n            ', default=720, minimum=1)}

    def get_expected_args(self):
        return {}

    @event_testing.test_events.cached_test
    def __call__(self):
        elapsed_time = services.current_zone().time_elapsed_since_last_save().in_minutes()
        if elapsed_time <= self.minutes_passed:
            return event_testing.results.TestResult(False, 'TimeElapsedZoneTest: elapsed time ({}) since last save at this zone is not greater than {}', elapsed_time, self.minutes_passed)
        return event_testing.results.TestResult.TRUE

class TunableObjectModifyGlobalTestVariant(TunableVariant):

    def __init__(self, additional_tests=None, **kwargs):
        if additional_tests is not None:
            kwargs.update(additional_tests)
        super().__init__(season=seasons.season_tests.SeasonTest.TunableFactory(locked_args={'tooltip': None}), elapsed_time=TimeElapsedZoneTest.TunableFactory(locked_args={'tooltip': None}), zone=ZoneTest.TunableFactory(locked_args={'tooltip': None}), **kwargs)

class TunableObjectModifyGlobalTestList(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, additional_tests=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the test.'
        super().__init__(description=description, tunable=TunableObjectModifyGlobalTestVariant(additional_tests=additional_tests), **kwargs)

class TunableObjectModifyTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', test_excluded=(), additional_tests=None, **kwargs):
        if additional_tests is not None:
            kwargs.update(additional_tests)
        super().__init__(description=description, state=event_testing.state_tests.TunableStateTest(locked_args={'who': ParticipantType.Object, 'tooltip': None}), object_definition=TunableObjectMatchesDefinitionOrTagTest(), inventory=objects.object_tests.InventoryTest.TunableFactory(locked_args={'tooltip': None}), custom_name=objects.object_tests.CustomNameTest.TunableFactory(locked_args={'tooltip': None}), consumable_test=objects.object_tests.ConsumableTest.TunableFactory(locked_args={'tooltip': None}), existence=objects.object_tests.ExistenceTest.TunableFactory(locked_args={'tooltip': None, 'require_instantiated': False}), location=world.world_tests.LocationTest.TunableFactory(locked_args={'tooltip': None, 'subject': ParticipantType.Object}), season=seasons.season_tests.SeasonTest.TunableFactory(locked_args={'tooltip': None}), **kwargs)

class TunableObjectModifyTestSet(event_testing.tests.CompoundTestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.CompoundTestList()

    def __init__(self, description=None, additional_tests=None, **kwargs):
        super().__init__(description=description, tunable=TunableList(TunableObjectModifyTestVariant(additional_tests=additional_tests), description='A list of tests.  All of these must pass for the group to pass.'), **kwargs)

class ObjectMatchesDefinitionOrTagTest(event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'description': 'Check to see if the specified object matches either a static definition or a set of tags', 'item': TunableVariant(actual_item=objects.object_tests.CraftActualItemFactory(), tagged_item=objects.object_tests.CraftTaggedItemFactory(), default='tagged_item', description='Whether to test for a specific item or item that has a set of tags')}

    def __init__(self, item, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    def get_expected_args(self):
        return {'objects': ParticipantType.Object}

    def __call__(self, objects=None):
        obj = next(iter(objects))
        match = self.item(obj, None)
        if not match:
            return event_testing.results.TestResult(False, 'ObjectMatchesDefinitionOrTagTest: Object did not match specified checks.')
        return event_testing.results.TestResult.TRUE
TunableObjectMatchesDefinitionOrTagTest = TunableSingletonFactory.create_auto_factory(ObjectMatchesDefinitionOrTagTest)
class ModifyAllLotItems(HasTunableFactory, AutoFactoryInit):
    DESTROY_OBJECT = 0
    SET_STATE = 1
    INVENTORY_TRANSFER = 2
    DELIVER_BILLS = 3
    SET_ON_FIRE = 4
    CLEANUP_VEHICLE = 5
    FACTORY_TUNABLES = {'description': '\n        Tune modifications to apply to all objects on a lot.\n        Can do state changes, destroy certain items, etc.\n        \n        EX: for auto cleaning, tune to have objects with Dirtiness state that\n        equals dirty to be set to the clean state and tune to have dirty dishes\n        and spoiled food to be deleted\n        ', 'modifications': TunableList(description="\n            A list of where the elements define how to modify objects on the\n            lot. Each entry is a triplet of an object modification action\n            (currently either destroy the object or set its state), a list of\n            tests to run on the object to determine if we should actually apply\n            the modification, and a priority in case some modifications should\n            take precedence over other ones when both of their tests pass.\n            \n            EX: test list: object's dirtiness state != dirtiness clean\n            action: set state to Dirtiness_clean\n            \n            So dirty objects will become clean\n            ", tunable=TunableTuple(action=TunableVariant(set_state=TunableTuple(action_value=TunableStateValueReference(description='An object state to set the object to', pack_safe=True), locked_args={'action_type': SET_STATE}), destroy_object=TunableTuple(locked_args={'action_type': DESTROY_OBJECT}), inventory_transfer=TunableTuple(action_value=InventoryTransferFakePerform.TunableFactory(), locked_args={'action_type': INVENTORY_TRANSFER}), deliver_bills=TunableTuple(action_value=DeliverBillFakePerform.TunableFactory(), locked_args={'action_type': DELIVER_BILLS}), set_on_fire=TunableTuple(locked_args={'action_type': SET_ON_FIRE}), cleanup_vehicle=TunableTuple(description='\n                        Cleanup vehicles that are left around.\n                        ', locked_args={'action_type': CLEANUP_VEHICLE})), global_tests=TunableObjectModifyGlobalTestList(description="\n                    Non object-related tests that gate this modification from occurring.  Use this for any global\n                    tests that don't require the object, such as zone/location/time-elapsed tests.  These tests\n                    will run only ONCE for this action, unlike 'Tests', which runs PER OBJECT. \n                    "), tests=TunableObjectModifyTestSet(description='\n                    All least one subtest group (AKA one list item) must pass\n                    within this list before the action associated with this\n                    tuning will be run.\n                    ', additional_tests={'elapsed_time': TimeElapsedZoneTest.TunableFactory(locked_args={'tooltip': None}), 'statistic': StatThresholdTest.TunableFactory(locked_args={'tooltip': None})})))}

    def modify_objects(self, object_criteria=None):
        objects_to_destroy = []
        num_modified = 0
        modifications = defaultdict(CompoundTestList)
        for mod in self.modifications:
            if mod.global_tests and not mod.global_tests.run_tests(GlobalResolver()):
                pass
            else:
                modifications[mod.action].extend(mod.tests)
        all_objects = list(services.object_manager().values())
        for obj in all_objects:
            if obj.is_sim:
                pass
            elif object_criteria is not None and not object_criteria(obj):
                pass
            else:
                resolver = SingleObjectResolver(obj)
                modified = False
                for (action, tests) in modifications.items():
                    if not tests.run_tests(resolver):
                        pass
                    else:
                        modified = True
                        action_type = action.action_type
                        if action_type == ModifyAllLotItems.DESTROY_OBJECT:
                            objects_to_destroy.append(obj)
                            break
                        elif action_type == ModifyAllLotItems.SET_STATE:
                            new_state_value = action.action_value
                            if obj.state_component and obj.has_state(new_state_value.state):
                                obj.set_state(new_state_value.state, new_state_value, immediate=True)
                                if action_type in (ModifyAllLotItems.INVENTORY_TRANSFER, ModifyAllLotItems.DELIVER_BILLS):
                                    element = action.action_value()
                                    element._do_behavior()
                                elif action_type == ModifyAllLotItems.SET_ON_FIRE:
                                    fire_service = services.get_fire_service()
                                    fire_service.spawn_fire_at_object(obj)
                                elif action_type == ModifyAllLotItems.CLEANUP_VEHICLE:
                                    if self._should_cleanup_vehicle(obj):
                                        objects_to_destroy.append(obj)
                                        raise NotImplementedError
                                else:
                                    raise NotImplementedError
                        elif action_type in (ModifyAllLotItems.INVENTORY_TRANSFER, ModifyAllLotItems.DELIVER_BILLS):
                            element = action.action_value()
                            element._do_behavior()
                        elif action_type == ModifyAllLotItems.SET_ON_FIRE:
                            fire_service = services.get_fire_service()
                            fire_service.spawn_fire_at_object(obj)
                        elif action_type == ModifyAllLotItems.CLEANUP_VEHICLE:
                            if self._should_cleanup_vehicle(obj):
                                objects_to_destroy.append(obj)
                                raise NotImplementedError
                        else:
                            raise NotImplementedError
                if modified:
                    num_modified += 1
        for obj in objects_to_destroy:
            obj.destroy(source=self, cause='Destruction requested by modify lot tuning')
        objects_to_destroy = None
        return num_modified

    def _should_cleanup_vehicle(self, obj):
        vehicle_component = obj.get_component(VEHICLE_COMPONENT)
        if vehicle_component is None:
            return False
        household_owner_id = obj.get_household_owner_id()
        if household_owner_id is not None and household_owner_id != 0:
            return False
        elif obj.interaction_refs:
            return False
        return True
