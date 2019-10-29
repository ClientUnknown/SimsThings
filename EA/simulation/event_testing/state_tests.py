from event_testing.results import TestResultfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypefrom objects import ALL_HIDDEN_REASONSfrom sims4.math import Operatorfrom sims4.tuning.tunable import TunableEnumEntry, TunableOperator, TunablePackSafeReference, TunableVariant, TunableSingletonFactory, HasTunableSingletonFactory, AutoFactoryInit, TunableReferencefrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport algosimport event_testing.test_baseimport servicesimport sims4.resources
class StateTest(event_testing.test_base.BaseTest):
    test_events = ()
    ALWAYS_PASS = 'always_pass'
    ALWAYS_FAIL = 'always_fail'
    FACTORY_TUNABLES = {'description': "\n        Gate availability by object state.  By default, the test will use the\n        state's linked stat as a fallback in case the target doesn't have the\n        state involved.\n        ", 'who': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'operator': TunableOperator(description='\n            The comparison to use.', default=Operator.EQUAL), 'value': TunablePackSafeReference(description='\n            The value to compare to.', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions='ObjectStateValue'), 'fallback_behavior': TunableVariant(description="\n            What to do if the given object doesn't have the state in question.\n            ", default=ALWAYS_FAIL, locked_args={ALWAYS_FAIL: ALWAYS_FAIL, ALWAYS_PASS: ALWAYS_PASS})}
    __slots__ = ('who', 'operator', 'operator_enum', 'value', 'fallback_behavior')

    def __init__(self, who, operator, value, fallback_behavior=ALWAYS_FAIL, **kwargs):
        super().__init__(**kwargs)
        self.who = who
        self.operator = operator
        self.operator_enum = Operator.from_function(operator)
        self.value = value
        self.fallback_behavior = fallback_behavior

    def get_expected_args(self):
        return {'test_targets': self.who}

    @cached_test
    def __call__(self, test_targets):
        if not test_targets:
            return TestResult(False, 'failed state check: no target object found!', tooltip=self.tooltip)
        for target in test_targets:
            if target.is_sim:
                if target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS) is None:
                    return TestResult(False, '{} failed state check: It is not an instantiated sim.', target, tooltip=self.tooltip)
                target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            state_component = target.state_component
            if self.value is not None and state_component is not None and state_component.has_state(self.value.state):
                curr_value = state_component.get_state(self.value.state)
            elif self.fallback_behavior == self.ALWAYS_FAIL:
                return TestResult(False, '{} failed state check: {} does not have the {} state.', self.who.name, target.__class__.__name__, self.value.state if self.value is not None else '<Unavailable>', tooltip=self.tooltip)
                if self.operator_enum.category == sims4.math.Operator.EQUAL:
                    if not self.operator(curr_value, self.value):
                        operator_symbol = self.operator_enum.symbol
                        return TestResult(False, '{} failed state check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.value.state, operator_symbol, self.value, curr_value, tooltip=self.tooltip)
                        if not self.operator(curr_value.value, self.value.value):
                            operator_symbol = self.operator_enum.symbol
                            return TestResult(False, '{} failed state check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.value.state, operator_symbol, self.value, curr_value, tooltip=self.tooltip)
                elif not self.operator(curr_value.value, self.value.value):
                    operator_symbol = self.operator_enum.symbol
                    return TestResult(False, '{} failed state check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.value.state, operator_symbol, self.value, curr_value, tooltip=self.tooltip)
            if self.operator_enum.category == sims4.math.Operator.EQUAL:
                if not self.operator(curr_value, self.value):
                    operator_symbol = self.operator_enum.symbol
                    return TestResult(False, '{} failed state check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.value.state, operator_symbol, self.value, curr_value, tooltip=self.tooltip)
                    if not self.operator(curr_value.value, self.value.value):
                        operator_symbol = self.operator_enum.symbol
                        return TestResult(False, '{} failed state check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.value.state, operator_symbol, self.value, curr_value, tooltip=self.tooltip)
            elif not self.operator(curr_value.value, self.value.value):
                operator_symbol = self.operator_enum.symbol
                return TestResult(False, '{} failed state check: {}.{} {} {} (current value: {})', self.who.name, target.__class__.__name__, self.value.state, operator_symbol, self.value, curr_value, tooltip=self.tooltip)
        return TestResult.TRUE

    def _get_make_true_value(self):
        if self.value is not None:
            for value in algos.binary_walk_gen(self.value.state.values):
                if self.operator(value.value, self.value.value):
                    return (TestResult.TRUE, value)
            operator_symbol = Operator.from_function(self.operator).symbol
        return (TestResult(False, 'Could not find value to satisfy operation: {} {} {}', self.value.state if self.value is not None else '<Unavailable>', operator_symbol, self.value), None)
TunableStateTest = TunableSingletonFactory.create_auto_factory(StateTest)
class WhiteBlackStateTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    test_events = ()
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            Who or what to apply this test to.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'states': TunableWhiteBlackList(description="\n            The target's states much conform to the white black list.\n            ", tunable=TunableReference(description='\n                Allowed and disallowed states.\n                ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), pack_safe=True))}

    def get_expected_args(self):
        return {'test_targets': self.participant}

    @cached_test
    def __call__(self, test_targets=tuple()):
        for target in test_targets:
            if target.state_component is None:
                return TestResult(False, '{} does not have a state component', target, tooltip=self.tooltip)
            current_states = list(target.state_component.values())
            if not self.states.test_collection(current_states):
                return TestResult(False, "{}'s current states do not match the WhiteBlackList that has been defined.", target, tooltip=self.tooltip)
        return TestResult.TRUE
