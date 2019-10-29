from call_to_action.call_to_action_elements import SituationStateCallToActionMixinfrom event_testing.resolver import SingleSimResolver, GlobalResolverfrom open_street_director.festival_open_street_director import BaseFestivalOpenStreetDirector, FestivalStateInfo, TimedFestivalState, LoadLayerFestivalState, CleanupObjectsFestivalStatefrom sims4 import randomfrom sims4.localization import LocalizationHelperTuningfrom sims4.tuning.tunable import TunableList, TunableTuple, Tunable, TunableRange, TunableReference, TunableInterval, OptionalTunablefrom sims4.utils import classpropertyfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, SituationState, SituationStateDatafrom situations.situation_guest_list import SituationGuestListfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport servicesimport sims4.resources
class LogicFestivalContestState(SituationStateCallToActionMixin, SituationState):
    pass

class LogicFestivalContestSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'contest_state': LogicFestivalContestState.TunableFactory(description='\n            The contest state for this Situation\n            Starts.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'npc_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of npcs that are in this situation.\n            '), 'player_job_and_role_state': TunableSituationJobAndRoleState(description='\n            The job and role state of player Sims that are in this situation.\n            '), 'start_notification': OptionalTunable(description='\n            If enabled then we will show a notification when this contest\n            begins.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification that will appear at the start of this situation.\n                ')), 'end_notification': OptionalTunable(description='\n            If enabled then we will show a notification when this contest ends.\n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification that will appear at the end of this situation.\n                '))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, LogicFestivalContestState, factory=cls.contest_state),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.npc_job_and_role_state.job, cls.npc_job_and_role_state.role_state), (cls.player_job_and_role_state.job, cls.player_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(self.contest_state())
        if self.start_notification is not None:
            start_notification = self.start_notification(services.active_sim_info())
            start_notification.show_dialog()

    def _issue_requests(self):
        super()._issue_requests()
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(role_state_type=self.player_job_and_role_state.role_state), job_type=self.player_job_and_role_state.job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)

    def _should_show_end_notification(self):
        return self.end_notification is not None

    def _get_end_notification_resolver_and_tokens(self):
        return (GlobalResolver(), tuple())

    def on_remove(self):
        if self._should_show_end_notification():
            (resolver, additional_tokens) = self._get_end_notification_resolver_and_tokens()
            end_notification = self.end_notification(services.active_sim_info(), resolver=resolver)
            end_notification.show_dialog(additional_tokens=additional_tokens)
        super().on_remove()

class ScoredLogicFestivalContestSituation(LogicFestivalContestSituation):
    INSTANCE_TUNABLES = {'contest_statistic': TunableReference(description='\n            The statistic that we will use for scoring the Sims in the contest.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'bronze_prize': TunableReference(description='\n            A reference to a loot that will be applied as the bronze prize.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), 'silver_prize': TunableReference(description='\n            A reference to a loot that will be applied as the silver prize.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',)), 'gold_prize': TunableReference(description='\n            A reference to a loot that will be applied as the gold prize.\n            ', manager=services.get_instance_manager(sims4.resources.Types.ACTION), class_restrictions=('LootActions',))}

    def _on_add_sim_to_situation(self, sim, job_type, role_state_type_override=None):
        super()._on_add_sim_to_situation(sim, job_type, role_state_type_override=role_state_type_override)
        sim.set_stat_value(self.contest_statistic, value=self.contest_statistic.min_value, add=True)

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        sim.sim_info.remove_statistic(self.contest_statistic)

    def _should_show_end_notification(self):
        return super()._should_show_end_notification() and any(sim.get_stat_value(self.contest_statistic) > 0 for sim in self.all_sims_in_situation_gen())

    def _get_end_notification_resolver_and_tokens(self):
        sims = [sim for sim in self.all_sims_in_situation_gen() if sim.get_stat_value(self.contest_statistic) > 0]
        if not sims:
            return (GlobalResolver(), tuple())
        sims.sort(key=lambda item: (item.get_stat_value(self.contest_statistic), item.is_selectable), reverse=True)
        gold_sim = sims[0]
        return (SingleSimResolver(gold_sim.sim_info), (gold_sim.get_stat_value(self.contest_statistic),))

    def on_remove(self):
        sims = [sim for sim in self.all_sims_in_situation_gen() if sim.get_stat_value(self.contest_statistic) > 0]
        if sims:
            sims.sort(key=lambda item: (item.get_stat_value(self.contest_statistic), item.is_selectable), reverse=True)
            gold_sim = sims[0]
            if gold_sim.is_selectable:
                gold_resolver = SingleSimResolver(gold_sim.sim_info)
                self.gold_prize.apply_to_resolver(gold_resolver)
                if len(sims) > 1:
                    silver_sim = sims[1]
                    if silver_sim.is_selectable:
                        silver_resolver = SingleSimResolver(silver_sim.sim_info)
                        self.silver_prize.apply_to_resolver(silver_resolver)
                if len(sims) > 2:
                    bronze_sim = sims[2]
                    if bronze_sim.is_selectable:
                        bronze_resolver = SingleSimResolver(bronze_sim.sim_info)
                        self.bronze_prize.apply_to_resolver(bronze_resolver)
        super().on_remove()

class SpinupFestivalState(LoadLayerFestivalState):

    @classproperty
    def key(cls):
        return 1

    def _get_next_state(self):
        return self._owner.pre_contest_festival_state(self._owner)

class PreContestFestivalState(TimedFestivalState):

    @classproperty
    def key(cls):
        return 2

    def _get_next_state(self):
        return self._owner.contest_festival_state(self._owner)
CONTEST_TOKENS = 'contest_situation_ids'
class ContestFestivalState(TimedFestivalState):
    FACTORY_TUNABLES = {'_possible_contests': TunableList(description='\n            A list of possible situations to choose and weights associated\n            with them.\n            ', tunable=TunableTuple(description='\n                A pair of situation and weight.\n                ', weight=TunableRange(description='\n                    The weight of this situation to be chosen.\n                    ', tunable_type=float, default=1, minimum=1), situation=LogicFestivalContestSituation.TunableReference(description='\n                    The type of contest to run.\n                    '))), '_number_of_contests': TunableInterval(description='\n            Minimum and maximum number of contests to trigger\n            Randomly start some number of contests between minimum and maximum,\n            with maximum capped at the actual number of possible contests.\n            if no min is specified, will do max.  If no max is specified\n            will randomly pick between min and all.  (So if neither specified, will do\n            all)\n            ', tunable_type=int, minimum=0, default_lower=None, default_upper=None)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._contest_situation_ids = None

    @classproperty
    def key(cls):
        return 3

    def _get_next_state(self):
        return self._owner.post_contest_festival_state(self._owner)

    def on_state_activated(self, reader=None, preroll_time_override=None):
        super().on_state_activated(reader=reader, preroll_time_override=preroll_time_override)
        if reader is not None:
            self._contest_situation_ids = reader.read_uint64s(CONTEST_TOKENS, None)
        if self._contest_situation_ids is None:
            self._contest_situation_ids = []
            situation_manager = services.get_zone_situation_manager()
            max_contests = self._number_of_contests.upper_bound
            min_contests = self._number_of_contests.lower_bound
            if max_contests is None:
                max_contests = len(self._possible_contests)
            else:
                max_contests = min(len(self._possible_contests), max_contests)
            if min_contests is None:
                min_contests = len(self._possible_contests)
            min_contests = min(min_contests, max_contests)
            contest_count = random.random.randint(min_contests, max_contests)
            possible_situations = [(possible_contest.weight, possible_contest.situation) for possible_contest in self._possible_contests]
            while contest_count:
                contest_count -= 1
                chosen_situation = random.pop_weighted(possible_situations)
                guest_list = SituationGuestList(invite_only=True)
                self._contest_situation_ids.append(situation_manager.create_situation(chosen_situation, guest_list=guest_list, user_facing=False))

    def on_state_deactivated(self):
        if self._contest_situation_ids is not None:
            situation_manager = services.get_zone_situation_manager()
            for situation_id in self._contest_situation_ids:
                situation_manager.destroy_situation_by_id(situation_id)
        super().on_state_deactivated()

    def save(self, writer):
        super().save(writer)
        if self._contest_situation_ids is not None:
            writer.write_uint64s(CONTEST_TOKENS, self._contest_situation_ids)

class PostContestFestivalState(TimedFestivalState):

    @classproperty
    def key(cls):
        return 4

    def _get_next_state(self):
        return self._owner.cooldown_festival_state(self._owner)

class CooldownFestivalState(TimedFestivalState):
    FACTORY_TUNABLES = {'notification': TunableUiDialogNotificationSnippet(description='\n            The notification that will appear when we enter this festival\n            state.\n            ')}

    @classproperty
    def key(cls):
        return 5

    def on_state_activated(self, reader=None, preroll_time_override=None):
        super().on_state_activated(reader=reader, preroll_time_override=preroll_time_override)
        for situation in self._owner.get_running_festival_situations():
            situation.put_on_cooldown()
        notification = self.notification(services.active_sim_info())
        notification.show_dialog()

    def _get_next_state(self):
        return self._owner.cleanup_festival_state(self._owner)

class CleanupFestivalState(CleanupObjectsFestivalState):

    @classproperty
    def key(cls):
        return 6

    def _get_next_state(self):
        pass

class LogicFestivalOpenStreetDirector(BaseFestivalOpenStreetDirector):
    INSTANCE_TUNABLES = {'spinup_festival_state': SpinupFestivalState.TunableFactory(), 'pre_contest_festival_state': PreContestFestivalState.TunableFactory(), 'contest_festival_state': ContestFestivalState.TunableFactory(), 'post_contest_festival_state': PostContestFestivalState.TunableFactory(), 'cooldown_festival_state': CooldownFestivalState.TunableFactory(), 'cleanup_festival_state': CleanupFestivalState.TunableFactory()}

    @classmethod
    def _states(cls):
        return (FestivalStateInfo(SpinupFestivalState, cls.spinup_festival_state), FestivalStateInfo(PreContestFestivalState, cls.pre_contest_festival_state), FestivalStateInfo(ContestFestivalState, cls.contest_festival_state), FestivalStateInfo(PostContestFestivalState, cls.post_contest_festival_state), FestivalStateInfo(CooldownFestivalState, cls.cooldown_festival_state), FestivalStateInfo(CleanupFestivalState, cls.cleanup_festival_state))

    def _get_starting_state(self):
        return self.spinup_festival_state(self)

    def on_startup(self):
        super().on_startup()
        if self.was_loaded or not self.did_preroll:
            self.change_state(self._get_starting_state())

    def _clean_up(self):
        if self._current_state.key != CleanupFestivalState.key:
            self.change_state(self.cleanup_festival_state(self))
