from event_testing.resolver import SingleSimResolverfrom interactions.utils.loot import LootActionsfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableListfrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationStateData, TunableSituationJobAndRoleState, SituationStatefrom situations.situation_types import SituationCreationUIOptionfrom statistics.statistic import Statisticfrom tunable_time import TunableTimeOfDayfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport operatorimport servicesimport sims4logger = sims4.log.Logger('KaraokeContestSituation', default_owner='jdimailig')
class _KaraokeContestSituationState(SituationState):
    pass

class KaraokeContestSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'scoring_stat': Statistic.TunableReference(description='\n            The statistic to look for to determine how the Sim scored.\n            ', tuning_group=GroupNames.SITUATION), 'end_time': TunableTimeOfDay(description='\n            The time that this situation will end.\n            ', tuning_group=GroupNames.SITUATION), 'start_notification': TunableUiDialogNotificationSnippet(description='\n            The notification to display when this situation starts.\n            ', tuning_group=GroupNames.SITUATION), 'player_won_notification': TunableUiDialogNotificationSnippet(description='\n            The notification to display when this situation ends and player Sim won.\n            ', tuning_group=GroupNames.SITUATION), 'player_lost_notification': TunableUiDialogNotificationSnippet(description='\n            The notification to display when this situation ends and player Sim participated but lost.\n            ', tuning_group=GroupNames.SITUATION), 'end_notification': TunableUiDialogNotificationSnippet(description='\n            The notification to display when this situation ends without the active Sim having participated.\n            ', tuning_group=GroupNames.SITUATION), 'no_winner_notification': TunableUiDialogNotificationSnippet(description='\n            The notification to display when no one actually scored anything.\n            '), 'contestant_job_and_role': TunableSituationJobAndRoleState(description='\n            The contestant job and role for this situation.\n            ', tuning_group=GroupNames.SITUATION), 'winner_loot_actions': TunableList(description='\n            Loot to apply to the winner of the contest.\n            ', tuning_group=GroupNames.SITUATION, tunable=LootActions.TunableReference())}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _KaraokeContestSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.contestant_job_and_role.job, cls.contestant_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def _handle_contest_results(self):
        scores = []
        for sim in self._situation_sims:
            score = sim.get_stat_value(self.scoring_stat)
            if score <= 0:
                pass
            else:
                scores.append((sim, score))
                logger.debug('{0} got a score of {1}', sim, score)
        if scores:
            self._show_winner_notification(scores)
        else:
            self._show_no_winner_notification()

    def _show_winner_notification(self, scores):
        (winner, winning_score) = max(scores, key=operator.itemgetter(1))
        household_sim_infos = list(services.active_household().sim_info_gen())
        player_sim_participated = any(score_tuple[0] for score_tuple in scores if score_tuple[0].sim_info in household_sim_infos)
        player_sim_won = winner.sim_info in household_sim_infos
        logger.debug('Winner is {0} with score {1}!', winner, winning_score)
        resolver = SingleSimResolver(winner.sim_info)
        for loot_action in self.winner_loot_actions:
            loot_action.apply_to_resolver(resolver)
        if not player_sim_participated:
            dialog = self.end_notification(services.active_sim_info(), resolver=resolver)
        elif player_sim_won:
            dialog = self.player_won_notification(services.active_sim_info(), resolver=resolver)
        else:
            dialog = self.player_lost_notification(services.active_sim_info(), resolver=resolver)
        dialog.show_dialog()

    def _show_no_winner_notification(self):
        active_sim_info = services.active_sim_info()
        resolver = SingleSimResolver(active_sim_info)
        dialog = self.no_winner_notification(active_sim_info, resolver=resolver)
        dialog.show_dialog()

    def start_situation(self):
        super().start_situation()
        self._change_state(_KaraokeContestSituationState())
        dialog = self.start_notification(services.active_sim_info())
        dialog.show_dialog()

    def _get_duration(self):
        time_now = services.time_service().sim_now
        return time_now.time_till_next_day_time(self.end_time).in_minutes()

    def _situation_timed_out(self, _):
        self._handle_contest_results()
        super()._situation_timed_out(_)
lock_instance_tunables(KaraokeContestSituation, exclusivity=BouncerExclusivityCategory.VENUE_BACKGROUND, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)