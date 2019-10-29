from autonomy.settings import AutonomyRandomizationfrom date_and_time import TimeSpanfrom event_testing.register_test_event_mixin import RegisterTestEventMixinfrom event_testing.results import TestResultfrom event_testing.test_events import TestEventfrom objects import componentsfrom objects.components.object_claim_component import ObjectClaimComponentfrom objects.system import create_objectfrom sims4.tuning.tunable import TunableReference, TunableSingletonFactory, TunableSet, TunableEnumEntry, TunableList, AutoFactoryInit, HasTunableFactory, TunableMapping, Tunable, OptionalTunable, TunableSimMinutefrom situations.situation import Situationfrom tag import Tagimport alarmsimport autonomy.autonomy_modesimport autonomy.autonomy_requestimport clockimport event_testingimport gsi_handlersimport interactions.contextimport interactions.priorityimport servicesimport sims4.logimport situationslogger = sims4.log.Logger('Situations')
class SituationStateData:

    def __init__(self, uid, state_type, factory=None):
        self._uid = uid
        self._state_type = state_type
        self._factory = factory

    @property
    def uid(self):
        return self._uid

    @property
    def state_type(self):
        return self._state_type

    def construct_state(self):
        if self._factory is not None:
            return self._factory()
        else:
            return self._state_type()

    @classmethod
    def from_auto_factory(cls, uid, auto_factory):
        return SituationStateData(uid, auto_factory.factory, factory=auto_factory)

class SituationComplex(RegisterTestEventMixin, Situation):

    def test_interaction_complete_by_job_holder(self, sim_info, resolver, job_type, test):
        sim = sim_info.get_sim_instance()
        if sim is None:
            return False
        if not self.sim_has_job(sim, job_type):
            return False
        return resolver(test)

    def _choose_role_interaction(self, sim, push_priority=interactions.priority.Priority.High, run_priority=interactions.priority.Priority.High, allow_failed_path_plans=False):
        context = interactions.context.InteractionContext(sim, interactions.context.InteractionSource.AUTONOMY, push_priority, run_priority=run_priority)
        distance_estimation_behavior = autonomy.autonomy_request.AutonomyDistanceEstimationBehavior.FULL
        if allow_failed_path_plans:
            distance_estimation_behavior = autonomy.autonomy_request.AutonomyDistanceEstimationBehavior.ALLOW_UNREACHABLE_LOCATIONS
        autonomy_request = autonomy.autonomy_request.AutonomyRequest(sim, autonomy_mode=autonomy.autonomy_modes.FullAutonomy, skipped_static_commodities=sim.autonomy_component.standard_static_commodity_skip_set, limited_autonomy_allowed=False, context=context, distance_estimation_behavior=distance_estimation_behavior, autonomy_mode_label_override='ChooseRoleInteraction')
        best_interaction = services.autonomy_service().find_best_action(autonomy_request, randomization_override=AutonomyRandomization.DISABLED)
        return best_interaction

    def _destroy(self):
        self._unregister_for_all_test_events()
        super()._destroy()

class _StateAlarm:

    def __init__(self, alarm_handle, should_persist=True):
        self.alarm_handle = alarm_handle
        self.should_persist = should_persist

class SituationState:

    def __init__(self):
        self._active = False
        self.owner = None
        self._registered_test_events = set()
        self._alarms = {}

    def __str__(self):
        return '{}'.format(self.__class__.__name__)

    def on_pre_activate(self, reader=None):
        pass

    def on_activate(self, reader=None):
        self._active = True

    def on_deactivate(self):
        self._unregister_for_all_test_events()
        for state_alarm in self._alarms.values():
            alarms.cancel_alarm(state_alarm.alarm_handle)
        self._alarms.clear()
        self.owner = None
        self._active = False

    def save_state(self, writer):
        for (name, state_alarm) in self._alarms.items():
            if state_alarm.should_persist:
                writer.write_float(name, state_alarm.alarm_handle.get_remaining_time().in_minutes())

    def _change_state(self, new_state):
        self.owner._change_state(new_state)

    def _test_event_register(self, test_event, custom_key=None):
        custom_key_tuple = (test_event, custom_key)
        self._registered_test_events.add(custom_key_tuple)
        services.get_event_manager().register_with_custom_key(self, test_event, custom_key)

    def _test_event_unregister(self, test_event, custom_key=None):
        custom_key_tuple = (test_event, custom_key)
        if custom_key_tuple in self._registered_test_events:
            self._registered_test_events.remove(custom_key_tuple)
            services.get_event_manager().unregister_with_custom_key(self, test_event, custom_key)

    def _unregister_for_all_test_events(self):
        for (event_type, custom_key) in self._registered_test_events:
            services.get_event_manager().unregister_with_custom_key(self, event_type, custom_key)
        self._registered_test_events.clear()

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target):
        pass

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        return (role_state_type, role_affordance_target)

    def _create_or_load_alarm(self, alarm_name, minutes, callback, repeating=False, use_sleep_time=False, should_persist=True, reader=None):
        if should_persist:
            minutes = reader.read_float(alarm_name, minutes)
        alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(minutes), callback, repeating=repeating, use_sleep_time=use_sleep_time)
        self._alarms[alarm_name] = _StateAlarm(alarm_handle, should_persist)

    def _cancel_alarm(self, alarm_name):
        state_alarm = self._alarms.pop(alarm_name, None)
        if state_alarm is None:
            return
        alarms.cancel_alarm(state_alarm.alarm_handle)

    def _get_remaining_alarm_time(self, alarm_name):
        state_alarm = self._alarms.get(alarm_name, None)
        if state_alarm is None:
            return TimeSpan.ZERO
        return state_alarm.alarm_handle.get_remaining_time()

    def allow_join_situation(self):
        return True

class CommonSituationState(SituationState, HasTunableFactory):
    FACTORY_TUNABLES = {'job_and_role_changes': TunableMapping(description='\n                A mapping between situation jobs and role states that defines\n                what role states we want to switch to for sims on which jobs\n                when this situation state is entered.\n                ', key_type=TunableReference(description="\n                    A reference to a SituationJob that we will use to change\n                    sim's role state.\n                    ", manager=services.situation_job_manager()), key_name='Situation Job', value_type=TunableReference(description='\n                    The role state that we will switch sims of the linked job\n                    into.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE)), value_name='Role State'), 'allow_join_situation': Tunable(description='\n                Whether the situation is allowed to join at this state.\n                ', tunable_type=bool, default=True), 'time_out': OptionalTunable(description='\n                How long this state will last before time expired. Please talk to the GPE who implemented the specific\n                situation to see what the state will do on time expired.\n                ', tunable=TunableSimMinute(default=15, minimum=1))}

    def __init__(self, job_and_role_changes, allow_join_situation, time_out):
        super().__init__()
        self._job_and_role_changes = job_and_role_changes
        self._allow_join_situation = allow_join_situation
        self._time_out = time_out
        self._time_out_string = '' if self._time_out is None else '{}_TIMEOUT'.format(self.__class__.__name__)

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._set_job_role_state()
        if self._time_out is not None:
            self._create_or_load_alarm(self._time_out_string, self._time_out, lambda _: self.timer_expired(), should_persist=True)

    def _set_job_role_state(self):
        for (job, role_state) in self._job_and_role_changes.items():
            self.owner._set_job_role_state(job, role_state)

    def get_all_job_and_role_states(self):
        return self._job_and_role_changes.items()

    def allow_join_situation(self):
        return self._allow_join_situation

    def timer_expired(self):
        pass

class InteractionOfInterest(AutoFactoryInit):
    FACTORY_TUNABLES = {'affordances': TunableList(description="\n            The Sim must have started either any affordance in this list or an\n            interaction matching one of the tags in this tunable's Tags\n            field.\n            ", tunable=TunableReference(services.affordance_manager(), pack_safe=True)), 'tags': TunableSet(description='\n            The Sim must have run either an interaction matching one of these\n            Tags or an affordance from the list of Affordances in this\n            tunable.', tunable=TunableEnumEntry(Tag, Tag.INVALID))}
    expected_kwargs = (('interaction', event_testing.test_constants.FROM_EVENT_DATA),)

    def get_expected_args(self):
        return dict(self.expected_kwargs)

    def __call__(self, interaction=None):
        if interaction is None:
            return TestResult(False, 'No affordance to check against {}', self.affordances)
        if self.tags & interaction.get_category_tags():
            return TestResult.TRUE
        if interaction.affordance in self.affordances:
            return TestResult.TRUE
        return TestResult(False, 'Failed affordance check: {} not in {}', interaction.affordance, self.affordances)

    def custom_keys_gen(self):
        for affordance in self.affordances:
            yield affordance
        for tag in self.tags:
            yield tag
TunableInteractionOfInterest = TunableSingletonFactory.create_auto_factory(InteractionOfInterest)
class CommonInteractionCompletedSituationState(CommonSituationState):
    FACTORY_TUNABLES = {'interaction_of_interest': TunableInteractionOfInterest(description='\n                 The interaction that when run will cause GPE defined behavior\n                 to run.\n                 ')}

    def __init__(self, interaction_of_interest, **kwargs):
        super().__init__(**kwargs)
        self._interaction_of_interest = interaction_of_interest

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete and resolver(self._interaction_of_interest) and self._additional_tests(sim_info, event, resolver):
            self._on_interaction_of_interest_complete(sim_info=sim_info, resolver=resolver)

    def _on_interaction_of_interest_complete(self, **kwargs):
        pass

    def _additional_tests(self, sim_info, event, resolver):
        return True

class CommonMultiInteractionCompletedSituationState(CommonSituationState):
    COMPLETED_INTERACTIONS_TOKEN = 'completed_interactions'
    FACTORY_TUNABLES = {'interactions_of_interest': TunableList(description='\n            Groups of tags/interactions which must each (each group) be\n            satisfied before GPE defined behavior is triggered. To satisfy a\n            group, either an interaction which matches a tuned tag must be run\n            or an interaction that matches a tuned affordance must be run. To\n            create an AND condition, use multiple groups.\n            ', tunable=TunableInteractionOfInterest())}

    def __init__(self, interactions_of_interest, **kwargs):
        super().__init__(**kwargs)
        self._interactions_of_interest = interactions_of_interest
        self._completed_interactions = set()

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for interaction_tuning in self._interactions_of_interest:
            if interaction_tuning in self._completed_interactions:
                pass
            else:
                for custom_key in interaction_tuning.custom_keys_gen():
                    self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete:
            for interaction_tuning in self._interactions_of_interest:
                if interaction_tuning in self._completed_interactions:
                    pass
                elif resolver(interaction_tuning) and self._additional_tests(sim_info, event, resolver):
                    self._completed_interactions.add(interaction_tuning)
                    for custom_key in interaction_tuning.custom_keys_gen():
                        self._test_event_unregister(TestEvent.InteractionComplete, custom_key)
                    if len(self._completed_interactions) == len(self._interactions_of_interest):
                        self._on_interactions_completed()

    def _on_interactions_completed(self):
        pass

    def _additional_tests(self, sim_info, event, resolver):
        return True

class CommonInteractionStartedSituationState(CommonSituationState):
    FACTORY_TUNABLES = {'interaction_of_interest': TunableInteractionOfInterest(description='\n                 The interaction that when run will cause GPE defined behavior\n                 to run.\n                 ')}

    def __init__(self, interaction_of_interest, **kwargs):
        super().__init__(**kwargs)
        self._interaction_of_interest = interaction_of_interest

    def on_activate(self, reader=None):
        super().on_activate(reader)
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionStart, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionStart and resolver(self._interaction_of_interest) and self._additional_tests(sim_info, event, resolver):
            self._on_interaction_of_interest_started()

    def _on_interaction_of_interest_started(self):
        pass

    def _additional_tests(self, sim_info, event, resolver):
        return True

class SituationJobAndRoleState:
    FACTORY_TUNABLES = {'situation_job': TunableReference(services.situation_job_manager(), description='A reference to a SituationJob that can be performed at this Situation.'), 'role_state': TunableReference(services.get_instance_manager(sims4.resources.Types.ROLE_STATE), description='A role state the sim assigned to the job will perform')}

    def __init__(self, situation_job, role_state):
        self.job = situation_job
        self.role_state = role_state

    def add_to_situation_jobs(self, situation):
        situation._add_job_type(self.job, self.role_state)
TunableSituationJobAndRoleState = TunableSingletonFactory.create_auto_factory(SituationJobAndRoleState)
class SituationComplexCommon(SituationComplex):
    SITUATION_STATE_GROUP = 'Situation State'
    STATE_ADVANCEMENT_GROUP = 'State Advancement'
    TIMEOUT_GROUP = 'Timeout And Time Jump'
    NOTIFICATION_GROUP = 'Notifications'
    INSTANCE_SUBCLASSES_ONLY = True
    REMOVE_INSTANCE_TUNABLES = ('_default_job',)
    INVALID_STATE_UID = -1
    STATE_ID_KEY = 'state_id'

    def __init__(self, *arg, **kwargs):
        super().__init__(*arg, **kwargs)
        self._cur_state = None

    def _destroy(self):
        if self._cur_state is not None:
            old_state = self._cur_state
            self._cur_state = None
            old_state.on_deactivate()
        super()._destroy()

    @classmethod
    def _state_to_uid(cls, state_to_find):
        return cls._state_type_to_uid(type(state_to_find))

    @classmethod
    def _state_type_to_uid(cls, state_type_to_find):
        for state_data in cls._states():
            if state_type_to_find is state_data.state_type:
                return state_data.uid
        return cls.INVALID_STATE_UID

    @classmethod
    def _uid_to_state_type(cls, uid_to_find):
        for state_data in cls._states():
            if uid_to_find == state_data.uid:
                return state_data.state_type

    @classmethod
    def _uid_to_state_data(cls, uid_to_find):
        for state_data in cls._states():
            if uid_to_find == state_data.uid:
                return state_data

    @classmethod
    def _states(cls):
        raise NotImplementedError

    @classmethod
    def _verify_tuning_callback(cls):
        if cls._resident_job is not None and cls.resident_job() not in cls.get_tuned_jobs():
            logger.error('Resident Job is tuned to {} for Situation {}, but does not exist in the default job and role state tuples.', cls._resident_job, cls.__name__, owner='rmccord')

    @classmethod
    def _tuning_loaded_callback(cls):
        job_and_state = cls._get_tuned_job_and_default_role_state_tuples()
        job_set = set()
        for (job, _) in job_and_state:
            if job in job_set:
                logger.error('Job {} appears more than once in tuning for situation {}', job, cls)
            else:
                job_set.add(job)
        cls._jobs = job_set
        super()._tuning_loaded_callback()

    @classmethod
    def _load_object(cls, reader, token, claim=False):
        if reader is None:
            return
        obj_id = reader.read_uint64(token, None)
        if obj_id is None:
            return
        if claim:
            cls._claim_object(obj_id)
        return obj_id

    @classmethod
    def _claim_object(cls, obj_id):
        obj_man = services.object_manager()
        inv_man = services.inventory_manager()
        obj = obj_man.get(obj_id)
        if obj is None:
            obj = obj_man.get(obj_id)
            if obj is None:
                obj = inv_man.get(obj_id)
        if obj is not None:
            if not obj.has_component(components.types.OBJECT_CLAIM_COMPONENT):
                obj.add_dynamic_component(components.types.OBJECT_CLAIM_COMPONENT)
            obj.object_claim_component.claim()
            obj_man.set_claimed_item(obj.id)
        inv_man.set_claimed_item(obj_id)

    def _create_object_for_situation(self, sim, obj_to_create, add_to_inventory=True):

        def setup_object(obj):
            obj.set_household_owner_id(sim.household_id)

        target = create_object(obj_to_create.id, init=setup_object)
        try:
            if add_to_inventory:
                sim.inventory_component.system_add_object(target)
            if target.object_claim_component is None:
                target.add_dynamic_component(components.types.OBJECT_CLAIM_COMPONENT)
            target.object_claim_component.claim()
            services.object_manager().set_claimed_item(target.id)
        except:
            target.destroy(source=sim, cause='Exception during creation of object for situation.')
            raise
        if target is None:
            raise ValueError('No object created for {} during {}'.format(self, self))
        return target

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        raise NotImplementedError

    @classmethod
    def get_tuned_jobs(cls):
        return cls._jobs

    def _initialize_situation_jobs(self):
        super()._initialize_situation_jobs()
        for (job, role_state) in self._get_tuned_job_and_default_role_state_tuples():
            self._add_job_type(job, role_state)

    def _load_situation_states_and_phases(self):
        super()._load_situation_states_and_phases()
        complex_seedling = self._seed.situation_complex_seedling
        if complex_seedling.state_custom_reader is not None:
            self._load_custom_state(complex_seedling.state_custom_reader)

    def _save_custom(self, seed):
        super()._save_custom(seed)
        seedling = seed.setup_for_complex_save()
        self._save_custom_situation(seedling.situation_custom_writer)
        self._save_custom_state(seedling.state_custom_writer)

    def _save_custom_situation(self, writer):
        pass

    def _save_custom_state(self, writer):
        uid = self._state_to_uid(self._cur_state)
        if uid == SituationComplexCommon.INVALID_STATE_UID:
            raise AssertionError('SituationState: {} in Situation: {} has no unique id'.format(self._cur_state, self))
        writer.write_uint32(SituationComplexCommon.STATE_ID_KEY, uid)
        self._cur_state.save_state(writer)

    def _load_custom_state(self, reader):
        uid = reader.read_uint32(SituationComplexCommon.STATE_ID_KEY, SituationComplexCommon.INVALID_STATE_UID)
        state_data = self._uid_to_state_data(uid)
        if state_data is None:
            raise KeyError
        new_state = state_data.construct_state()
        self._change_state(new_state, reader)

    @classmethod
    def get_current_state_type(cls, seed):
        state_type = None
        uid = cls.get_current_state_id(seed)
        if uid is not None:
            state_type = cls._uid_to_state_type(uid)
        return state_type

    @classmethod
    def get_current_state_id(cls, seed):
        uid = None
        state_reader = seed.situation_complex_seedling.state_custom_reader
        if state_reader is not None:
            uid = state_reader.read_uint32(SituationComplexCommon.STATE_ID_KEY, SituationComplexCommon.INVALID_STATE_UID)
        return uid

    @classmethod
    def default_job(cls):
        raise NotImplementedError

    @classmethod
    def get_sim_filter_gsi_name(cls):
        return str(cls)

    def _change_state(self, new_state, reader=None):
        if False and self.situation_serialization_option != situations.situation_types.SituationSerializationOption.DONT and self._state_to_uid(new_state) == self.INVALID_STATE_UID:
            logger.error('Situation State: {} is not in states() list for Situation: {}. This will prevent it from serializing when in this state.', new_state, self)
        old_state = self._cur_state
        self._cur_state = new_state
        if False and gsi_handlers.situation_handlers.situation_archiver.enabled:
            gsi_handlers.situation_handlers.situation_archiver.archive_event(self, 'Change State {} -> {}'.format(old_state, new_state), sub_event=True)
        try:
            if self._cur_state is not None:
                self._cur_state.owner = self
                self._cur_state.on_pre_activate(reader)
        finally:
            if old_state is not None:
                old_state.on_deactivate()
        if self._cur_state is not None:
            self._cur_state.on_activate(reader)

    def get_phase_state_name_for_gsi(self):
        if self._cur_state is None:
            return 'None'
        return self._cur_state.__class__.__name__

    def _on_set_sim_role_state(self, sim, job_type, role_state_type, role_affordance_target):
        if self._cur_state is not None:
            self._cur_state._on_set_sim_role_state(sim, job_type, role_state_type, role_affordance_target)

    def _get_role_state_overrides(self, sim, job_type, role_state_type, role_affordance_target):
        if self._cur_state is None:
            return (role_state_type, role_affordance_target)
        return self._cur_state._get_role_state_overrides(sim, job_type, role_state_type, role_affordance_target)

    def is_in_joinable_state(self):
        if self._cur_state is None:
            return True
        return self._cur_state.allow_join_situation()
