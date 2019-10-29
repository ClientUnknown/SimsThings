import randomfrom protocolbuffers import Consts_pb2from date_and_time import create_date_and_timefrom drama_scheduler.drama_node import BaseDramaNodefrom event_testing.resolver import SingleSimResolverfrom event_testing.test_events import TestEventfrom interactions.utils.loot import LootActionsfrom sims.sim_info_lod import SimInfoLODLevelfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableRangefrom sims4.utils import classpropertyfrom tunable_time import TunableTimeOfWeekfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport alarmsimport servicesLOTTERY_CANIDATES_TOKEN = 'lottery_candidates'
class LotteryDramaNode(BaseDramaNode):
    INSTANCE_TUNABLES = {'payout': Tunable(description="\n            The payout of the lottery to the winning Sim's household.\n            ", tunable_type=int, default=1000000), 'lottery_event': TunableEnumEntry(description='\n            The event that triggers the active household being added to the\n            lottery.\n            ', tunable_type=TestEvent, default=TestEvent.Invalid, invalid_enums=(TestEvent.Invalid,)), 'minimum_sims': TunableRange(description='\n            The minimum number of sims that we want to trigger a lottery\n            for.  If not enough households have signed up for the lottery we\n            will select random non-played sims to fill up the lottery\n            pool.\n            ', tunable_type=int, default=100, minimum=1), 'end_time': TunableTimeOfWeek(description='\n            The time that this Drama Node is going to end.\n            '), 'winning_sim_loot': LootActions.TunableReference(description='\n            Loot action applied to the Winning Sim if they are in the active\n            household when the lottery completes.\n            '), 'losing_sim_loot': LootActions.TunableReference(description='\n            Loot action applied to losing Sims if they are in the active\n            household when the lottery completes.\n            '), 'notification': TunableUiDialogNotificationSnippet(description='\n            The notification that we will display to explain the winner of the\n            lottery.\n            ')}

    @classproperty
    def simless(cls):
        return True

    @classproperty
    def persist_when_active(cls):
        return True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._end_alarm_handle = None
        self._lottery_sims = set()

    def cleanup(self, from_service_stop=False):
        super().cleanup(from_service_stop=from_service_stop)
        if self._end_alarm_handle is not None:
            alarms.cancel_alarm(self._end_alarm_handle)
        self._lottery_sims.clear()
        services.get_event_manager().unregister_single_event(self, self.lottery_event)

    def handle_event(self, sim_info, event, resolver):
        if sim_info is None:
            return
        self._lottery_sims.add(sim_info.sim_id)

    def _check_lottery_sim_criteria(self, sim_info):
        if sim_info.lod == SimInfoLODLevel.MINIMUM:
            return False
        if sim_info.is_teen_or_younger:
            return False
        if sim_info.household.hidden:
            return False
        elif sim_info.household.is_player_household:
            return False
        return True

    def _end_lottery(self, _):
        try:
            if not self._lottery_sims:
                return
            lottery_candidates = []
            active_household_candidates = []
            sim_info_manager = services.sim_info_manager()
            for sim_id in self._lottery_sims:
                sim_info = sim_info_manager.get(sim_id)
                if sim_info is None:
                    pass
                else:
                    lottery_candidates.append(sim_info)
                    if sim_info.is_selectable:
                        active_household_candidates.append(sim_info)
            if len(lottery_candidates) < self.minimum_sims:
                sims_to_get = self.minimum_sims - len(lottery_candidates)
                additional_candidates = [sim_info for sim_info in sim_info_manager.values() if self._check_lottery_sim_criteria(sim_info)]
                if len(additional_candidates) < sims_to_get:
                    lottery_candidates.extend(additional_candidates)
                else:
                    lottery_candidates.extend(random.sample(additional_candidates, sims_to_get))
            winning_sim_info = random.choice(lottery_candidates)
            winning_sim_info.household.funds.add(self.payout, Consts_pb2.FUNDS_HOLIDAY_LOTTERY)
            notification = self.notification(services.active_sim_info())
            notification.show_dialog(additional_tokens=(winning_sim_info,))
            if winning_sim_info.is_selectable:
                resolver = SingleSimResolver(winning_sim_info)
                self.winning_sim_loot.apply_to_resolver(resolver)
            else:
                for sim_info in active_household_candidates:
                    resolver = SingleSimResolver(sim_info)
                    self.losing_sim_loot.apply_to_resolver(resolver)
        finally:
            services.drama_scheduler_service().complete_node(self.uid)

    def _setup_lottery(self):
        time = create_date_and_time(days=self.end_time.day, hours=self.end_time.hour, minutes=self.end_time.minute)
        time_until_end = services.time_service().sim_now.time_to_week_time(time)
        self._end_alarm_handle = alarms.add_alarm(self, time_until_end, self._end_lottery, cross_zone=True)
        services.get_event_manager().register_single_event(self, self.lottery_event)

    def _run(self):
        self._setup_lottery()
        return False

    def resume(self):
        self._setup_lottery()

    def _save_custom_data(self, writer):
        writer.write_uint64s(LOTTERY_CANIDATES_TOKEN, self._lottery_sims)

    def _load_custom_data(self, reader):
        self._lottery_sims = set(reader.read_uint64s(LOTTERY_CANIDATES_TOKEN, ()))
        return True
