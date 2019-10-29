import randomfrom business.business_employee_situation_mixin import BusinessEmployeeSituationMixinfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom role.role_state import RoleStatefrom sims4.tuning.tunable import TunableSimMinute, AutoFactoryInit, HasTunableFactoryfrom sims4.utils import classpropertyfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableInteractionOfInterest, SituationState, SituationStateDatafrom situations.situation_job import SituationJobimport servicesimport sims4import situationslogger = sims4.log.Logger('Retail', default_owner='trevor')
class RetailEmployeeSituation(BusinessEmployeeSituationMixin, SituationComplexCommon):

    class _EmployeeSituationState(HasTunableFactory, AutoFactoryInit, SituationState):
        FACTORY_TUNABLES = {'role_state': RoleState.TunableReference(description='\n                The role state that is active on the employee for the duration\n                of this state.\n                '), 'timeout_min': TunableSimMinute(description='\n                The minimum amount of time, in Sim minutes, the employee will be\n                in this state before moving on to a new state.\n                ', default=10), 'timeout_max': TunableSimMinute(description='\n                The maximum amount of time, in Sim minutes, the employee will be\n                in this state before moving on to a new state.\n                ', default=30), 'push_interaction': TunableInteractionOfInterest(description='\n                If an interaction of this type is run by the employee, this\n                state will activate.\n                ')}

        def __init__(self, *args, state_name=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.state_name = state_name

        def on_activate(self, reader=None):
            super().on_activate(reader)
            self.owner._set_job_role_state(self.owner.employee_job, self.role_state)
            timeout = random.randint(self.timeout_min, self.timeout_max)
            self._create_or_load_alarm(self.state_name, timeout, self._timeout_expired, reader=reader)

        def _timeout_expired(self, *_, **__):
            self._change_state(self.owner._choose_next_state())

    INSTANCE_TUNABLES = {'employee_job': SituationJob.TunableReference(description='\n            The situation job for the employee.\n            '), 'role_state_go_to_store': RoleState.TunableReference(description='\n            The role state for getting the employee inside the store. This is\n            the default role state and will be run first before any other role\n            state can start.\n            '), 'role_state_go_to_store_timeout': TunableSimMinute(description="\n            Automatically advance out of the role state after waiting for this\n            duration. There's a number of reasons the employee can fail to exit\n            the role state in a timely fashion, such as the register is blocked\n            (by another employee clocking, even) and hijacked by a social.\n            ", default=60), 'state_socialize': _EmployeeSituationState.TunableFactory(description='\n            The state during which employees socialize with customers.\n            ', locked_args={'state_name': 'socialize'}), 'state_restock': _EmployeeSituationState.TunableFactory(description='\n            The state during which employees restock items.\n            ', locked_args={'state_name': 'restock'}), 'state_clean': _EmployeeSituationState.TunableFactory(description='\n            The state during which employees clean the store.\n            ', locked_args={'state_name': 'clean'}), 'state_slack_off': _EmployeeSituationState.TunableFactory(description='\n            The state during which employees slack off.\n            ', locked_args={'state_name': 'slack_off'}), 'state_ring_up_customers': _EmployeeSituationState.TunableFactory(description='\n            The state during which employees will ring up customers.\n            ', locked_args={'state_name': 'ring_up_customers'}), 'go_to_store_interaction': TunableInteractionOfInterest(description='\n            The interaction that, when run by an employee, will switch the\n            situation state to start cleaning, upselling, restocking, etc.\n            '), 'go_home_interaction': TunableInteractionOfInterest(description='\n            The interaction that, when run on an employee, will have them end\n            this situation and go home.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._employee_sim_info = None
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.state_socialize.push_interaction.custom_keys_gen())
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.state_restock.push_interaction.custom_keys_gen())
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.state_clean.push_interaction.custom_keys_gen())
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.state_slack_off.push_interaction.custom_keys_gen())
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.state_ring_up_customers.push_interaction.custom_keys_gen())
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.go_home_interaction.custom_keys_gen())

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _GoToStoreState), SituationStateData(2, cls.state_socialize), SituationStateData(5, cls.state_restock), SituationStateData(6, cls.state_clean), SituationStateData(7, cls.state_slack_off), SituationStateData(8, cls.state_ring_up_customers))

    @classmethod
    def _state_to_uid(cls, state_to_find):
        state_type_to_find = type(state_to_find)
        if state_type_to_find is _GoToStoreState:
            return 1
        state_name = getattr(state_to_find, 'state_name', None)
        if state_name is None:
            return cls.INVALID_STATE_UID
        for state_data in cls._states():
            if getattr(state_data.state_type, 'state_name', None) == state_name:
                return state_data.uid
        return cls.INVALID_STATE_UID

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_uint64('original_duration', self._original_duration)

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.InteractionComplete:
            target_sim = resolver.interaction.get_participant(ParticipantType.TargetSim)
            if target_sim is None:
                target_sim = resolver.interaction.get_participant(ParticipantType.Actor)
            target_sim = getattr(target_sim, 'sim_info', target_sim)
            if target_sim is self._employee_sim_info:
                if resolver(self.state_socialize.push_interaction):
                    self._change_state(self.state_socialize())
                elif resolver(self.state_restock.push_interaction):
                    self._change_state(self.state_restock())
                elif resolver(self.state_clean.push_interaction):
                    self._change_state(self.state_clean())
                elif resolver(self.state_slack_off.push_interaction):
                    self._change_state(self.state_slack_off())
                elif resolver(self.state_ring_up_customers.push_interaction):
                    self._change_state(self.state_ring_up_customers())
                elif resolver(self.go_home_interaction):
                    self._on_business_closed()
        super().handle_event(sim_info, event, resolver)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.employee_job, cls.role_state_go_to_store)]

    @classmethod
    def default_job(cls):
        return cls.employee_job

    def start_situation(self):
        super().start_situation()
        self._change_state(_GoToStoreState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.LOT

    def get_employee_sim_info(self):
        if self._employee_sim_info is not None:
            return self._employee_sim_info
        return next(self._guest_list.invited_sim_infos_gen(), None)

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._employee_sim_info = sim.sim_info
        self._update_work_buffs(from_load=True)

    @property
    def _is_clocked_in(self):
        business_manager = services.business_service().get_business_manager_for_zone()
        if business_manager is None:
            return False
        return business_manager.is_employee_clocked_in(self._employee_sim_info)

    def _choose_next_state(self):
        valid_states = [self.state_socialize, self.state_restock, self.state_clean, self.state_ring_up_customers]
        random_state = random.choice(valid_states)
        return random_state()

class _GoToStoreState(SituationState):
    _GO_TO_STORE_TIMEOUT = 'go_to_store_timeout'

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.employee_job, self.owner.role_state_go_to_store)
        for custom_key in self.owner.go_to_store_interaction.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionComplete, custom_key)
        self._create_or_load_alarm(self._GO_TO_STORE_TIMEOUT, self.owner.role_state_go_to_store_timeout, self._on_timeout, reader=reader)

    def on_deactivate(self):
        employee_sim_info = self.owner._employee_sim_info
        if employee_sim_info is not None and not services.current_zone().is_zone_shutting_down:
            sim_instance = employee_sim_info.get_sim_instance()
            if sim_instance is not None and not (sim_instance.is_being_destroyed or self.owner._is_clocked_in):
                self.owner._start_work_duration()
        return super().on_deactivate()

    def handle_event(self, sim_info, event, resolver):
        if self.owner is None:
            return
        if event == TestEvent.InteractionComplete and self.owner._employee_sim_info is sim_info and resolver(self.owner.go_to_store_interaction):
            self._advance_state()

    def _advance_state(self):
        self.owner._start_work_duration()
        self._change_state(self.owner._choose_next_state())

    def _on_timeout(self, alarm_handle):
        self._advance_state()
