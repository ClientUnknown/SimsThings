import randomfrom away_actions.away_actions import AwayActionfrom careers.career_enums import CareerCategoryfrom careers.career_tuning import Careerfrom element_utils import build_critical_section_with_finallyfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.results import TestResultfrom fame.fame_tuning import FameTunablesfrom filters.tunable import TunableSimFilterfrom interactions.aop import AffordanceObjectPairfrom interactions.base.picker_interaction import PickerSingleChoiceSuperInteractionfrom interactions.base.super_interaction import SuperInteractionfrom interactions.utils.loot import LootActionsfrom interactions.utils.success_chance import SuccessChancefrom interactions.utils.tunable import TunableContinuationfrom objects.terrain import TerrainSuperInteractionfrom sims.sim_info_interactions import SimInfoInteractionfrom sims4.tuning.tunable import OptionalTunable, TunableList, Tunable, TunableVariant, TunableEnumSet, HasTunableSingletonFactory, AutoFactoryInit, TunableTuple, TunableRange, TunableReferencefrom sims4.tuning.tunable_base import GroupNamesfrom sims4.utils import flexmethodfrom statistics.commodity import RuntimeCommodity, CommodityTimePassageFixupTypefrom ui.ui_dialog_picker import ObjectPickerRowimport alarmsimport clockimport date_and_timeimport event_testingimport interactions.base.super_interactionimport interactions.rabbit_holeimport servicesimport sims4.tuning.tunableimport terrainlogger = sims4.log.Logger('Careers')with sims4.reload.protected(globals()):
    _force_fame_moment = False
def set_force_fame_moment(value):
    global _force_fame_moment
    _force_fame_moment = value

class CareerSuperInteraction(interactions.base.super_interaction.SuperInteraction):

    def __init__(self, aop, context, career_uid=None, **kwargs):
        super().__init__(aop, context, **kwargs)
        if career_uid is None:
            career = self.sim.sim_info.career_tracker.career_currently_within_hours
            if career is not None:
                career_uid = career.guid64
        self._career_uid = career_uid
        self._fame_moment_active = False

    @property
    def interaction_parameters(self):
        kwargs = super().interaction_parameters
        kwargs['career_uid'] = self._career_uid
        return kwargs

    @property
    def career_uid(self):
        return self._career_uid

    def get_career(self, career_id=None):
        return self.sim.sim_info.career_tracker.get_career_by_uid(self._career_uid)

    @classmethod
    def _test(cls, target, context, career_uid=None, skip_safe_tests=False, **kwargs):
        career = context.sim.sim_info.career_tracker.get_career_by_uid(career_uid)
        if career is None:
            career = context.sim.sim_info.career_tracker.career_currently_within_hours
        if career is None:
            return event_testing.results.TestResult(False, 'Sim({}) does not have career: {}.', context.sim, career_uid)
        if not career.is_work_time:
            return event_testing.results.TestResult(False, 'Not currently a work time for Sim({})', context.sim)
        return event_testing.results.TestResult.TRUE

    def on_added_to_queue(self, *args, **kwargs):
        self.add_liability(interactions.rabbit_hole.RABBIT_HOLE_LIABILTIY, interactions.rabbit_hole.RabbitHoleLiability(self))
        return super().on_added_to_queue(*args, **kwargs)

    def build_basic_elements(self, sequence=()):
        career = self.get_career()
        career_level = career.current_level_tuning()
        if career_level.fame_moment is not None and self._should_run_fame_moment(career, career_level):
            self._start_fame_moment(career, career_level.fame_moment)
        sequence = super().build_basic_elements(sequence=sequence)
        sequence = build_critical_section_with_finally(self.interaction_start, sequence, self.interaction_end)
        return sequence

    def _should_run_fame_moment(self, career, level):
        if career.fame_moment_completed:
            return False
        if _force_fame_moment:
            return True
        resolver = self.get_resolver()
        chance = level.fame_moment.chance_to_occur.get_chance(resolver)
        return random.random() <= chance

    def _start_fame_moment(self, career, fame_moment):
        self.add_additional_instance_basic_extra(fame_moment.moment)
        self.register_for_fame_moment_callback()
        self._fame_moment_active = True

    def interaction_start(self, _):
        career = self.get_career()
        if career is not None:
            career.attend_work(interaction=self)

    def interaction_end(self, _):
        if services.current_zone().is_zone_shutting_down:
            return
        career = self.get_career()
        if career is not None:
            career.leave_work(left_early=not self.is_finishing_naturally)
            self.unregister_for_fame_moment_callback()

    def register_for_fame_moment_callback(self):
        services.get_event_manager().register_single_event(self, FameTunables.FAME_MOMENT_EVENT)

    def unregister_for_fame_moment_callback(self):
        services.get_event_manager().unregister_single_event(self, FameTunables.FAME_MOMENT_EVENT)

    def handle_event(self, sim_info, event, resolver):
        if event == FameTunables.FAME_MOMENT_EVENT and self._sim.sim_info is sim_info:
            career = self.get_career()
            if career is not None:
                career.on_fame_moment_complete()

    @property
    def fame_moment_active(self):
        return self._fame_moment_active

class CareerPickerSuperInteraction(PickerSingleChoiceSuperInteraction):

    class CareerPickerFilter(HasTunableSingletonFactory, AutoFactoryInit):

        def is_valid(self, career):
            raise NotImplementedError

    class CareerPickerFilterAll(CareerPickerFilter):

        def is_valid(self, career):
            return True

    class CareerPickerFilterWhitelist(CareerPickerFilter):
        FACTORY_TUNABLES = {'whitelist': TunableEnumSet(description='\n                Only careers of this category are allowed. If this set is\n                empty, then no careers are allowed.\n                ', enum_type=CareerCategory)}

        def is_valid(self, career):
            return career.career_category in self.whitelist

    class CareerPickerFilterBlacklist(CareerPickerFilter):
        FACTORY_TUNABLES = {'blacklist': TunableEnumSet(description='\n                Careers of this category are not allowed. All others are\n                allowed.\n                ', enum_type=CareerCategory)}

        def is_valid(self, career):
            return career.career_category not in self.blacklist

    INSTANCE_TUNABLES = {'continuation': OptionalTunable(description='\n            If enabled, you can tune a continuation to be pushed. PickedItemId\n            will be the id of the selected career.\n            ', tunable=TunableContinuation(description='\n                If specified, a continuation to push with the chosen career.\n                '), tuning_group=GroupNames.PICKERTUNING), 'career_filter': TunableVariant(description='\n            Which career types to show.\n            ', all=CareerPickerFilterAll.TunableFactory(), blacklist=CareerPickerFilterBlacklist.TunableFactory(), whitelist=CareerPickerFilterWhitelist.TunableFactory(), default='all', tuning_group=GroupNames.PICKERTUNING)}

    @classmethod
    def _valid_careers_gen(cls, sim):
        if sim is None:
            return
        yield from (career for career in sim.sim_info.careers.values() if cls.career_filter.is_valid(career))

    @classmethod
    def has_valid_choice(cls, target, context, **kwargs):
        return any(cls._valid_careers_gen(context.sim))

    def _run_interaction_gen(self, timeline):
        self._show_picker_dialog(self.sim, target_sim=self.target)
        return True

    @flexmethod
    def picker_rows_gen(cls, inst, target, context, **kwargs):
        for career in cls._valid_careers_gen(context.sim):
            track = career.current_track_tuning
            row = ObjectPickerRow(name=track.career_name(context.sim), icon=track.icon, row_description=track.career_description, tag=career)
            yield row

    def on_choice_selected(self, choice_tag, **kwargs):
        career = choice_tag
        if career is not None and self.continuation is not None:
            picked_item_set = set()
            picked_item_set.add(career.guid64)
            self.interaction_parameters['picked_item_ids'] = picked_item_set
            self.push_tunable_continuation(self.continuation, picked_item_ids=picked_item_set)

class CareerProxyInteractionMixin:

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        if context.sim is None:
            return
        career = context.sim.sim_info.career_tracker.career_currently_within_hours
        if career is not None and not (career.currently_at_work or career.on_assignment):
            affordance = career.get_work_affordance()
            if affordance is not None:
                yield AffordanceObjectPair(affordance, target, affordance, None, **kwargs)

class CareerProxySuperInteraction(CareerProxyInteractionMixin, SuperInteraction):
    pass

class CareerTerrainProxySuperInteraction(CareerProxyInteractionMixin, TerrainSuperInteraction):

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        (position, _, result) = cls._get_target_position_surface_and_test_off_lot(target, context)
        if not result:
            return
        if position is not None and not terrain.is_position_in_street(position):
            return
        yield from super().potential_interactions(context.sim, context, **kwargs)

class CareerLeaveWorkEarlyInteraction(SimInfoInteraction):

    @classmethod
    def _test(cls, *args, sim_info=None, **kwargs):
        if sim_info is None:
            return TestResult(False, 'No sim info')
        career = sim_info.career_tracker.get_at_work_career()
        if career is None:
            return TestResult(False, 'Not currently at work')
        return super()._test(*args, **kwargs)

    def _run_interaction_gen(self, timeline):
        career = self._sim_info.career_tracker.get_at_work_career()
        if career is not None:
            career.leave_work_early()
        return True

class CareerTone(AwayAction):
    INSTANCE_TUNABLES = {'dominant_tone_loot_actions': TunableList(description='\n            Loot to apply at the end of a work period if this tone ran for the\n            most amount of time out of all tones.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions', 'RandomWeightedLoot'))), 'performance_multiplier': Tunable(description='\n            Performance multiplier applied to work performance gain.\n            ', tunable_type=float, default=1), 'periodic_sim_filter_loot': TunableList(description='\n            Loot to apply periodically to between the working Sim and other\n            Sims, specified via a Sim filter.\n            \n            Example Usages:\n            -Gain relationship with 2 coworkers every hour.\n            -Every hour, there is a 5% chance of meeting a new coworker.\n            ', tunable=TunableTuple(chance=SuccessChance.TunableFactory(description='\n                    Chance per hour of loot being applied.\n                    '), sim_filter=TunableSimFilter.TunableReference(description='\n                    Filter for specifying who to set at target Sims for loot\n                    application.\n                    '), max_sims=OptionalTunable(description='\n                    If enabled and the Sim filter finds more than the specified\n                    number of Sims, the loot will only be applied a random\n                    selection of this many Sims.\n                    ', tunable=TunableRange(tunable_type=int, default=1, minimum=1)), loot=LootActions.TunableReference(description='\n                    Loot actions to apply to the two Sims. The Sim in the \n                    career is Actor, and if Targeted is enabled those Sims\n                    will be TargetSim.\n                    ')))}
    runtime_commodity = None

    @classmethod
    def _tuning_loaded_callback(cls):
        if cls.runtime_commodity is not None:
            return
        commodity = RuntimeCommodity.generate(cls.__name__)
        commodity.decay_rate = 0
        commodity.convergence_value = 0
        commodity.remove_on_convergence = True
        commodity.visible = False
        commodity.max_value_tuning = date_and_time.SECONDS_PER_WEEK
        commodity.min_value_tuning = 0
        commodity.initial_value = 0
        commodity._time_passage_fixup_type = CommodityTimePassageFixupType.DO_NOT_FIXUP
        cls.runtime_commodity = commodity

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._update_alarm_handle = None
        self._last_update_time = None

    def run(self, callback):
        super().run(callback)
        self._last_update_time = services.time_service().sim_now
        time_span = clock.interval_in_sim_minutes(Career.CAREER_PERFORMANCE_UPDATE_INTERVAL)
        self._update_alarm_handle = alarms.add_alarm(self, time_span, lambda alarm_handle: self._update(), repeating=True)

    def stop(self):
        if self._update_alarm_handle is not None:
            alarms.cancel_alarm(self._update_alarm_handle)
            self._update_alarm_handle = None
        self._update()
        super().stop()

    def _update(self):
        career = self.sim_info.career_tracker.get_at_work_career()
        if career is None:
            logger.error('CareerTone {} trying to update performance when Sim {} not at work', self, self.sim_info, owner='tingyul')
            return
        if career._upcoming_gig is not None and career._upcoming_gig.odd_job_tuning is not None:
            return
        now = services.time_service().sim_now
        elapsed = now - self._last_update_time
        self._last_update_time = now
        career.apply_performance_change(elapsed, self.performance_multiplier)
        career.resend_career_data()
        resolver = SingleSimResolver(self.sim_info)
        for entry in self.periodic_sim_filter_loot:
            chance = entry.chance.get_chance(resolver)*elapsed.in_hours()
            if random.random() > chance:
                pass
            else:
                services.sim_filter_service().submit_filter(entry.sim_filter, self._sim_filter_loot_response, callback_event_data=entry, requesting_sim_info=self.sim_info, gsi_source_fn=self.get_sim_filter_gsi_name)

    def get_sim_filter_gsi_name(self):
        return str(self)

    def _sim_filter_loot_response(self, filter_results, callback_event_data):
        entry = callback_event_data
        if entry.max_sims is None:
            targets = tuple(result.sim_info for result in filter_results)
        else:
            sample_size = min(len(filter_results), entry.max_sims)
            targets = tuple(result.sim_info for result in random.sample(filter_results, sample_size))
        for target in targets:
            resolver = DoubleSimResolver(self.sim_info, target)
            entry.loot.apply_to_resolver(resolver)

    def apply_dominant_tone_loot(self):
        resolver = self.get_resolver()
        for loot in self.dominant_tone_loot_actions:
            loot.apply_to_resolver(resolver)
