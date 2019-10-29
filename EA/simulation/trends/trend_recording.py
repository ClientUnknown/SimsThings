import randomfrom element_utils import build_element, CleanupTypefrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypeSingleSimfrom interactions.utils.tunable import TunableContinuationfrom objects.object_creation import ObjectCreationMixin, CreationDataBasefrom sims.sim_info_types import Agefrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableEnumEntry, OptionalTunablefrom trends.trend_tuning import TrendTuningimport elementsimport servicesimport sims4.loglogger = sims4.log.Logger('Trends', default_owner='rmccord')
class _TrendsCreationData(CreationDataBase):

    def __init__(self):
        self._recorded_trend_tag = None

    @property
    def recorded_trend_tag(self):
        return self._recorded_trend_tag

    @property
    def has_recorded_trend_tag(self):
        return self._recorded_trend_tag is not None

    def record_trend_tag(self, trend_tag):
        self._recorded_trend_tag = trend_tag

    def get_definition(self, *_, **__):
        if not self._recorded_trend_tag:
            return TrendTuning.TRENDLESS_VIDEO_DEFINITION
        definition_manager = services.definition_manager()
        filtered_defs = list(definition_manager.get_definitions_for_tags_gen({self._recorded_trend_tag}))
        if not filtered_defs:
            logger.error('Could not find object definitions tagged as {} for recording trends.', self.filter_tags)
            return
        return random.choice(filtered_defs)

class RecordTrendsElement(elements.ParentElement, ObjectCreationMixin, HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'subject': TunableEnumEntry(description='\n            The subject we want to record trends from.\n            ', tunable_type=ParticipantTypeSingleSim, default=ParticipantTypeSingleSim.Actor), 'continuation': TunableContinuation(description='\n            The continuation to push if we recorded a trend.\n            '), 'celebrity_tests': OptionalTunable(description='\n            If enabled, we will run these tests and attempt to apply the\n            celebrity trend if they pass.\n            ', tunable=TunableTestSet(description='\n                The tests to determine whether or not we should apply the celebrity\n                trend to the video recorded by this interaction.\n                ')), 'locked_args': {'creation_data': None}}

    def __init__(self, interaction, *args, sequence=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.interaction = interaction
        self.creation_data = _TrendsCreationData()
        self.sequence = sequence
        self.resolver = interaction.get_resolver()
        self._recorded_sim = None
        self._registered_events = []

    def unregister_trend_events(self):
        if self._registered_events:
            event_manager = services.get_event_manager()
            event_manager.unregister(self, self._registered_events)
            self._registered_events.clear()

    def handle_event(self, sim_info, event_type, resolver, *_, **__):
        if self.creation_data.has_recorded_trend_tag or sim_info.sim_id != self._recorded_sim.id:
            return
        if event_type == TestEvent.SkillValueChange:
            skill = resolver.event_kwargs['skill']
            if skill.trend_tag is not None:
                self.creation_data.record_trend_tag(skill.trend_tag)
        if self.creation_data.has_recorded_trend_tag:
            self.unregister_trend_events()

    def _record_static_trends(self):
        if self.celebrity_tests is not None and self.celebrity_tests.run_tests(self.resolver):
            self.creation_data.record_trend_tag(TrendTuning.CELEBRITY_TREND)
            return
        elif self._recorded_sim.age == Age.CHILD or self._recorded_sim.age == Age.TODDLER:
            self.creation_data.record_trend_tag(TrendTuning.TODDLER_CHILD_TREND)
            return

    def _start_recording(self, _):
        self._recorded_sim = self.interaction.get_participant(self.subject)
        if self._recorded_sim is None:
            logger.error('Subject is None for {} on {}.', self.subject, self.interaction)
        self._record_static_trends()
        if not self.creation_data.has_recorded_trend_tag:
            event_manager = services.get_event_manager()
            event_manager.register_single_event(self, TestEvent.SkillValueChange)
            self._registered_events.append(TestEvent.SkillValueChange)

    def _stop_recording(self, _):
        if services.current_zone().is_zone_shutting_down:
            return
        self.unregister_trend_events()
        created_object = self.create_object(self.resolver)
        if created_object is None:
            logger.error('Failed to create trend recording {} on {}', self.creation_data.recorded_trend_tag, self.interaction)
            return
        self.interaction.context.create_target_override = created_object
        self.interaction.push_tunable_continuation(self.continuation)

    def _run(self, timeline):
        sequence = [self._start_recording, self.sequence, self._stop_recording]
        child_element = build_element(sequence, critical=CleanupType.OnCancelOrException)
        return timeline.run_child(child_element)
