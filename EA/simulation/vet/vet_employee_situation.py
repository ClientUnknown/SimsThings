import functoolsfrom business.business_employee_situation_mixin import BusinessEmployeeSituationMixinfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom sims4 import randomfrom sims4.resources import Typesfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableTuple, TunableMapping, OptionalTunable, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation import Situation, TunableEnumEntry, TunableRangefrom situations.situation_complex import CommonSituationState, TunableInteractionOfInterest, SituationComplexCommon, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom vet.vet_clinic_handlers import log_vet_flow_entryimport servicesimport sims4import situations.bouncerlogger = sims4.log.Logger('VetEmployeeSituation', default_owner='jdimailig')
class VetEmployeeSituationStates(DynamicEnum):
    DEFAULT = 0

class VetManagedEmployeeSituationState(CommonSituationState):
    FACTORY_TUNABLES = {'transition_out_interaction': OptionalTunable(description='\n             When this interaction is run, this state can be transitioned out of;\n             we will try to advance to another state.  This can be used as a way \n             to switch states before the timeout occurs.\n             ', tunable=TunableInteractionOfInterest()), 'state_specific_transitions': TunableMapping(description='\n            Mapping to allow direct transitions to other states using interactions.\n            ', key_type=TunableEnumEntry(VetEmployeeSituationStates, default=VetEmployeeSituationStates.DEFAULT), value_type=TunableInteractionOfInterest()), 'locked_args': {'allow_join_situation': False}}

    def __init__(self, state_type, *args, enable_disable=None, transition_out_interaction=None, state_specific_transitions=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._state_type = state_type
        self._transition_out_interaction = transition_out_interaction
        self._state_specific_transitions = state_specific_transitions
        self._test_custom_keys = set()
        if self._transition_out_interaction is not None:
            self._transition_out_interaction = transition_out_interaction
            self._test_custom_keys.update(self._transition_out_interaction.custom_keys_gen())
        for state_specific_transition in self._state_specific_transitions.values():
            self._test_custom_keys.update(state_specific_transition.custom_keys_gen())

    @property
    def state_type(self):
        return self._state_type

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        for custom_key in self._test_custom_keys:
            self._test_event_register(TestEvent.InteractionComplete, custom_key)

    def handle_event(self, sim_info, event, resolver):
        if not self.owner.is_sim_info_in_situation(sim_info):
            target_sim_info = resolver.get_participant(ParticipantType.TargetSim)
            if target_sim_info is None or not self.owner.is_sim_info_in_situation(target_sim_info):
                return
        if event == TestEvent.InteractionComplete:
            for (state_type, state_specific_transition) in self._state_specific_transitions.items():
                if resolver(state_specific_transition):
                    self.owner.try_set_next_state(state_type)
                    return
            if self._transition_out_interaction is not None and resolver(self._transition_out_interaction):
                self.owner.try_set_next_state()

    def timer_expired(self):
        self.owner.try_set_next_state()

class VetEmployeeSituation(BusinessEmployeeSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'_default_state': VetManagedEmployeeSituationState.TunableFactory(description='\n                Default state for the vet employee, which can never be disabled.\n                ', locked_args={'state_type': VetEmployeeSituationStates.DEFAULT}, tuning_group=GroupNames.SITUATION), '_managed_states': TunableMapping(description='\n            A mapping of state types to states.\n            ', key_type=TunableEnumEntry(VetEmployeeSituationStates, default=VetEmployeeSituationStates.DEFAULT, invalid_enums=(VetEmployeeSituationStates.DEFAULT,)), value_type=TunableTuple(state=VetManagedEmployeeSituationState.TunableFactory(), enable_disable=OptionalTunable(display_name='Enable/Disable Support', tunable=TunableTuple(enable_interaction=TunableInteractionOfInterest(description='\n                            Interaction of interest which will cause this state to be enabled.\n                            '), disable_interaction=TunableInteractionOfInterest(description='\n                            Interaction of interest which will cause this state to be disabled.\n                            '), disabling_buff=TunableReference(description='\n                            The Buff that disables the state, used to set\n                            the state from the load.\n                            ', manager=services.get_instance_manager(Types.BUFF)))), weight=TunableRange(description='\n                    A weight to use to choose to run this state in a random lottery.\n                    ', tunable_type=int, minimum=0, default=1)), tuning_group=GroupNames.SITUATION), '_default_state_weight': TunableRange(description='\n            A weight to use to choose to for the default state in a random\n            lottery of which state to run.\n            ', tunable_type=int, minimum=1, default=1)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        state_data = []
        state_data.append(SituationStateData(VetEmployeeSituationStates.DEFAULT.value, VetManagedEmployeeSituationState, factory=cls._default_state))
        for (state_type, state_tuning) in cls._managed_states.items():
            state_data.append(SituationStateData(state_type.value, VetManagedEmployeeSituationState, factory=functools.partial(state_tuning.state, state_type)))
        return state_data

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _state_to_uid(cls, state_to_find):
        return state_to_find.state_type.value

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._default_state._tuned_values.job_and_role_changes.items())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._locked_states = set()
        self._type_to_disable_interaction = {}
        self._type_to_enable_interaction = {}
        self._state_disabling_buffs = set()
        for (state_type, state_tuning) in self._managed_states.items():
            enable_disable = state_tuning.enable_disable
            if enable_disable is None:
                pass
            else:
                self._register_test_event_for_keys(TestEvent.InteractionComplete, enable_disable.disable_interaction.custom_keys_gen())
                self._type_to_disable_interaction[state_type] = enable_disable.disable_interaction
                self._register_test_event_for_keys(TestEvent.InteractionComplete, enable_disable.enable_interaction.custom_keys_gen())
                self._type_to_enable_interaction[state_type] = enable_disable.enable_interaction
                self._state_disabling_buffs.add(enable_disable.disabling_buff)

    def start_situation(self):
        super().start_situation()
        self._change_state(self._default_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._start_work_duration()

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override)
        sim.Buffs.on_buff_added.append(self._updated_disabled_states)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        sim.Buffs.on_buff_added.remove(self._updated_disabled_states)

    def _updated_disabled_states(self, buff_type, sim_id):
        if buff_type not in self._state_disabling_buffs:
            return
        for state_type in self._managed_states:
            state_tuning = self._managed_states[state_type]
            if state_tuning.enable_disable is None:
                pass
            elif state_tuning.enable_disable.disabling_buff == buff_type:
                self._disable_state(state_type)

    def get_employee(self):
        return next(iter(self.all_sims_in_situation_gen()), None)

    def get_employee_sim_info(self):
        employee = self.get_employee()
        if employee is None:
            return
        return employee.sim_info

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        target_sim_info = resolver.get_participant(ParticipantType.TargetSim)
        if not (target_sim_info is sim_info and self.is_sim_info_in_situation(sim_info)):
            return
        for (state_type, interaction_test) in self._type_to_disable_interaction.items():
            if resolver(interaction_test):
                self._disable_state(state_type)
        for (state_type, interaction_test) in self._type_to_enable_interaction.items():
            if resolver(interaction_test):
                self._enable_state(state_type)

    def try_set_next_state(self, next_state_type=None):
        if next_state_type is None or next_state_type in self._locked_states:
            next_state_type = self._choose_next_state(invalid_states=(next_state_type,))
        self._change_to_state_type(next_state_type)

    def _change_to_state_type(self, state_type):
        self.log_flow_entry('Changing to state {}'.format(state_type.name))
        if state_type == VetEmployeeSituationStates.DEFAULT:
            self._change_state(self._default_state())
        else:
            self._change_state(self._managed_states[state_type].state(state_type))

    def _choose_next_state(self, invalid_states=None):
        available_states = set(self._managed_states.keys()) - self._locked_states
        if invalid_states is not None:
            available_states = available_states - set(invalid_states)
        if not available_states:
            return VetEmployeeSituationStates.DEFAULT
        weighted = [(self._managed_states[key].weight, key) for key in available_states]
        weighted.append((self._default_state_weight, VetEmployeeSituationStates.DEFAULT))
        return random.weighted_random_item(weighted)

    def _enable_state(self, state_type):
        if state_type in self._locked_states:
            self._locked_states.remove(state_type)

    def _disable_state(self, state_type):
        self._locked_states.add(state_type)
        if self._cur_state.state_type == state_type:
            self.try_set_next_state()

    def get_phase_state_name_for_gsi(self):
        if self._cur_state is None:
            return 'None'
        else:
            return self._cur_state.state_type.name

    def _gsi_additional_data_gen(self):
        yield ('Locked States', str(self._locked_states))

    def log_flow_entry(self, message):
        log_vet_flow_entry(repr(self.get_employee()), type(self).__name__, message)
lock_instance_tunables(VetEmployeeSituation, duration=0, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.VENUE_EMPLOYEE)