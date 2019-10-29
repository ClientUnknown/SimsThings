import event_testing.test_baseimport sims4.logfrom event_testing.results import TestResultfrom interactions import ParticipantTypeSim, ParticipantTypeObjectfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableEnumEntry, Tunablefrom tag import TunableTaglogger = sims4.log.Logger('FavoritesTests', default_owner='trevor')
class FavoritesTest(HasTunableSingletonFactory, AutoFactoryInit, event_testing.test_base.BaseTest):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description="\n            The subject who's favorite we're testing against.\n            ", tunable_type=ParticipantTypeSim, default=ParticipantTypeSim.Actor), 'target': TunableEnumEntry(description='\n            The potential favorite object to test agains.\n            ', tunable_type=ParticipantTypeObject, default=ParticipantTypeObject.Object), 'favorite_type': TunableTag(description='\n           The tag that represents this type of favorite.\n           ', filter_prefixes=('Func',)), 'negate': Tunable(description='\n            If checked, the result of this test will be negated. Error cases,\n            like subject or target not being found or the subject not having a\n            favorites tracker, will always fail.\n            ', tunable_type=bool, default=False)}

    def get_expected_args(self):
        return {'subject': self.subject, 'target': self.target}

    def __call__(self, subject=None, target=None):
        if not (subject and target):
            logger.error('Subject or Target not found while running a Favorites Test')
            return TestResult(False, 'Subject or Target was not found.', tooltip=self.tooltip)
        if len(subject) > 1:
            logger.warn('FavoritesTest is being called with more than one participant for subject. Only the first participant will be used.')
        if len(target) > 1:
            logger.warn('FavoritesTest is being called with more than one participant for target. Only the first participant will be used.')
        sim = subject[0]
        obj = target[0]
        favorites_tracker = sim.sim_info.favorites_tracker
        if favorites_tracker is None:
            logger.error("Trying to get a favorites tracker for Sim {} but they don't have one.", sim)
            return TestResult(False, 'Sim {} has no favorites tracker.', sim, tooltip=self.tooltip)
        if favorites_tracker.is_favorite(self.favorite_type, obj):
            if self.negate:
                return TestResult(False, 'Found favorite for Sim. Test is negated.', tooltip=self.tooltip)
            return TestResult.TRUE
        if self.negate:
            return TestResult.TRUE
        return TestResult(False, 'Object {} is not the favorite for Sim {}', obj, sim, tooltip=self.tooltip)
