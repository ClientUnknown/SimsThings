from event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import TestEventfrom global_policies.global_policy_enums import GlobalPolicyProgressEnumfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, Tunable, HasTunableFactory, TunableReference, TunableEnumEntry, TunableListimport servicesimport sims4
class _AllActivePolicies(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'inverse': Tunable(description='\n            If checked, test will pass if no states are in the specified progress\n            state.\n            ', tunable_type=bool, default=False)}

    def test(self, progress_state, tooltip):
        global_policies = services.global_policy_service().get_global_policies()
        all_policies_in_state = not self.inverse
        if all_policies_in_state:
            for policy in global_policies:
                if policy.progress_state != progress_state:
                    return TestResult(False, 'Failed to pass Global Policies Test, {} is not in state {}.'.format(policy, progress_state))
        else:
            for policy in global_policies:
                if policy.progress_state == progress_state:
                    return TestResult(False, 'Failed to pass Global Policies Test, {} is in state {}.'.format(policy, progress_state))
        return TestResult(True)

class _SpecificPolicy(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'policies': TunableList(description='\n            The subset of policies against which to test if all members are in \n            the specified state.\n            \n            Inactive policies that have never had progress made towards them\n            will be treated as Not-Started.\n            ', tunable=TunableReference(description='\n                The global policy whose progress state is checked.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SNIPPET), class_restrictions=('GlobalPolicy',), allow_none=False, pack_safe=True), unique_entries=True)}

    def get_custom_event_registration_keys(self):
        keys = []
        for policy in self.policies:
            keys.append((TestEvent.GlobalPolicyProgress, policy))
        return keys

    def test(self, progress_state, tooltip):
        global_policy_service = services.global_policy_service()
        if self.policies or progress_state != GlobalPolicyProgressEnum.NOT_STARTED:
            return TestResult(False, "Trying to test for policies that have been started when those policies don't exist in current pack configuration.")
        for policy in self.policies:
            global_policy = global_policy_service.get_global_policy(policy, create=False)
            if global_policy is None:
                if progress_state != GlobalPolicyProgressEnum.NOT_STARTED:
                    return TestResult(False, 'Global Policy {} has never been started, has no progress state.'.format(global_policy))
                    if global_policy.progress_state != progress_state:
                        return TestResult(False, 'Global Policy {} is in state {} not the specified state {}.'.format(global_policy, global_policy.progress_state, progress_state))
            elif global_policy.progress_state != progress_state:
                return TestResult(False, 'Global Policy {} is in state {} not the specified state {}.'.format(global_policy, global_policy.progress_state, progress_state))
        return TestResult(True)

class GlobalPolicyStateTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'test_type': TunableVariant(description="\n            The type of test to run. Note, 'All Active Policies' will test against\n            the set of all policies that have ever had progress made towards them.\n            ", all_active_policies=_AllActivePolicies.TunableFactory(), specific_policy=_SpecificPolicy.TunableFactory(), default='all_active_policies'), 'progress_state': TunableEnumEntry(description='\n            The progress state against which to test.\n            ', tunable_type=GlobalPolicyProgressEnum, default=GlobalPolicyProgressEnum.IN_PROGRESS)}

    def get_test_events_to_register(self):
        return (TestEvent.GlobalPolicyProgress,)

    def get_expected_args(self):
        return {}

    def __call__(self):
        return self.test_type().test(self.progress_state, self.tooltip)
