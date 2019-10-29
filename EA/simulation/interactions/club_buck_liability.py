from clubs import club_tuningfrom clubs.club_telemetry import club_telemetry_writer, TELEMETRY_HOOK_CLUB_BUCKSEARNED, TELEMETRY_FIELD_CLUB_ID, TELEMETRY_FIELD_CLUB_AMOUNTEARNED, TELEMETRY_FIELD_CLUB_TOTALAMOUNTEARNEDfrom clubs.club_tuning import ClubTunablesfrom date_and_time import create_time_spanfrom event_testing import test_eventsfrom interactions.base.interaction import TELEMETRY_FIELD_INTERACTION_IDfrom interactions.liability import Liabilityimport alarmsimport servicesimport telemetry_helper
class ClubBucksLiability(Liability):
    LIABILITY_TOKEN = 'ClubBucksLiability'

    def __init__(self, interaction, **kwargs):
        super().__init__(**kwargs)
        self._timer = None
        self._interaction = interaction
        self._totals_earned = {}
        self._fired_events = False

    def on_run(self):
        if self._timer is not None:
            return
        sim = self._interaction.sim
        if not sim.is_selectable:
            self._interaction.remove_liability(self.LIABILITY_TOKEN)
            return
        start_duration = create_time_span(minutes=club_tuning.ClubTunables.CLUB_BUCKS_ENCOURAGED_REWARDS_TIMER_START)
        repeat_duration = create_time_span(minutes=club_tuning.ClubTunables.CLUB_BUCKS_ENCOURAGED_REWARDS_TIMER_REPEATING)
        self._timer = alarms.add_alarm(self, start_duration, self._award_bucks, repeating=True, repeating_time_span=repeat_duration)

    def release(self):
        if self._timer is None:
            return
        self._timer.cancel()
        self._timer = None
        club_service = services.get_club_service()
        for (club_id, total) in self._totals_earned.items():
            with telemetry_helper.begin_hook(club_telemetry_writer, TELEMETRY_HOOK_CLUB_BUCKSEARNED) as hook:
                hook.write_int(TELEMETRY_FIELD_CLUB_ID, club_id)
                hook.write_guid(TELEMETRY_FIELD_INTERACTION_ID, self._interaction.guid64)
                hook.write_int(TELEMETRY_FIELD_CLUB_AMOUNTEARNED, total)
                club = club_service.get_club_by_id(club_id)
                if club is not None:
                    club_bucks = club.bucks_tracker.get_bucks_amount_for_type(ClubTunables.CLUB_BUCKS_TYPE)
                    hook.write_int(TELEMETRY_FIELD_CLUB_TOTALAMOUNTEARNED, club_bucks)
        self._totals_earned.clear()

    def _get_club_bucks_multiplier(self):
        sim = self._interaction.sim
        if sim is None:
            return 1
        trait_tracker = sim.sim_info.trait_tracker
        if trait_tracker is None:
            return 1
        if club_tuning.ClubTunables.CLUB_BUCKS_REWARDS_MULTIPLIER.trait in trait_tracker.equipped_traits:
            multiplier = club_tuning.ClubTunables.CLUB_BUCKS_REWARDS_MULTIPLIER.multiplier
        else:
            multiplier = 1
        return multiplier

    def _award_bucks(self, handle):
        club_service = services.get_club_service()
        if club_service is None:
            self._interaction.remove_liability(self.LIABILITY_TOKEN)
            return
        club_rewards = club_service.get_encouragment_mapping_for_sim_info(self._interaction.sim.sim_info, self._interaction.aop)
        if not club_rewards:
            return
        multiplier = self._get_club_bucks_multiplier()
        for (club, reward) in club_rewards.items():
            club.bucks_tracker.try_modify_bucks(club_tuning.ClubTunables.CLUB_BUCKS_TYPE, int(reward*multiplier), reason='Club Buck Liability: {}'.format(self._interaction))
            total = self._totals_earned.get(club.id, 0)
            self._totals_earned[club.id] = total + reward*multiplier
            self._handle_first_bucks_earned_events()

    def should_transfer(self, continuation):
        club_service = services.get_club_service()
        if club_service is None:
            return False
        elif not club_service.interaction_is_encouraged_for_sim_info(self._interaction.sim.sim_info, continuation.aop):
            return False
        return True

    def transfer(self, continuation):
        club_service = services.get_club_service()
        if club_service is None:
            return
        self._interaction = continuation

    def _handle_first_bucks_earned_events(self):
        if not self._fired_events:
            services.get_event_manager().process_event(test_events.TestEvent.EncouragedInteractionStarted, sim_info=self._interaction.sim.sim_info)
            self._fired_events = True
