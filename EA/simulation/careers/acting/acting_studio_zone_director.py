from audio.primitive import TunablePlayAudio, play_tunable_audiofrom careers.acting.performance_object_data import PerformanceObjectDatafrom careers.career_event_zone_director import CareerEventZoneDirectorfrom event_testing.resolver import SingleActorAndObjectResolverfrom event_testing.test_events import TestEventfrom interactions.utils.loot_ops import LockDoorfrom objects.components import typesfrom sims4.tuning.tunable import TunableMapping, TunableReference, TunableSet, TunableTuple, TunableVariant, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom tag import TunableTagfrom tunable_time import TunableTimeSpanimport alarmsimport servicesimport sims4.resources
class ActingStudioZoneDirector(CareerEventZoneDirector):
    INSTANCE_TUNABLES = {'stage_marks': TunableMapping(description='\n            A mapping of stage marker tags to the interactions that should be\n            added to them for this gig. These interactions will be applied to\n            the stage mark/object on zone load.\n            ', key_name='stage_mark_tag', key_type=TunableTag(description='\n                The tag for the stage mark object the tuned scene interactions\n                should be on.\n                ', filter_prefixes=('func',)), value_name='scene_interactions', value_type=TunableSet(description='\n                The set of interactions that will be added to the stage mark\n                object.\n                ', tunable=TunableReference(description='\n                    A Super Interaction that should be added to the stage mark\n                    object.\n                    ', manager=services.affordance_manager(), class_restrictions='SuperInteraction')), tuning_group=GroupNames.CAREER), 'performance_objects': TunableMapping(description='\n            A mapping of performance objects (i.e. lights, green screen, vfx\n            machine) and the state they should be put into when the performance\n            starts/stops.\n            ', key_name='performance_object_tag', key_type=TunableTag(description='\n                The tag for the performance object.\n                ', filter_prefixes=('func',)), value_name='performance_object_states', value_type=TunableTuple(description="\n                States that should be applied to the objects before, during, and\n                after the performance. If the object doesn't have the necessary\n                state then nothing will happen.\n                ", pre_performance_states=TunableSet(description='\n                    States to set on the object when the zone loads.\n                    ', tunable=TunableTuple(description='\n                        A state to set on an object as well as a perk that will\n                        skip setting the state.\n                        ', state_value=TunableReference(description='\n                            A state value to set on the object.\n                            ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)), skip_with_perk=OptionalTunable(description='\n                            If enabled, allows skipping this state change if the\n                            active Sim has a tuned perk.\n                            ', tunable=TunableReference(description="\n                                If the active Sim has this perk, this state won't be\n                                set on the tuned objects. For instance, if the Sim\n                                has the Established Name perk, they don't need to\n                                use the hair and makeup chair. This can prevent\n                                those objects from glowing in that case.\n                                ", manager=services.get_instance_manager(sims4.resources.Types.BUCKS_PERK))))), post_performance_states=TunableSet(description='\n                    States set on the object when the performance is over.\n                    ', tunable=TunableReference(description='\n                        A state value to set on the object.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',))), performance_states=TunableSet(description='\n                    States to set on the object when the performance starts.\n                    ', tunable=TunableReference(description='\n                        A state value to set on the object.\n                        ', manager=services.get_instance_manager(sims4.resources.Types.OBJECT_STATE), class_restrictions=('ObjectStateValue',)))), tuning_group=GroupNames.CAREER), 'start_performance_interaction': TunableReference(description='\n            A reference to the interaction that indicates the performance is\n            starting. This is what triggers all of the state changes in the\n            Performance Object tuning.\n            ', manager=services.affordance_manager(), class_restrictions='SuperInteraction', tuning_group=GroupNames.CAREER), 'lot_load_loot': TunableMapping(description='\n            A mapping of Object IDs and loots to apply to those objects when the\n            lot loads. This can be used for things like applying specific locks\n            to door.\n            ', key_name='object_tag', key_type=TunableTag(description='\n                All objects with this tag will have the tuned loot applied on\n                lot load..\n                ', filter_prefixes=('func',)), value_name='loot', value_type=TunableSet(description='\n                A set of loots to apply to all objects with the specified tag.\n                ', tunable=TunableVariant(description='\n                    A specific loot to apply.\n                    ', lock_door=LockDoor.TunableFactory())), tuning_group=GroupNames.CAREER), 'thats_a_wrap_audio': TunablePlayAudio(description='\n            The sound to play when the player has completed the performance and\n            the Post Performance Time To Wrap Callout time has passed.\n            '), 'post_performance_time_remaining': TunableTimeSpan(description="\n            This is how long the gig should last once the player completes the\n            final interaction. Regardless of how long the timer shows, once the\n            player finishes the final interaction, we'll set the gig to end in\n            this tuned amount of time.\n            \n            Note: This should be enough time to encompass both the Post\n            Performance Time To Wrap Callout and Post Performance time Between\n            Wrap And Lights time spans.\n            ", default_minutes=20, locked_args={'days': 0}), 'post_performance_time_to_wrap_callout': TunableTimeSpan(description='\n            How long, after the Player completes the entire gig, until the\n            "That\'s a wrap" sound should play.\n            ', default_minutes=5, locked_args={'days': 0, 'hours': 0}), 'post_performance_time_between_wrap_and_lights': TunableTimeSpan(description='\n            How long after the "that\'s a wrap" sound until the post-performance\n            state should be swapped on all the objects (lights, greenscreen,\n            etc.)\n            ', default_minutes=5, locked_args={'days': 0, 'hours': 0})}
    ACTING_STUDIO_EVENTS = (TestEvent.InteractionComplete, TestEvent.MainSituationGoalComplete)
    STATE_PRE_PERFORMANCE = 0
    STATE_PERFORMANCE = 1
    STATE_POST_PERFORMANCE = 2
    SAVE_DATA_STATE = 'acting_studio_state'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._reset_data()

    def _reset_data(self):
        self._stage_marks = set()
        self._performance_object_data = []
        self._post_performance_state_alarm = None
        self._post_performance_call_out_alarm = None
        self._current_state = self.STATE_PRE_PERFORMANCE

    def on_startup(self):
        super().on_startup()
        services.get_event_manager().register(self, self.ACTING_STUDIO_EVENTS)

    def on_cleanup_zone_objects(self):
        object_manager = services.object_manager()
        self._init_stage_marks(object_manager)
        self._init_performance_object_data(object_manager)
        self._apply_lot_load_loot(object_manager)

    def _apply_lot_load_loot(self, object_manager):
        active_sim_info = services.active_sim_info()
        for (tag, loots) in self.lot_load_loot.items():
            objects = object_manager.get_objects_matching_tags((tag,))
            for obj in objects:
                resolver = SingleActorAndObjectResolver(active_sim_info, obj, source=self)
                for loot in loots:
                    loot.apply_to_resolver(resolver)

    def on_shutdown(self):
        super().on_shutdown()
        services.get_event_manager().unregister(self, self.ACTING_STUDIO_EVENTS)
        self._reset_data()

    def on_career_event_stop(self):
        services.get_event_manager().unregister(self, self.ACTING_STUDIO_EVENTS)

    def handle_event(self, sim_info, event, resolver):
        career = services.get_career_service().get_career_in_career_event()
        if career.sim_info is not sim_info:
            return
        if event == TestEvent.InteractionComplete and isinstance(resolver.interaction, self.start_performance_interaction) and not resolver.interaction.has_been_reset:
            self._start_performance()
        elif event == TestEvent.MainSituationGoalComplete:
            self._end_performance(career)

    def _save_custom_zone_director(self, zone_director_proto, writer):
        writer.write_uint32(self.SAVE_DATA_STATE, self._current_state)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        if reader is not None:
            self._current_state = reader.read_uint32(self.SAVE_DATA_STATE, self.STATE_PRE_PERFORMANCE)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _start_performance(self):
        for performance_object_data in self._performance_object_data:
            performance_object_data.set_performance_states()
        self._current_state = self.STATE_PERFORMANCE

    def _end_performance(self, career):
        new_end_time = services.time_service().sim_now + self.post_performance_time_remaining()
        career.set_career_end_time(new_end_time, reset_warning_alarm=False)
        self._post_performance_state_alarm = alarms.add_alarm(self, self.post_performance_time_to_wrap_callout(), self._post_performance_wrap_callout)
        self._current_state = self.STATE_POST_PERFORMANCE

    def _post_performance_wrap_callout(self, _):
        play_tunable_audio(self.thats_a_wrap_audio)
        self._post_performance_state_alarm = alarms.add_alarm(self, self.post_performance_time_between_wrap_and_lights(), self._post_performance_state_change)

    def _post_performance_state_change(self, _):
        for performance_object_data in self._performance_object_data:
            performance_object_data.set_post_performance_states()
        self._post_performance_state_alarm = None

    def _init_stage_marks(self, object_manager):
        for (tag, interactions) in self.stage_marks.items():
            marks = object_manager.get_objects_matching_tags((tag,))
            if not marks:
                pass
            else:
                self._stage_marks.update(marks)
                for obj in marks:
                    obj.add_dynamic_component(types.STAGE_MARK_COMPONENT, performance_interactions=interactions)

    def _init_performance_object_data(self, object_manager):
        for (tag, states) in self.performance_objects.items():
            performance_objects = object_manager.get_objects_matching_tags((tag,))
            if not performance_objects:
                pass
            else:
                performance_object_data = PerformanceObjectData(performance_objects, states.pre_performance_states, states.performance_states, states.post_performance_states)
                self._performance_object_data.append(performance_object_data)
                if self._current_state == self.STATE_PRE_PERFORMANCE:
                    performance_object_data.set_pre_performance_states()
