from sims4.tuning.tunable import TunableEnumEntry, HasTunableSingletonFactory, AutoFactoryInit, TunableIntervalfrom event_testing import test_basefrom event_testing.results import TestResultfrom interactions import ParticipantTypeimport build_buyimport terrain
class PoolSizeTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    FACTORY_TUNABLES = {'target': TunableEnumEntry(description='\n            The target of the test.\n            ', tunable_type=ParticipantType, default=ParticipantType.Object), 'allowable_size': TunableInterval(description='\n            The range (inclusive min, exclusive max) of pool sizes for which \n            this test will pass. Pool size is measured in half tiles.\n            ', tunable_type=float, default_lower=0, default_upper=0)}

    def get_expected_args(self):
        return {'targets': self.target}

    def __call__(self, targets):
        for target in targets:
            pool_size = build_buy.get_pool_size_at_location(target.location.zone_id, target.location.world_transform.translation, target.level)
            if pool_size is None:
                if 0.0 < terrain.get_water_depth_at_location(target.location):
                    return TestResult.TRUE
                return TestResult(False, 'PoolSizeTest: Target is not a pool or ocean')
            min_size = self.allowable_size.lower_bound
            max_size = self.allowable_size.upper_bound
            if not pool_size < min_size:
                if pool_size >= max_size:
                    return TestResult(False, f'PoolSizeTest: A pool size of {pool_size} is not within the allowable range of {min_size} to {max_size}')
            return TestResult(False, f'PoolSizeTest: A pool size of {pool_size} is not within the allowable range of {min_size} to {max_size}')
        return TestResult.TRUE
