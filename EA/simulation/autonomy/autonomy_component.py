import randomfrom autonomy.autonomy_gsi_enums import GSIDataKeysfrom autonomy.autonomy_liabilities import AutonomousGetComfortableLiabilityfrom autonomy.autonomy_modes import FullAutonomy, AutonomyMode, SubActionAutonomy, PrerollAutonomyfrom autonomy.autonomy_request import AutonomyRequest, AutonomyDistanceEstimationBehavior, PrerollAutonomyRequestfrom autonomy.settings import AutonomySettings, AutonomySettingsGroupfrom buffs.tunable import TunableBuffReferencefrom date_and_time import DateAndTime, TimeSpan, create_time_spanfrom event_testing.results import EnqueueResultfrom interactions.aop import AffordanceObjectPairfrom interactions.context import InteractionSource, InteractionContextfrom interactions.priority import Priorityfrom objects.components import Component, componentmethodfrom objects.components.types import AUTONOMY_COMPONENTfrom postures import DerailReasonfrom role.role_tracker import RoleStateTrackerfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableSet, TunableReference, TunableSimMinute, TunableRange, TunableTuple, Tunable, TunableList, TunableMapping, TunableEnumEntry, OptionalTunablefrom singletons import UNSETfrom tunable_time import TunableTimeOfDayimport alarmsimport autonomy.autonomy_modifierimport cachesimport clockimport date_and_timeimport elementsimport gsi_handlersimport servicesimport sims4.loglogger = sims4.log.Logger('Autonomy')
class AutonomyComponent(Component, HasTunableFactory, AutoFactoryInit, component_name=AUTONOMY_COMPONENT):
    _STORE_AUTONOMY_REQUEST_HISTORY = False

    class TunableSleepSchedule(TunableTuple):

        def __init__(self, *args, **kwargs):
            super().__init__(*args, schedule=TunableList(tunable=TunableTuple(description="\n                        Define a Sim's sleep pattern by applying buffs at\n                        certain times before their scheduled work time. If Sim's\n                        don't have a job, define an arbitrary time and define\n                        buffs relative to that.\n                        ", time_from_work_start=Tunable(description='\n                            The time relative to the start work time that the buff\n                            should be added. For example, if you want the Sim to\n                            gain this static commodity 10 hours before work, set\n                            this value to 10.\n                            ', tunable_type=float, default=0), buff=TunableBuffReference(description='\n                            Buff that gets added to the Sim.\n                            ', allow_none=True))), default_work_time=TunableTimeOfDay(description="\n                    The default time that the Sim assumes he needs to be at work\n                    if he doesn't have a career. This is only used for sleep.\n                    ", default_hour=9), **kwargs)

    FACTORY_TUNABLES = {'initial_delay': TunableSimMinute(description='\n            How long to wait, in Sim minutes, before running autonomy for the\n            first time.\n            ', default=5), 'mixer_interaction_cache_size': TunableRange(description='\n            The number of mixes to cache during a subaction autonomy request.\n            ', tunable_type=int, default=3, minimum=1), 'standard_static_commodity_skip_set': TunableSet(description='\n            A set of static commodities. Any affordances that provide these\n            commodities will be skipped in a standard autonomy run.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.STATIC_COMMODITY))), 'preroll_affordance_skip_set': TunableSet(description='\n            A set of affordances to skip when preroll autonomy is run.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.INTERACTION), pack_safe=True)), 'sleep_schedule': TunableTuple(description='\n            Define when Sims are supposed to sleep.\n            ', default_schedule=TunableSleepSchedule(description="\n                The Sim's default sleep schedule.\n                "), trait_overrides=TunableMapping(description="\n                If necessary, override sleep patterns based on a Sim's trait. For\n                example, elders might have different patterns than other Sims.\n                \n                Tune these in priority order. The first trait to be encountered\n                determines the pattern.\n                ", key_type=TunableReference(manager=services.get_instance_manager(Types.TRAIT), pack_safe=True), value_type=TunableSleepSchedule())), '_settings_group': TunableEnumEntry(description='\n            Define which settings apply to this Sim.\n            ', tunable_type=AutonomySettingsGroup, default=AutonomySettingsGroup.DEFAULT), 'get_comfortable': OptionalTunable(description='\n            If enabled, the Sim will attempt to run this interaction whenever\n            their autonomy bucket is empty, provided this interaction is\n            compatible with what they are already running.\n            ', tunable=TunableTuple(affordance=TunableReference(description='\n                    The "Get Comfortable" super interaction.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions=('SuperInteraction',)), delay=TunableSimMinute(description='\n                    How long the Sim waits before executing the "Get\n                    Comfortable" interaction. This allows for other interactions\n                    to execute and interrupt this.\n                    ', default=4)))}

    def __init__(self, owner, *args, **kwargs):
        super().__init__(owner, *args, **kwargs)
        self._last_user_directed_action_time = None
        self._last_autonomous_action_time = DateAndTime(0)
        self._last_no_result_time = None
        self._autonomy_skip_sis = set()
        self._autonomy_enabled = False
        self._full_autonomy_alarm_handle = None
        self._get_comfortable_alarm_handle = None
        self._multitasking_roll = UNSET
        self._role_tracker = RoleStateTracker(owner)
        self._full_autonomy_request = None
        self._full_autonomy_element_handle = None
        self._autonomy_anchor = None
        self._sleep_buff_handle = None
        self._sleep_buff_alarms = {}
        self._sleep_buff_reset = None
        self._autonomy_settings = AutonomySettings()
        self._cached_mixer_interactions = []
        self._queued_autonomy_request = None

    def on_add(self):
        self.owner.si_state.on_changed.append(self.reset_multitasking_roll)
        self.owner.si_state.on_changed.append(self.invalidate_mixer_interaction_cache)

    def on_remove(self):
        for alarm_handle in self._sleep_buff_alarms.keys():
            alarms.cancel_alarm(alarm_handle)
        if self._full_autonomy_request is not None:
            self._full_autonomy_request.valid = False
            self._full_autonomy_request = None
        if self._sleep_buff_reset is not None:
            alarms.cancel_alarm(self._sleep_buff_reset)
        self.owner.si_state.on_changed.remove(self.invalidate_mixer_interaction_cache)
        self.owner.si_state.on_changed.remove(self.reset_multitasking_roll)
        self.on_sim_reset(True)
        self._role_tracker.shutdown()

    @componentmethod
    def get_autonomy_settings_group(self):
        return self._settings_group

    @componentmethod
    def queue_autonomy_request(self, request):
        if request is None:
            logger.error('Attempting to queue up a None autonomy request.')
            return
        self._queued_autonomy_request = request

    def _on_run_full_autonomy_callback(self, handle):
        if self._full_autonomy_element_handle is not None:
            return
        timeline = services.time_service().sim_timeline
        self._full_autonomy_element_handle = timeline.schedule(elements.GeneratorElement(self._run_full_autonomy_callback_gen))

    def _run_full_autonomy_callback_gen(self, timeline):
        try:
            self.set_last_autonomous_action_time(False)
            autonomy_pushed_interaction = yield from self._attempt_full_autonomy_gen(timeline)
            self._last_autonomy_result_was_none = not autonomy_pushed_interaction
        except Exception:
            logger.exception('Exception hit while processing FullAutonomy for {}:', self.owner, owner='rez')
        finally:
            self._full_autonomy_element_handle = None
            self._schedule_next_full_autonomy_update()

    def _attempt_full_autonomy_gen(self, timeline):
        if self._full_autonomy_request is not None and self._full_autonomy_request.valid:
            logger.debug('Ignoring full autonomy request for {} due to pending request in the queue.', self.owner)
            return False
        if self.to_skip_autonomy():
            if gsi_handlers.autonomy_handlers.archiver.enabled:
                gsi_handlers.autonomy_handlers.archive_autonomy_data(self.owner, 'None - Running SIs are preventing autonomy from running: {}'.format(self._autonomy_skip_sis), 'FullAutonomy', None)
            return False
        if not self._test_full_autonomy():
            return False
        try:
            selected_interaction = None
            try:
                if self._queued_autonomy_request is not None:
                    self._full_autonomy_request = self._queued_autonomy_request
                    self._queued_autonomy_request = None
                else:
                    self._full_autonomy_request = self._create_autonomy_request()
                selected_interaction = yield from services.autonomy_service().find_best_action_gen(timeline, self._full_autonomy_request, archive_if_enabled=False)
            finally:
                self._full_autonomy_request.valid = False
            if not self._autonomy_enabled:
                if gsi_handlers.autonomy_handlers.archiver.enabled:
                    gsi_handlers.autonomy_handlers.archive_autonomy_data(self.owner, 'None - Autonomy Disabled', 'FullAutonomy', None)
                return False
            if not self._test_full_autonomy():
                if selected_interaction:
                    selected_interaction.invalidate()
                return False
            if selected_interaction is not None:
                if selected_interaction.transition is not None and (self.owner.routing_master is not None and self.owner.routing_master.is_sim) and self.owner.routing_master.transition_controller is not None:
                    selected_interaction.transition.derail(DerailReason.PREEMPTED, self.owner)
                result = self._push_interaction(selected_interaction)
                if result or gsi_handlers.autonomy_handlers.archiver.enabled:
                    gsi_handlers.autonomy_handlers.archive_autonomy_data(self.owner, 'Failed - interaction failed to be pushed {}.'.format(selected_interaction), 'FullAutonomy', None)
                if result:
                    if gsi_handlers.autonomy_handlers.archiver.enabled:
                        gsi_handlers.autonomy_handlers.archive_autonomy_data(self._full_autonomy_request.sim, selected_interaction, self._full_autonomy_request.autonomy_mode_label, self._full_autonomy_request.gsi_data)
                        self._full_autonomy_request.gsi_data = None
                    return True
            elif gsi_handlers.autonomy_handlers.archiver.enabled:
                gsi_handlers.autonomy_handlers.archive_autonomy_data(self._full_autonomy_request.sim, 'None', self._full_autonomy_request.autonomy_mode_label, self._full_autonomy_request.gsi_data)
                self._full_autonomy_request.gsi_data = None
            return False
        finally:
            if selected_interaction is not None:
                selected_interaction.invalidate()
            self._full_autonomy_request = None

    def _test_full_autonomy(self):
        result = FullAutonomy.test(self.owner)
        if not result:
            if gsi_handlers.autonomy_handlers.archiver.enabled:
                gsi_handlers.autonomy_handlers.archive_autonomy_data(self.owner, result.reason, 'FullAutonomy', None)
            return False
        return True

    @componentmethod
    def run_test_autonomy_ping(self, affordance_list=None, commodity_list=None):
        autonomy_request = AutonomyRequest(self.owner, autonomy_mode=FullAutonomy, commodity_list=commodity_list, affordance_list=affordance_list, skipped_static_commodities=self.standard_static_commodity_skip_set, limited_autonomy_allowed=False)
        selected_interaction = services.autonomy_service().find_best_action(autonomy_request)
        return selected_interaction

    @componentmethod
    def cancel_actively_running_full_autonomy_request(self):
        if self._full_autonomy_element_handle is not None:
            self._full_autonomy_element_handle.trigger_hard_stop()
            self._full_autonomy_element_handle = None

    @caches.cached
    def is_object_autonomously_available(self, obj, interaction):
        autonomy_rule = self.owner.get_off_lot_autonomy_rule()
        if interaction.context.pick is not None:
            delta = obj.position - interaction.context.pick.location
            if delta.magnitude() <= autonomy_rule.radius:
                return True
        return self.get_autonomous_availability_of_object(obj, autonomy_rule)

    def get_autonomous_availability_of_object(self, obj, autonomy_rule, reference_object=None):
        reference_object = self.owner if reference_object is None else reference_object
        autonomy_type = autonomy_rule.rule
        off_lot_radius = autonomy_rule.radius
        tolerance = autonomy_rule.tolerance
        anchor_tag = autonomy_rule.anchor_tag
        anchor_buff = autonomy_rule.anchor_buff
        if obj is self.owner:
            return True
        if self.owner.locked_from_obj_by_privacy(obj):
            return False
        if autonomy_type == autonomy.autonomy_modifier.OffLotAutonomyRules.UNLIMITED:
            return True
        if obj.is_sim:
            autonomy_service = services.autonomy_service()
            target_delta = obj.intended_position - obj.position
            if target_delta.magnitude() > autonomy_service.MAX_OPEN_STREET_ROUTE_DISTANCE_FOR_SOCIAL_TARGET:
                return False
            if not obj.is_on_active_lot(tolerance=tolerance):
                distance_from_me = obj.intended_position - self.owner.intended_position
                if distance_from_me.magnitude() > autonomy_service.MAX_OPEN_STREET_ROUTE_DISTANCE_FOR_INITIATING_SOCIAL:
                    return False
        if self.owner.object_tags_override_off_lot_autonomy_ref_count(obj.get_tags()):
            return True
        if autonomy_type == autonomy.autonomy_modifier.OffLotAutonomyRules.RESTRICTED:
            zone = services.current_zone()
            return zone.is_point_in_restricted_autonomy_area(obj.position)
        if autonomy_type == autonomy.autonomy_modifier.OffLotAutonomyRules.ANCHORED:
            obj_intended_postion = obj.intended_position
            obj_level = obj.level

            def is_close_by(position, level):
                if level is UNSET or level == obj_level:
                    delta = obj_intended_postion - position
                    if delta.magnitude() <= off_lot_radius:
                        return True
                return False

            candidates_exist = False
            if self._autonomy_anchor is not None:
                candidates_exist = True
                if is_close_by(*self._autonomy_anchor):
                    return True
            for anchor in services.object_manager().get_objects_with_tag_gen(anchor_tag):
                candidates_exist = True
                if is_close_by(anchor.intended_position, anchor.level):
                    return True
            if anchor_buff is not None:
                for sim in services.sim_info_manager().instanced_sims_gen():
                    if sim.Buffs.has_buff(anchor_buff.buff_type):
                        candidates_exist = True
                        if is_close_by(sim.intended_position, sim.level):
                            return True
            if candidates_exist:
                return False
            logger.warn('Off-lot autonomy rule is ANCHORED, but there was no anchor set for {} or no objects found with anchor tag: {} or anchor buff: {}. Reverting to default behavior.', self.owner, anchor_tag, anchor_buff)
            autonomy_type = autonomy.autonomy_modifier.OffLotAutonomyRules.DEFAULT
        if autonomy_type == autonomy.autonomy_modifier.OffLotAutonomyRules.DEFAULT:
            reference_object_on_active_lot = reference_object.is_on_active_lot(tolerance=tolerance)
            if reference_object_on_active_lot and obj.is_on_active_lot(tolerance=tolerance):
                return True
            reference_object_on_active_lot = reference_object.is_on_active_lot()
            if reference_object_on_active_lot:
                return False
            delta = obj.position - reference_object.position
            return delta.magnitude() <= off_lot_radius
        if obj.is_on_active_lot(tolerance=tolerance):
            return autonomy_type == autonomy.autonomy_modifier.OffLotAutonomyRules.ON_LOT_ONLY
        else:
            delta = obj.position - reference_object.position
            return delta.magnitude() <= off_lot_radius

    def _create_autonomy_request(self):
        autonomy_request = AutonomyRequest(self.owner, autonomy_mode=FullAutonomy, skipped_static_commodities=self.standard_static_commodity_skip_set, limited_autonomy_allowed=False)
        return autonomy_request

    def _push_interaction(self, selected_interaction):
        if AffordanceObjectPair.execute_interaction(selected_interaction):
            if self.get_comfortable is not None:
                get_comfortable_liability = AutonomousGetComfortableLiability(self.owner)
                selected_interaction.add_liability(AutonomousGetComfortableLiability.LIABILITY_TOKEN, get_comfortable_liability)
            return True
        should_log = services.autonomy_service().should_log(self.owner)
        if should_log:
            logger.debug('Autonomy failed to push {}', selected_interaction.affordance)
        if selected_interaction.target:
            self.owner.add_lockout(selected_interaction.target, AutonomyMode.LOCKOUT_TIME)
        return False

    def _schedule_next_full_autonomy_update(self, delay_in_sim_minutes=None):
        if not self._autonomy_enabled:
            return
        try:
            if delay_in_sim_minutes is None:
                delay_in_sim_minutes = self.get_time_until_next_update()
            logger.assert_log(isinstance(delay_in_sim_minutes, TimeSpan), 'delay_in_sim_minutes is not a TimeSpan object in _schedule_next_full_autonomy_update()', owner='rez')
            logger.debug('Scheduling next autonomy update for {} for {}', self.owner, delay_in_sim_minutes)
            self._create_full_autonomy_alarm(delay_in_sim_minutes)
        except Exception:
            logger.exception('Exception hit while attempting to schedule FullAutonomy for {}:', self.owner)

    def start_autonomy_alarm(self):
        self._autonomy_enabled = True
        self._schedule_next_full_autonomy_update(clock.interval_in_sim_minutes(self.initial_delay))

    def _create_full_autonomy_alarm(self, time_until_trigger):
        if self._full_autonomy_alarm_handle is not None:
            self._destroy_full_autonomy_alarm()
        if time_until_trigger.in_ticks() <= 0:
            time_until_trigger = TimeSpan(1)
        self._full_autonomy_alarm_handle = alarms.add_alarm(self, time_until_trigger, self._on_run_full_autonomy_callback, use_sleep_time=False)

    def get_time_until_ping(self):
        if self._full_autonomy_alarm_handle is not None:
            return self._full_autonomy_alarm_handle.get_remaining_time()

    def _destroy_full_autonomy_alarm(self):
        if self._full_autonomy_alarm_handle is not None:
            alarms.cancel_alarm(self._full_autonomy_alarm_handle)
            self._full_autonomy_alarm_handle = None

    @componentmethod
    def get_multitasking_roll(self):
        if self._multitasking_roll is UNSET:
            self._multitasking_roll = random.random()
        return self._multitasking_roll

    @componentmethod
    def reset_multitasking_roll(self, interaction=None):
        if interaction is None or (interaction.source is InteractionSource.PIE_MENU or interaction.source is InteractionSource.AUTONOMY) or interaction.source is InteractionSource.SCRIPT:
            self._multitasking_roll = UNSET

    @componentmethod
    def set_anchor(self, anchor):
        self._autonomy_anchor = anchor

    @componentmethod
    def clear_anchor(self):
        self._autonomy_anchor = None

    @componentmethod
    def push_get_comfortable_interaction(self):
        if self.get_comfortable is None:
            return False
        if self._get_comfortable_alarm_handle is not None:
            return False

        def _push_get_comfortable_interaction(_):
            self._get_comfortable_alarm_handle = None
            if any(si.is_guaranteed() for si in self.owner.si_state):
                return
            context = InteractionContext(self.owner, InteractionSource.AUTONOMY, Priority.Low)
            self.owner.push_super_affordance(self.get_comfortable.affordance, None, context)

        self._get_comfortable_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.get_comfortable.delay), _push_get_comfortable_interaction)

    def _destroy_get_comfortable_alarm(self):
        if self._get_comfortable_alarm_handle is not None:
            self._get_comfortable_alarm_handle.cancel()
            self._get_comfortable_alarm_handle = None

    @componentmethod
    def on_sim_reset(self, is_kill):
        self.invalidate_mixer_interaction_cache(None)
        if self._full_autonomy_request is not None:
            self._full_autonomy_request.valid = False
        if is_kill:
            self._autonomy_enabled = False
            self._destroy_full_autonomy_alarm()
        self._destroy_get_comfortable_alarm()
        if self._full_autonomy_element_handle is not None:
            self._full_autonomy_element_handle.trigger_hard_stop()
            self._full_autonomy_element_handle = None

    @componentmethod
    def run_full_autonomy_next_ping(self):
        self._last_user_directed_action_time = None
        self._schedule_next_full_autonomy_update(TimeSpan(1))

    @componentmethod
    def set_last_user_directed_action_time(self, to_reschedule_autonomy=True):
        now = services.time_service().sim_now
        logger.debug('Setting user-directed action time for {} to {}', self.owner, now)
        self._last_user_directed_action_time = now
        self._last_autonomy_result_was_none = False
        if to_reschedule_autonomy:
            self._schedule_next_full_autonomy_update()

    @componentmethod
    def set_last_autonomous_action_time(self, to_reschedule_autonomy=True):
        now = services.time_service().sim_now
        logger.debug('Setting last autonomous action time for {} to {}', self.owner, now)
        self._last_autonomous_action_time = now
        self._last_autonomy_result_was_none = False
        if to_reschedule_autonomy:
            self._schedule_next_full_autonomy_update()

    @componentmethod
    def set_last_no_result_time(self, to_reschedule_autonomy=True):
        now = services.time_service().sim_now
        logger.debug('Setting last no-result time for {} to {}', self.owner, now)
        self._last_no_result_time = now
        if to_reschedule_autonomy:
            self._schedule_next_full_autonomy_update()

    @componentmethod
    def skip_autonomy(self, si, to_skip):
        if si.source == InteractionSource.BODY_CANCEL_AOP or si.source == InteractionSource.CARRY_CANCEL_AOP or si.source == InteractionSource.SOCIAL_ADJUSTMENT:
            return
        if to_skip:
            logger.debug('Skipping autonomy for {} due to {}', self.owner, si)
            self._autonomy_skip_sis.add(si)
        else:
            if si in self._autonomy_skip_sis:
                self._autonomy_skip_sis.remove(si)
            logger.debug('Unskipping autonomy for {} due to {}; {} is left.', self.owner, si, self._autonomy_skip_sis)

    def _get_last_user_directed_action_time(self):
        return self._last_user_directed_action_time

    def _get_last_autonomous_action_time(self):
        return self._last_autonomous_action_time

    def _get_last_no_result_time(self):
        return self._last_no_result_time

    @property
    def _last_autonomy_result_was_none(self):
        return self._last_no_result_time is not None

    @_last_autonomy_result_was_none.setter
    def _last_autonomy_result_was_none(self, value:bool):
        if value == True:
            self.set_last_no_result_time(to_reschedule_autonomy=False)
        else:
            self._last_no_result_time = None

    @componentmethod
    def to_skip_autonomy(self):
        return bool(self._autonomy_skip_sis)

    @componentmethod
    def clear_all_autonomy_skip_sis(self):
        self._autonomy_skip_sis.clear()

    @componentmethod
    def is_player_active(self):
        if self._get_last_user_directed_action_time() is None:
            return False
        else:
            delta = services.time_service().sim_now - self._get_last_user_directed_action_time()
            if delta >= AutonomyMode.get_autonomy_delay_after_user_interaction():
                return False
        return True

    @componentmethod
    def get_time_until_next_update(self, mode=FullAutonomy):
        time_to_run_autonomy = None
        if self.is_player_active():
            time_to_run_autonomy = self._get_last_user_directed_action_time() + mode.get_autonomy_delay_after_user_interaction()
        elif self._last_autonomy_result_was_none:
            time_to_run_autonomy = self._get_last_no_result_time() + mode.get_no_result_delay_time()
        elif self.owner.has_any_pending_or_running_interactions():
            time_to_run_autonomy = self._get_last_autonomous_action_time() + mode.get_autonomous_delay_time()
        else:
            time_to_run_autonomy = self._get_last_autonomous_action_time() + mode.get_autonomous_update_delay_with_no_primary_sis()
        delta_time = time_to_run_autonomy - services.time_service().sim_now
        if delta_time.in_ticks() <= 0:
            delta_time = TimeSpan(1)
        return delta_time

    @componentmethod
    def run_preroll_autonomy(self, ignored_objects):
        sim = self.owner
        sim_info = sim.sim_info
        for (_, modifier) in sim_info.get_statistic_modifiers_gen():
            if modifier.autonomy_modifier.suppress_preroll_autonomy:
                return (None, None)
        if self._queued_autonomy_request is not None:
            autonomy_request = self._queued_autonomy_request
            self._queued_autonomy_request = None
        else:
            current_away_action = sim_info.current_away_action
            if current_away_action is not None:
                commodity_list = current_away_action.get_commodity_preroll_list()
                static_commodity_list = current_away_action.get_static_commodity_preroll_list()
            else:
                commodity_list = None
                static_commodity_list = None
            autonomy_request = PrerollAutonomyRequest(self.owner, autonomy_mode=PrerollAutonomy, commodity_list=commodity_list, static_commodity_list=static_commodity_list, distance_estimation_behavior=AutonomyDistanceEstimationBehavior.IGNORE_DISTANCE, ignored_object_list=ignored_objects, limited_autonomy_allowed=False, autonomy_mode_label_override='PrerollAutonomy')
        selected_interaction = services.autonomy_service().find_best_action(autonomy_request)
        if selected_interaction is None:
            return (None, None)
        elif self._push_interaction(selected_interaction):
            return (selected_interaction.affordance, selected_interaction.target)
        return (None, None)

    @componentmethod
    def invalidate_mixer_interaction_cache(self, si):
        if si is not None and not si.visible:
            return
        if autonomy.autonomy_util.info_start_time is not None:
            sub_action_ping_data = autonomy.autonomy_util.sim_id_to_sub_autonomy_ping.get(self.owner.id, None)
            if sub_action_ping_data is not None:
                sub_action_ping_data.mixers_cleared += len(self._cached_mixer_interactions)
        for interaction in self._cached_mixer_interactions:
            interaction.invalidate()
        self._cached_mixer_interactions.clear()

    def _should_run_cached_interaction(self, interaction_to_run):
        if interaction_to_run is None:
            return False
        super_interaction = interaction_to_run.super_interaction
        if super_interaction is None or super_interaction.is_finishing:
            return False
        if super_interaction.phase_index is not None and interaction_to_run.affordance not in super_interaction.all_affordances_gen(phase_index=super_interaction.phase_index):
            return False
        if interaction_to_run.is_finishing:
            return False
        if self.owner.is_sub_action_locked_out(interaction_to_run.affordance, interaction_to_run.target):
            return False
        return interaction_to_run.test()

    def _get_number_mixers_cache(self):
        additional_mixers_to_cache = sum(si.additional_mixers_to_cache() for si in self.owner.si_state if not si.is_finishing)
        return self.mixer_interaction_cache_size + additional_mixers_to_cache

    @componentmethod
    def run_subaction_autonomy(self):
        if not SubActionAutonomy.test(self.owner):
            if gsi_handlers.autonomy_handlers.archiver.enabled:
                gsi_handlers.autonomy_handlers.archive_autonomy_data(self.owner, 'None - Autonomy Disabled', 'SubActionAutonomy', gsi_handlers.autonomy_handlers.EMPTY_ARCHIVE)
            return EnqueueResult.NONE
        attempt_to_use_cache = False
        if gsi_handlers.autonomy_handlers.archiver.enabled:
            caching_info = []
        else:
            caching_info = None
        sub_action_ping_data = None
        if autonomy.autonomy_util.info_start_time is not None:
            sub_action_ping_data = autonomy.autonomy_util.sim_id_to_sub_autonomy_ping.get(self.owner.id, None)
        while self._cached_mixer_interactions:
            attempt_to_use_cache = True
            interaction_to_run = self._cached_mixer_interactions.pop(0)
            if self._should_run_cached_interaction(interaction_to_run):
                enqueue_result = AffordanceObjectPair.execute_interaction(interaction_to_run)
                if enqueue_result:
                    if gsi_handlers.autonomy_handlers.archiver.enabled:
                        gsi_handlers.autonomy_handlers.archive_autonomy_data(self.owner, 'Using Cache: {}'.format(interaction_to_run), 'SubActionAutonomy', gsi_handlers.autonomy_handlers.EMPTY_ARCHIVE)
                    if sub_action_ping_data is not None:
                        sub_action_ping_data.cache_hits += 1
                    return enqueue_result
            if interaction_to_run:
                interaction_to_run.invalidate()
            if caching_info is not None:
                caching_info.append('Failed to use cache interaction: {}'.format(interaction_to_run))
            if sub_action_ping_data is not None:
                sub_action_ping_data.cache_use_fails += 1
        if caching_info is not None and attempt_to_use_cache:
            caching_info.append('Cache invalid:Regenerating')
        self.invalidate_mixer_interaction_cache(None)
        context = InteractionContext(self.owner, InteractionSource.AUTONOMY, Priority.Low)
        autonomy_request = AutonomyRequest(self.owner, context=context, consider_scores_of_zero=True, skipped_affordance_list=[], autonomy_mode=SubActionAutonomy)
        if caching_info is not None:
            caching_info.append('Caching: Mixers - START')
        mixers_to_cache = self._get_number_mixers_cache()
        initial_probability_result = None
        while len(self._cached_mixer_interactions) < mixers_to_cache:
            interaction = services.autonomy_service().find_best_action(autonomy_request, consider_all_options=True, archive_if_enabled=False)
            if interaction is None:
                break
            if caching_info is not None:
                caching_info.append('caching interaction: {}'.format(interaction))
                if initial_probability_result is None:
                    initial_probability_result = list(autonomy_request.gsi_data[GSIDataKeys.PROBABILITY_KEY])
            self._cached_mixer_interactions.append(interaction)
            autonomy_request.skipped_affordance_list.clear()
            autonomy_request.skip_adding_request_record = True
            if interaction.lock_out_time is not None and not interaction.lock_out_time.target_based_lock_out:
                autonomy_request.skipped_affordance_list.append(interaction.affordance)
        if caching_info is not None:
            caching_info.append('Caching: Mixers - DONE')
        if autonomy.autonomy_util.info_start_time is not None:
            if sub_action_ping_data is None:
                sub_action_ping_data = autonomy.autonomy_util.SubAutonomyPingData()
            sub_action_ping_data.num_mixers_cached.append((len(self._cached_mixer_interactions), mixers_to_cache))
        if self._cached_mixer_interactions:
            interaction = self._cached_mixer_interactions.pop(0)
            if caching_info is not None:
                caching_info.append('Executing mixer: {}'.format(interaction))
            enqueue_result = AffordanceObjectPair.execute_interaction(interaction)
            if caching_info is not None:
                autonomy_request.gsi_data[GSIDataKeys.MIXER_CACHING_INFO_KEY] = caching_info
                autonomy_request.gsi_data[GSIDataKeys.PROBABILITY_KEY] = initial_probability_result
                if enqueue_result:
                    result_info = str(interaction)
                else:
                    result_info = 'None - failed to execute: {}'.format(interaction)
                gsi_handlers.autonomy_handlers.archive_autonomy_data(autonomy_request.sim, result_info, autonomy_request.autonomy_mode_label, autonomy_request.gsi_data)
                autonomy_request.gsi_data = None
            if sub_action_ping_data is not None:
                sub_action_ping_data.cache_hits += 1
                autonomy.autonomy_util.sim_id_to_sub_autonomy_ping[self.owner.id] = sub_action_ping_data
            return enqueue_result
        else:
            return EnqueueResult.NONE

    @componentmethod
    def add_role(self, role_state_type, role_affordance_target=None, situation=None, **kwargs):
        for role_state in self._role_tracker:
            if isinstance(role_state, role_state_type):
                logger.error('Trying to add duplicate role:{}. Returning current instantiated role.', role_state_type)
                return role_state
        role_state = role_state_type(self.owner)
        self._role_tracker.add_role(role_state, role_affordance_target=role_affordance_target, situation=situation, **kwargs)
        return role_state

    @componentmethod
    def remove_role(self, role_state):
        return self._role_tracker.remove_role(role_state)

    @componentmethod
    def remove_role_of_type(self, role_state_type):
        for role_state_priority in self._role_tracker:
            for role_state in role_state_priority:
                if isinstance(role_state, role_state_type):
                    self.remove_role(role_state)
                    return True
        return False

    @componentmethod
    def active_roles(self):
        return self._role_tracker.active_role_states

    @componentmethod
    def reset_role_tracker(self):
        self._role_tracker.reset()

    def _get_sleep_schedule(self):
        for (trait, sleep_schedule) in self.sleep_schedule.trait_overrides.items():
            if self.owner.has_trait(trait):
                return sleep_schedule
        return self.sleep_schedule.default_schedule

    @componentmethod
    def update_sleep_schedule(self):
        self._remove_sleep_schedule_buff()
        for alarm_handle in self._sleep_buff_alarms.keys():
            alarms.cancel_alarm(alarm_handle)
        self._sleep_buff_alarms.clear()
        time_span_until_wakeup = self.get_time_until_next_wakeup()
        sleep_schedule = self._get_sleep_schedule()
        most_appropriate_buff = None
        for sleep_schedule_entry in sorted(sleep_schedule.schedule, key=lambda entry: entry.time_from_work_start, reverse=True):
            if time_span_until_wakeup.in_hours() <= sleep_schedule_entry.time_from_work_start:
                most_appropriate_buff = sleep_schedule_entry.buff
            else:
                time_until_buff_alarm = time_span_until_wakeup - create_time_span(hours=sleep_schedule_entry.time_from_work_start)
                alarm_handle = alarms.add_alarm(self, time_until_buff_alarm, self._add_buff_callback, True, create_time_span(hours=date_and_time.HOURS_PER_DAY))
                self._sleep_buff_alarms[alarm_handle] = sleep_schedule_entry.buff
        if most_appropriate_buff.buff_type:
            self._sleep_buff_handle = self.owner.add_buff(most_appropriate_buff.buff_type)
        if most_appropriate_buff and self._sleep_buff_reset:
            alarms.cancel_alarm(self._sleep_buff_reset)
        self._sleep_buff_reset = alarms.add_alarm(self, time_span_until_wakeup, self._reset_alarms_callback)

    @componentmethod
    def get_time_until_next_wakeup(self, offset_time:TimeSpan=None):
        now = services.time_service().sim_now
        time_span_until_wakeup = None
        sim_careers = self.owner.sim_info.careers
        if sim_careers:
            earliest_time = None
            for career in sim_careers.values():
                wakeup_time = career.get_next_wakeup_time()
                if not earliest_time is None:
                    if wakeup_time < earliest_time:
                        earliest_time = wakeup_time
                earliest_time = wakeup_time
            if earliest_time is not None:
                if offset_time is not None:
                    time_to_operate = now + offset_time
                else:
                    time_to_operate = now
                time_span_until_wakeup = time_to_operate.time_till_next_day_time(earliest_time)
        if time_span_until_wakeup is None:
            start_time = self._get_default_sleep_schedule_work_time(offset_time)
            time_span_until_wakeup = start_time - now
        if time_span_until_wakeup.in_ticks() <= 0:
            time_span_until_wakeup += TimeSpan(date_and_time.sim_ticks_per_day())
            logger.assert_log(time_span_until_wakeup.in_ticks() > 0, 'time_span_until_wakeup occurs in the past.')
        return time_span_until_wakeup

    def _add_buff_callback(self, alarm_handle):
        buff = self._sleep_buff_alarms.get(alarm_handle)
        if not buff:
            logger.error("Couldn't find alarm handle in _sleep_buff_alarms dict for sim:{}.", self.owner, owner='rez')
            return
        self._remove_sleep_schedule_buff()
        if buff.buff_type:
            self._sleep_buff_handle = self.owner.add_buff(buff.buff_type)

    def _reset_alarms_callback(self, _):
        self.update_sleep_schedule()

    def _remove_sleep_schedule_buff(self):
        if self._sleep_buff_handle is not None:
            self.owner.remove_buff(self._sleep_buff_handle)
            self._sleep_buff_handle = None

    def _get_default_sleep_schedule_work_time(self, offset_time):
        now = services.time_service().sim_now
        if offset_time is not None:
            now += offset_time
        sleep_schedule = self._get_sleep_schedule()
        work_time = date_and_time.create_date_and_time(days=int(now.absolute_days()), hours=sleep_schedule.default_work_time.hour(), minutes=sleep_schedule.default_work_time.minute())
        if work_time < now:
            work_time += date_and_time.create_time_span(days=1)
        return work_time

    @componentmethod
    def get_autonomy_state_setting(self) -> autonomy.settings.AutonomyState:
        return self._get_appropriate_autonomy_setting(autonomy.settings.AutonomyState)

    @componentmethod
    def get_autonomy_randomization_setting(self) -> autonomy.settings.AutonomyRandomization:
        return self._get_appropriate_autonomy_setting(autonomy.settings.AutonomyRandomization)

    @componentmethod
    def get_autonomy_settings(self):
        return self._autonomy_settings

    def _get_appropriate_autonomy_setting(self, setting_class):
        autonomy_service = services.autonomy_service()
        setting = autonomy_service.global_autonomy_settings.get_setting(setting_class, self.get_autonomy_settings_group())
        if setting != setting_class.UNDEFINED:
            return setting
        if self._role_tracker is not None:
            setting = self._role_tracker.get_autonomy_state()
            if setting != setting_class.UNDEFINED:
                return setting
        if services.current_zone().is_zone_running:
            tutorial_service = services.get_tutorial_service()
            if tutorial_service is not None and tutorial_service.is_tutorial_running():
                return autonomy.settings.AutonomyState.FULL
        setting = self._autonomy_settings.get_setting(setting_class, self.get_autonomy_settings_group())
        if setting != setting_class.UNDEFINED:
            return setting
        household = self.owner.household
        if household:
            setting = household.autonomy_settings.get_setting(setting_class, self.get_autonomy_settings_group())
            if setting != setting_class.UNDEFINED:
                return setting
        setting = autonomy_service.default_autonomy_settings.get_setting(setting_class, self.get_autonomy_settings_group())
        if setting == setting_class.UNDEFINED:
            logger.error('Sim {} has an UNDEFINED autonomy setting!', self.owner, owner='rez')
        return setting

    @componentmethod
    def debug_reset_autonomy_alarm(self):
        self._schedule_next_full_autonomy_update()

    @componentmethod
    def debug_output_autonomy_timers(self, _connection):
        now = services.time_service().sim_now
        if self._last_user_directed_action_time is not None:
            sims4.commands.output('Last User-Directed Action: {} ({} ago)'.format(self._last_user_directed_action_time, now - self._last_user_directed_action_time), _connection)
        else:
            sims4.commands.output('Last User-Directed Action: None', _connection)
        if self._last_autonomous_action_time is not None:
            sims4.commands.output('Last Autonomous Action: {} ({} ago)'.format(self._last_autonomous_action_time, now - self._last_autonomous_action_time), _connection)
        else:
            sims4.commands.output('Last Autonomous Action: None', _connection)
        if self._full_autonomy_alarm_handle is not None:
            sims4.commands.output('Full Autonomy: {} from now'.format(self._full_autonomy_alarm_handle.get_remaining_time()), _connection)
        else:
            sims4.commands.output('Full Autonomy: None)', _connection)
        if len(self._autonomy_skip_sis) > 0:
            sims4.commands.output("Skipping autonomy due to the follow SI's:", _connection)
            for si in self._autonomy_skip_sis:
                sims4.commands.output('\t{}'.format(si), _connection)
        else:
            sims4.commands.output('Not skipping autonomy', _connection)

    @componentmethod
    def debug_get_autonomy_timers_gen(self):
        now = services.time_service().sim_now
        if self._full_autonomy_alarm_handle is not None:
            yield ('Full Autonomy', '{}'.format(self._full_autonomy_alarm_handle.get_remaining_time()))
        else:
            yield ('Full Autonomy', 'None')
        if self._last_user_directed_action_time is not None:
            yield ('Last User-Directed Action', '{} ({} ago)'.format(self._last_user_directed_action_time, now - self._last_user_directed_action_time))
        if self._last_autonomous_action_time:
            yield ('Last Autonomous Action', '{} ({} ago)'.format(self._last_autonomous_action_time, now - self._last_autonomous_action_time))
        if len(self._autonomy_skip_sis) > 0:
            yield ('Skipping Autonomy?', 'True')
        else:
            yield ('Skipping Autonomy?', 'False')

    @componentmethod
    def debug_update_autonomy_timer(self, mode):
        self._schedule_next_full_autonomy_update()
