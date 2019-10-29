from collections import Counterimport collectionsfrom event_testing.test_constants import SIM_INSTANCE, TARGET_SIM_ID, FROM_EVENT_DATA, FROM_DATA_OBJECT, OBJECTIVE_GUID64from event_testing.test_events import TestEventfrom sims4.callback_utils import CallbackEventfrom sims4.service_manager import Servicefrom singletons import SingletonTypeimport cachesimport event_testing.resolverimport servicesimport sims4.loglogger = sims4.log.Logger('EventManager')
class DataStoreEventMap(SingletonType, dict):
    pass
with sims4.reload.protected(globals()):
    data_store_event_test_event_callback_map = DataStoreEventMap()
class DataMapHandler:

    def __init__(self, event_enum):
        self.event_enum = event_enum

    def __call__(self, func):
        callbacks = data_store_event_test_event_callback_map.get(self.event_enum)
        if callbacks is None:
            data_store_event_test_event_callback_map[self.event_enum] = [func.__name__]
        else:
            callbacks.append(func.__name__)
        return func

class EventManagerService(Service):

    def __init__(self):
        self._test_event_callback_map = collections.defaultdict(set)
        self._handlers_to_unregister_post_load = set()
        self._enabled = False

    def start(self):
        self._enabled = True

    def register_events_for_objectives(self):
        for aspiration in services.get_instance_manager(sims4.resources.Types.ASPIRATION).types.values():
            if not aspiration.do_not_register_events_on_load:
                aspiration.register_callbacks()
        for achievement in services.get_instance_manager(sims4.resources.Types.ACHIEVEMENT).types.values():
            achievement.register_callbacks()
        for household_milestone in services.get_instance_manager(sims4.resources.Types.HOUSEHOLD_MILESTONE).types.values():
            household_milestone.register_callbacks()

    def register_events_for_update(self):
        for aspiration in services.get_instance_manager(sims4.resources.Types.ASPIRATION).types.values():
            if aspiration.update_on_load:
                self.register_single_event(aspiration, TestEvent.UpdateObjectiveData)
                self._handlers_to_unregister_post_load.add(aspiration)
        for achievement in services.get_instance_manager(sims4.resources.Types.ACHIEVEMENT).types.values():
            self.register_single_event(achievement, TestEvent.UpdateObjectiveData)
            self._handlers_to_unregister_post_load.add(achievement)
        for household_milestone in services.get_instance_manager(sims4.resources.Types.HOUSEHOLD_MILESTONE).types.values():
            self.register_single_event(household_milestone, TestEvent.UpdateObjectiveData)
            self._handlers_to_unregister_post_load.add(household_milestone)

    def on_zone_unload(self):
        self._test_event_callback_map.clear()

    def disable_on_teardown(self):
        self._enabled = False

    def enable_event_manager(self):
        self._enabled = True

    def stop(self):
        self._test_event_callback_map = None
        self._handlers_to_unregister_post_load = None

    def _is_valid_handler(self, handler, event_types):
        if hasattr(handler, 'handle_event'):
            return True
        logger.error('Cannot register {} due to absence of expected callback method.  Registered event_types: {}.', handler, event_types, owner='manus')
        return False

    def register_tests(self, tuning_class_instance, tests):
        for test in tests:
            test_events = test.get_test_events_to_register()
            if test_events:
                self.register(tuning_class_instance, test_events)
            custom_keys = test.get_custom_event_registration_keys()
            for (test_event, custom_key) in custom_keys:
                self.register_with_custom_key(tuning_class_instance, test_event, custom_key)

    def unregister_tests(self, tuning_class_instance, tests):
        for test in tests:
            test_events = test.get_test_events_to_register()
            if test_events:
                self.unregister(tuning_class_instance, test_events)
            custom_keys = test.get_custom_event_registration_keys()
            for (test_event, custom_key) in custom_keys:
                self.unregister_with_custom_key(tuning_class_instance, test_event, custom_key)

    def register_single_event(self, handler, event_type):
        logger.assert_raise(self._enabled, 'Attempting to register event:{} \n            with handler:{} when the EventManagerService is disabled.', str(event_type), str(handler), owner='sscholl')
        self.register(handler, (event_type,))

    def register(self, handler, event_types):
        logger.assert_raise(self._enabled, 'Attempting to register events:{} \n            with handler:{} when the EventManagerService is disabled.', str(event_types), str(handler), owner='sscholl')
        if self._is_valid_handler(handler, event_types):
            for event in event_types:
                key = (event, None)
                self._test_event_callback_map[key].add(handler)

    def unregister_single_event(self, handler, event_type):
        self.unregister(handler, (event_type,))

    def unregister(self, handler, event_types):
        for event in event_types:
            key = (event, None)
            if handler in self._test_event_callback_map[key]:
                self._test_event_callback_map[key].remove(handler)

    def register_with_custom_key(self, handler, event_type, custom_key):
        if self._is_valid_handler(handler, (event_type,)):
            key = (event_type, custom_key)
            self._test_event_callback_map[key].add(handler)

    def unregister_with_custom_key(self, handler, event_type, custom_key):
        key = (event_type, custom_key)
        self._test_event_callback_map[key].discard(handler)

    def process_test_events_for_objective_updates(self, sim_info, init=True):
        if sim_info is None:
            return
        self._process_test_event(sim_info, TestEvent.UpdateObjectiveData, init=init)

    def unregister_unused_handlers(self):
        for handler in self._handlers_to_unregister_post_load:
            self.unregister_single_event(handler, TestEvent.UpdateObjectiveData)
        self._handlers_to_unregister_post_load = set()

    def process_event(self, event_type, sim_info=None, **kwargs):
        if not self._enabled:
            return
        caches.clear_all_caches()
        if sim_info is not None:
            callbacks = data_store_event_test_event_callback_map.get(event_type)
            if callbacks is not None:
                self._process_data_map_for_aspiration(sim_info, event_type, callbacks, **kwargs)
                self._process_data_map_for_achievement(sim_info, event_type, callbacks, **kwargs)
        self._process_test_event(sim_info, event_type, **kwargs)

    def process_events_for_household(self, event_type, household, exclude_sim=None, **kwargs):
        if not self._enabled:
            return
        if household is None:
            household = services.owning_household_of_active_lot()
        if household is None:
            return
        caches.clear_all_caches()
        with sims4.callback_utils.invoke_enter_exit_callbacks(CallbackEvent.ENTER_CONTENT_SET_GEN_OR_PROCESS_HOUSEHOLD_EVENTS, CallbackEvent.EXIT_CONTENT_SET_GEN_OR_PROCESS_HOUSEHOLD_EVENTS):
            callbacks = data_store_event_test_event_callback_map.get(event_type)
            has_not_triggered_achievment_data_object = True
            for sim_info in household._sim_infos:
                if sim_info == exclude_sim:
                    pass
                else:
                    if callbacks is not None:
                        self._process_data_map_for_aspiration(sim_info, event_type, callbacks, **kwargs)
                    if has_not_triggered_achievment_data_object:
                        if callbacks is not None:
                            self._process_data_map_for_achievement(sim_info, event_type, callbacks, **kwargs)
                        has_not_triggered_achievment_data_object = False
                    self._process_test_event(sim_info, event_type, **kwargs)

    def _process_data_map_for_aspiration(self, sim_info, event_type, callbacks, **kwargs):
        if sim_info.aspiration_tracker is None:
            return
        data_object = sim_info.aspiration_tracker.data_object
        for function_name in callbacks:
            aspiration_function = getattr(data_object, function_name)
            aspiration_function(**kwargs)

    def _process_data_map_for_achievement(self, sim_info, event_type, callbacks, **kwargs):
        if not sim_info.is_selectable:
            return
        data_object = sim_info.account.achievement_tracker.data_object
        for function_name in callbacks:
            achievement_function = getattr(data_object, function_name)
            achievement_function(**kwargs)

    def _update_call_counter(self, key):
        pass

    def _process_test_event(self, sim_info, event_type, custom_keys=tuple(), **kwargs):
        original_handlers = set()
        for custom_key in custom_keys:
            key = (event_type, custom_key)
            self._update_call_counter(key)
            handlers = self._test_event_callback_map.get(key)
            if handlers:
                original_handlers.update(handlers)
        key = (event_type, None)
        self._update_call_counter(key)
        handlers = self._test_event_callback_map.get(key)
        if handlers:
            original_handlers.update(handlers)
        if not original_handlers:
            return
        resolver = event_testing.resolver.DataResolver(sim_info, event_kwargs=kwargs)
        tests_for_event = tuple(original_handlers)
        for test in tests_for_event:
            try:
                if test in original_handlers:
                    test.handle_event(sim_info, event_type, resolver)
            except Exception as e:
                logger.exception('Exception raised while trying to run a test event in test_events.py:', exc=e)
