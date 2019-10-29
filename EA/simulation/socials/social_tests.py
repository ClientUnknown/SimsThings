import itertoolsfrom event_testing.results import TestResultfrom event_testing.test_base import BaseTestfrom event_testing.test_events import cached_testfrom interactions import ParticipantTypefrom objects import ALL_HIDDEN_REASONSfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableEnumEntry, TunableSetimport cachesimport relationships.relationship_bit
class SocialContextTest(HasTunableSingletonFactory, AutoFactoryInit, BaseTest):
    FACTORY_TUNABLES = {'participant': TunableEnumEntry(description='\n            The participant against which to test social context.\n            ', tunable_type=ParticipantType, default=ParticipantType.Actor), 'target_subject': TunableEnumEntry(description="\n            The participant that must be included in participant's social group\n            in order for this test to rely solely on the participant's current\n            STC. If target_subject is not in any of participant's social groups,\n            then the STC test will only consider the prevailing STC between\n            participant and target_subject.\n            ", tunable_type=ParticipantType, default=ParticipantType.TargetSim), 'required_set': TunableSet(description="\n            A set of contexts that are required. If any context is specified,\n            the test will fail if the participant's social context is not one of\n            these entries.\n            ", tunable=relationships.relationship_bit.RelationshipBit.TunableReference(pack_safe=True)), 'prohibited_set': TunableSet(description="\n            A set of contexts that are prohibited. The test will fail if the\n            participant's social context is one of these entries.\n            ", tunable=relationships.relationship_bit.RelationshipBit.TunableReference(pack_safe=True))}

    @staticmethod
    @caches.cached
    def get_overall_short_term_context_bit(*sims):
        positive_stc_tracks = []
        negative_stc_tracks = []
        for (sim_a, sim_b) in itertools.combinations(sims, 2):
            stc_track = sim_a.relationship_tracker.get_relationship_prevailing_short_term_context_track(sim_b.id)
            if stc_track is not None:
                if stc_track.get_value() >= 0:
                    positive_stc_tracks.append(stc_track)
                else:
                    negative_stc_tracks.append(stc_track)
        prevailing_stc_tracks = negative_stc_tracks if len(negative_stc_tracks) >= len(positive_stc_tracks) else positive_stc_tracks
        if prevailing_stc_tracks:
            prevailing_stc_track = None
            prevailing_stc_magnitude = None
            for (_, group) in itertools.groupby(sorted(prevailing_stc_tracks, key=lambda stc_track: stc_track.stat_type.type_id()), key=lambda stc_track: stc_track.stat_type.type_id()):
                group = list(group)
                stc_magnitude = sum(stc_track.get_value() for stc_track in group)/len(group)
                if not prevailing_stc_track is None:
                    if abs(stc_magnitude) > abs(prevailing_stc_magnitude):
                        prevailing_stc_magnitude = stc_magnitude
                        prevailing_stc_track = group[0].stat_type
                prevailing_stc_magnitude = stc_magnitude
                prevailing_stc_track = group[0].stat_type
            return prevailing_stc_track.get_bit_at_relationship_value(prevailing_stc_magnitude)
        else:
            sim = next(iter(sims), None)
            if sim is not None:
                return sim.relationship_tracker.get_default_short_term_context_bit()

    def get_expected_args(self):
        return {'subject': self.participant, 'target': self.target_subject}

    @cached_test
    def __call__(self, subject=(), target=()):
        subject = next(iter(subject), None)
        target = next(iter(target), None)
        if subject is None:
            return TestResult(False, '{} is not a valid participant', self.participant)
        if target is None:
            return TestResult(False, '{} is not a valid participant', self.target_subject)
        sim = subject.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if sim is None:
            return TestResult(False, '{} is non-instantiated', subject)
        target_sim = target.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
        if target_sim is None:
            return TestResult(False, '{} is non-instantiated', target)
        if sim.is_in_group_with(target_sim):
            social_context = sim.get_social_context()
        else:
            social_context = self.get_overall_short_term_context_bit(sim, target_sim)
        if self.required_set and social_context not in self.required_set:
            return TestResult(False, '{} for {} does not match required contexts', social_context, sim, tooltip=self.tooltip)
        if social_context in self.prohibited_set:
            return TestResult(False, '{} for {} is a prohibited context', social_context, sim, tooltip=self.tooltip)
        return TestResult.TRUE
