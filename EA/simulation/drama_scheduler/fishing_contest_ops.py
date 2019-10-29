from drama_scheduler.fishing_contest_tuning import FishingContestTuningfrom interactions import ParticipantType, ParticipantTypeSingleSimfrom interactions.utils.interaction_elements import XevtTriggeredElementfrom interactions.utils.loot_basic_op import BaseLootOperationfrom sims4.tuning.tunable import TunableList, OptionalTunable, TunableFactoryfrom sims4.tuning.tunable_base import GroupNamesfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationSnippetimport servicesimport sims4import singletonslogger = sims4.log.Logger('DramaNode', default_owner='msundaram')
class FishingContestSubmitElement(XevtTriggeredElement):
    FACTORY_TUNABLES = {'success_notification_by_rank': TunableList(description='\n            Notifications displayed if submitted fish is large enough to be ranked in\n            the fishing contest. Index refers to the place that the fish is in currently.\n            1st, 2nd, 3rd, etc.\n            ', tunable=UiDialogNotification.TunableFactory(), tuning_group=GroupNames.UI), 'unranked_notification': OptionalTunable(description='\n            If enabled, notification displayed if submitted fish is not large enough to rank in\n            the fishing contest. \n            ', tunable=TunableUiDialogNotificationSnippet(description='\n                The notification that will appear when the submitted fish does not rank.\n                '), tuning_group=GroupNames.UI)}

    def _do_behavior(self):
        resolver = self.interaction.get_resolver()
        running_contests = services.drama_scheduler_service().get_running_nodes_by_class(FishingContestTuning.FISHING_CONTEST)
        for contest in running_contests:
            if contest.is_during_pre_festival():
                pass
            else:
                fish = self.interaction.get_participant(ParticipantType.PickedObject)
                if fish is None:
                    logger.error('{} does not have PickedObject participant', resolver)
                    return False
                sim = self.interaction.sim
                if sim is None:
                    logger.error('{} does not have sim participant', resolver)
                    return False
                return self._remove_fish_and_add_score(contest, sim, fish, resolver)
        logger.error('{} no valid FishingContest', resolver)
        return False

    def _remove_fish_and_add_score(self, contest, sim, fish, resolver):
        weight = fish.get_tracker(FishingContestTuning.WEIGHT_STATISTIC)
        if weight is None:
            logger.error('{} picked object does not have weight stat {}', resolver, FishingContestTuning.WEIGHT_STATISTIC)
            return False
        current_inventory = fish.get_inventory()
        if current_inventory is None:
            logger.error('{} fish {} is not in an inventory', resolver, fish)
            return False
        if not current_inventory.try_remove_object_by_id(fish.id):
            logger.error('{} fail to remove object {} from inventory {}', resolver, fish, current_inventory)
            return False
        rank = contest.add_score(sim.id, weight.get_value(FishingContestTuning.WEIGHT_STATISTIC))
        if rank is not None:
            if rank >= len(self.success_notification_by_rank):
                return False
            notification = self.success_notification_by_rank[rank]
            dialog = notification(sim, target_sim_id=sim.id, resolver=resolver)
            dialog.show_dialog()
        elif self.unranked_notification is not None:
            dialog = self.unranked_notification(sim, target_sim_id=sim.id, resolver=resolver)
            dialog.show_dialog()
        return True

class FishingContestAwardWinners(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        running_contests = services.drama_scheduler_service().get_running_nodes_by_class(FishingContestTuning.FISHING_CONTEST)
        for contest in running_contests:
            if contest.is_during_pre_festival():
                pass
            else:
                contest.award_winners(subject, resolver, show_fallback_dialog=True)
                return
        logger.error('{} is not currently running, cannot award winners', FishingContestTuning.FISHING_CONTEST)

    @TunableFactory.factory_option
    def subject_participant_type_options(description=singletons.DEFAULT, **kwargs):
        return BaseLootOperation.get_participant_tunable(*('subject',), participant_type_enum=ParticipantTypeSingleSim, **kwargs)
