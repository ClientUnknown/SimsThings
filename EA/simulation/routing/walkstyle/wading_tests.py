from event_testing import test_basefrom event_testing.results import TestResultfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeSinglefrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableVariant, Tunable, TunableIntervalfrom terrain import get_water_depthfrom world.ocean_tuning import OceanTuningimport routing
class _CustomIntervalTest(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'height_range': TunableInterval(tunable_type=float, default_lower=-1000, default_upper=1000, minimum=-1000, maximum=1000)}

    def evaluate(self, subject, water_height, wading_interval, negate, tooltip):
        lower_bound = self.height_range.lower_bound
        upper_bound = self.height_range.upper_bound
        in_interval = lower_bound <= water_height <= upper_bound
        if in_interval:
            if negate:
                return TestResult(False, f'{subject} cannot go here. Water height {water_height} is between {lower_bound} and {upper_bound} and negate is True.', tooltip=tooltip)
            return TestResult.TRUE
        elif negate:
            return TestResult.TRUE
        else:
            return TestResult(False, f'{subject} cannot go here. Water height {water_height} is not between {lower_bound} and {upper_bound}', tooltip=tooltip)

class _WalkHereTest:

    def evaluate(self, subject, water_height, wading_interval, negate, tooltip):
        if wading_interval is None:
            sim = subject.get_sim_instance()
            if sim.routing_surface.type == routing.SurfaceType.SURFACETYPE_WORLD:
                if negate:
                    return TestResult(False, f'{subject} can walk on the world routing surface, but the test is negated.', tooltip=tooltip)
                return TestResult.TRUE
            if negate:
                return TestResult.TRUE
            return TestResult(False, f'{subject} cannot walk here as they have no wading interval and are not on the world routing surface.', tooltip=tooltip)
        if water_height < wading_interval.lower_bound:
            if negate:
                return TestResult(False, f'{subject} can walk here, but the test is negated. Water height offset: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)
            return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, f'{subject} cannot walk here. Water height offset: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)

class _WetHereTest:

    def evaluate(self, subject, water_height, wading_interval, negate, tooltip):
        if wading_interval is None:
            if negate:
                return TestResult.TRUE
            return TestResult(False, f'{subject} no wading water defined in world.', tooltip=tooltip)
        if 0 < water_height and water_height < wading_interval.lower_bound:
            if negate:
                return TestResult(False, f'{subject} can walk here, but the test is negated. Water height offset: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)
            return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, f'{subject} cannot walk here. Water height offset: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)

class _WadeHereTest:

    def evaluate(self, subject, water_height, wading_interval, negate, tooltip):
        if wading_interval is None:
            return TestResult(False, f'No wading interval found for {subject}.', tooltip=tooltip)
        if water_height in wading_interval:
            if negate:
                return TestResult(False, f'{subject} can wade here, but the test is negated. Water height offset: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)
            return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, f'{subject} cannot wade here. Water height offset: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)

class _SwimHereTest:

    def evaluate(self, subject, water_height, wading_interval, negate, tooltip):
        if wading_interval is None:
            sim = subject.get_sim_instance()
            if sim.routing_surface.type == routing.SurfaceType.SURFACETYPE_POOL:
                if negate:
                    return TestResult(False, f'{subject} can swim on the pool routing surface, but the test is negated.', tooltip=tooltip)
                return TestResult.TRUE
            if negate:
                return TestResult.TRUE
            return TestResult(False, f'{subject} cannot swim here as they have no wading interval and are not on the pool routing surface.', tooltip=tooltip)
        if water_height > wading_interval.upper_bound:
            if negate:
                return TestResult(False, f'{subject} can swim here, but the test is negated. Water height: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)
            return TestResult.TRUE
        if negate:
            return TestResult.TRUE
        return TestResult(False, f'{subject} cannot swim here. Water height offset: {water_height} Wading interval: {wading_interval}.', tooltip=tooltip)

class WadingIntervalTest(HasTunableSingletonFactory, AutoFactoryInit, test_base.BaseTest):
    WATER_DEPTH_ON_LAND = -1.0
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject to test to determine if they should walk, wade or swim\n            based on the water height at the targets location.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Actor), 'target': TunableEnumEntry(description='\n            The target whose location will be used to determine the water\n            height.\n            ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object), 'test': TunableVariant(description='\n            The type of test to run against the subjects wading interval and \n            the targets location.\n            ', default='walk_here', custom=_CustomIntervalTest.TunableFactory(), locked_args={'walk_here': _WalkHereTest(), 'wet_here': _WetHereTest(), 'wade_here': _WadeHereTest(), 'swim_here': _SwimHereTest()}), 'negate': Tunable(description='\n            If checked, negate the result of the specified test.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subjects': self.subject, 'targets': self.target}

    @cached_test
    def __call__(self, subjects, targets):
        subject = next(iter(subjects), None)
        if subject is None:
            return TestResult(False, 'WadingTest: Subject is None')
        target = next(iter(targets), None)
        if target is None:
            return TestResult(False, 'WadingTest: Target is None.')
        if target.is_sim:
            target = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
            if target is None:
                return TestResult(False, 'WadingTest: Target Sim is not instanced.')
        if target.location is None or target.location.routing_surface is None:
            water_height = WadingIntervalTest.WATER_DEPTH_ON_LAND
        else:
            target_location = target.location.transform.translation
            water_height = get_water_depth(target_location[0], target_location[2], target.location.level)
        wading_interval = OceanTuning.get_actor_wading_interval(subject)
        return self.test.evaluate(subject, water_height, wading_interval, self.negate, self.tooltip)
