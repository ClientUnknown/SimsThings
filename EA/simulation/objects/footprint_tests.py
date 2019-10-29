from event_testing.results import TestResultfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypeSingle, ParticipantTypeSingleSimfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableVariant, TunableTuple, Tunable, OptionalTunable, TunableSetfrom sims4.tuning.tunable_hash import TunableStringHash32from tag import TunableTagimport event_testing.test_baseimport services
class InFootprintTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    BY_PARTICIPANT = 0
    BY_TAG = 1
    test_events = ()
    FACTORY_TUNABLES = {'actor': TunableEnumEntry(description='\n            The actor whose location will be used.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'footprint_target': TunableVariant(description='\n            The object whose footprint to check against.\n            ', by_participant=TunableTuple(description='\n                Get footprint from a participant.\n                ', locked_args={'target_type': BY_PARTICIPANT}, participant=TunableEnumEntry(description='\n                    The participant whose required slot count we consider.\n                    ', tunable_type=ParticipantTypeSingle, default=ParticipantTypeSingle.Object)), by_tag=TunableTuple(description='\n                Get footprint from an object with this tag. If there are\n                multiple, the test passes as long as one passes.\n                ', tag=TunableTag(description='\n                    Tag to find objects by.\n                    '), locked_args={'target_type': BY_TAG}), default='by_participant'), 'footprint_names': OptionalTunable(description="\n            Specific footprints to check against. If left unspecified, we\n            check against the object's default footprints (i.e. the ones\n            enabled in Medator).\n            ", tunable=TunableSet(tunable=TunableStringHash32(description='\n                    Name of footprint. Can be looked up in Medator. If in\n                    doubt, consult the modeler.\n                    '), minlength=1)), 'invert': Tunable(description='\n            If checked, test will pass if the actor is not in the footprint.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        kwargs = {}
        kwargs['actors'] = self.actor
        if self.footprint_target.target_type == self.BY_PARTICIPANT:
            kwargs['footprint_target'] = self.footprint_target.participant
        return kwargs

    def _test_if_sim_in_target_footprint(self, sim, target):
        if self.footprint_names is None:
            polygon = target.footprint_polygon
        else:
            polygon = target.get_polygon_from_footprint_name_hashes(self.footprint_names)
        if polygon is not None and polygon.contains(sim.position):
            return True
        return False

    @cached_test
    def __call__(self, actors=(), footprint_target=None):
        actor = next(iter(actors), None)
        if actor is None:
            return TestResult(False, 'No actors', tooltip=self.tooltip)
        actor_sim = actor.get_sim_instance()
        if actor_sim is None:
            return TestResult(False, "Actor is not an instantiated Sim. Can't check position: {}", actor[0], tooltip=self.tooltip)
        if self.footprint_target.target_type == self.BY_PARTICIPANT:
            if footprint_target is None:
                return TestResult(False, 'Missing participant.', tooltip=self.tooltip)
            targets = (footprint_target,)
        elif self.footprint_target.target_type == self.BY_TAG:
            targets = services.object_manager().get_objects_with_tag_gen(self.footprint_target.tag)
        else:
            return TestResult(False, 'Unknown target type: {}', self.footprint_target.target_type, tooltip=self.tooltip)
        if self.invert:
            if any(self._test_if_sim_in_target_footprint(actor_sim, target) for target in targets):
                return TestResult(False, 'In footprint, inverted', tooltip=self.tooltip)
        elif not any(self._test_if_sim_in_target_footprint(actor_sim, target) for target in targets):
            return TestResult(False, 'Not in footprint', tooltip=self.tooltip)
        return TestResult.TRUE
