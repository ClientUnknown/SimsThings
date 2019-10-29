import randomfrom clock import interval_in_sim_minutesfrom clubs.club_tests import ClubTestfrom distributor.shared_messages import IconInfoDatafrom drama_scheduler.drama_node_tests import FestivalRunningTestfrom event_testing.resolver import GlobalResolver, DoubleSimResolverfrom event_testing.results import TestResultfrom interactions import ParticipantType, ParticipantTypeActorTargetSim, ParticipantTypeSimfrom interactions.money_payout import MoneyChangefrom interactions.utils.display_mixin import get_display_mixinfrom interactions.utils.loot_ops import DialogLootOp, StateChangeLootOpfrom interactions.utils.reactions import ReactionLootOpfrom interactions.utils.success_chance import SuccessChancefrom relationships.relationship_tests import TunableRelationshipTestfrom seasons.season_tests import SeasonTestfrom sims4.callback_utils import CallableListfrom sims4.tuning.instances import HashedTunedInstanceMetaclass, TunedInstanceMetaclassfrom sims4.tuning.tunable import Tunable, TunableEnumEntry, TunableList, TunableReference, TunableSet, TunableTuple, TunableVariant, TunableResourceKey, TunableSimMinute, HasTunableReference, OptionalTunablefrom sims4.tuning.tunable_base import GroupNamesfrom situations.situation_types import SituationGoalDisplayTypefrom statistics.statistic_ops import TunableStatisticChangefrom tag import Tagfrom ui.ui_dialog import UiDialogOkfrom ui.ui_dialog_notification import UiDialogNotification, TunableUiDialogNotificationSnippetimport buffs.buff_opsimport enumimport event_testing.state_testsimport event_testing.test_variantsimport event_testing.testsimport objects.object_testsimport servicesimport sims.sim_info_testsimport sims4.resourcesimport situationsimport statistics.skill_testsimport world.world_testsimport zone_tests
class TunableWeightedSituationGoalReference(TunableTuple):

    def __init__(self, pack_safe=False, **kwargs):
        super().__init__(weight=Tunable(float, 1.0, description='Higher number means higher chance of being selected.'), goal=TunableReference(services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL), description='A goal in the set.', pack_safe=pack_safe))

class TunableSituationGoalPreTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(bucks_perks_test=event_testing.test_variants.BucksPerkTest.TunableFactory(locked_args={'tooltip': None}), buff=sims.sim_info_tests.BuffTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), career=event_testing.test_variants.TunableCareerTest.TunableFactory(locked_args={'tooltip': None}), club=ClubTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'club': ClubTest.CLUB_USE_ANY, 'tooltip': None}), collection=event_testing.test_variants.TunableCollectionThresholdTest(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), detective_clues=event_testing.test_variants.DetectiveClueTest.TunableFactory(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), has_lot_owner=event_testing.test_variants.HasLotOwnerTest.TunableFactory(locked_args={'tooltip': None}), household_size=event_testing.test_variants.HouseholdSizeTest.TunableFactory(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), inventory=objects.object_tests.InventoryTest.TunableFactory(locked_args={'tooltip': None}), location=world.world_tests.LocationTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), locked_portal_count=event_testing.test_variants.LockedPortalCountTest.TunableFactory(locked_args={'tooltip': None}), lot_owner=event_testing.test_variants.LotOwnerTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), mood=sims.sim_info_tests.MoodTest.TunableFactory(locked_args={'who': ParticipantTypeSim.Actor, 'tooltip': None}), motive=event_testing.statistic_tests.MotiveThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), nearby_floor_feature=world.floor_feature_test.NearbyFloorFeatureTest.TunableFactory(locked_args={'radius_actor': ParticipantType.Actor, 'tooltip': None}), object_criteria=objects.object_tests.ObjectCriteriaTest.TunableFactory(locked_args={'tooltip': None}), ranked_statistic=event_testing.statistic_tests.RankedStatThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), relationship=TunableRelationshipTest(locked_args={'subject': ParticipantType.Actor, 'test_event': 0, 'tooltip': None}), season=SeasonTest.TunableFactory(locked_args={'tooltip': None}), sim_filter=sims.sim_info_tests.FilterTest.TunableFactory(locked_args={'filter_target': ParticipantType.Actor, 'tooltip': None}), sim_info=sims.sim_info_tests.SimInfoTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), situation_job=event_testing.test_variants.TunableSituationJobTest(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), situation_running=event_testing.test_variants.TunableSituationRunningTest(locked_args={'tooltip': None}), skill_tag=statistics.skill_tests.SkillTagThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), skill_test=statistics.skill_tests.SkillRangeTest.TunableFactory(locked_args={'tooltip': None}), state=event_testing.state_tests.TunableStateTest(locked_args={'who': ParticipantType.Object, 'tooltip': None}), statistic=event_testing.statistic_tests.StatThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), time_of_day=event_testing.test_variants.TunableDayTimeTest(locked_args={'tooltip': None}), trait=sims.sim_info_tests.TraitTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'tooltip': None}), zone=zone_tests.ZoneTest.TunableFactory(locked_args={'tooltip': None}), description=description, **kwargs)

class TunableSituationGoalPreTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableSituationGoalPreTestVariant(), **kwargs)

class TunableSituationGoalPostTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(buff=sims.sim_info_tests.BuffTest.TunableFactory(participant_type_override=(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor), locked_args={'tooltip': None}), career=event_testing.test_variants.TunableCareerTest.TunableFactory(locked_args={'tooltip': None}), club=ClubTest.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'club': ClubTest.CLUB_USE_ANY, 'tooltip': None}), collection=event_testing.test_variants.TunableCollectionThresholdTest(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), inventory=objects.object_tests.InventoryTest.TunableFactory(locked_args={'tooltip': None}), location=world.world_tests.LocationTest.TunableFactory(locked_args={'tooltip': None}), lot_owner=event_testing.test_variants.LotOwnerTest.TunableFactory(locked_args={'tooltip': None}), mood=sims.sim_info_tests.MoodTest.TunableFactory(participant_type_override=(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor), locked_args={'tooltip': None}), motive=event_testing.statistic_tests.MotiveThresholdTest.TunableFactory(participant_type_override=(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor), locked_args={'tooltip': None}), object_criteria=objects.object_tests.ObjectCriteriaTest.TunableFactory(locked_args={'tooltip': None}), ranked_statistic=event_testing.statistic_tests.RankedStatThresholdTest.TunableFactory(locked_args={'who': ParticipantType.Actor, 'tooltip': None}), relationship=TunableRelationshipTest(locked_args={'subject': ParticipantType.Actor, 'test_event': 0, 'tooltip': None}), relative_statistic=event_testing.statistic_tests.RelativeStatTest.TunableFactory(locked_args={'source': ParticipantType.Actor, 'target': ParticipantType.TargetSim}), sim_filter=sims.sim_info_tests.FilterTest.TunableFactory(locked_args={'tooltip': None}), sim_info=sims.sim_info_tests.SimInfoTest.TunableFactory(participant_type_override=(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor), locked_args={'tooltip': None}), situation_job=event_testing.test_variants.TunableSituationJobTest(locked_args={'participant': ParticipantType.Actor, 'tooltip': None}), skill_tag=statistics.skill_tests.SkillTagThresholdTest.TunableFactory(participant_type_override=(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor), locked_args={'tooltip': None}), skill_test=statistics.skill_tests.SkillRangeTest.TunableFactory(locked_args={'tooltip': None}), state=event_testing.state_tests.TunableStateTest(locked_args={'who': ParticipantType.Object, 'tooltip': None}), statistic=event_testing.statistic_tests.StatThresholdTest.TunableFactory(participant_type_override=(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor), locked_args={'tooltip': None}), time_of_day=event_testing.test_variants.TunableDayTimeTest(locked_args={'tooltip': None}), topic=event_testing.test_variants.TunableTopicTest(locked_args={'subject': ParticipantType.Actor, 'target_sim': ParticipantType.TargetSim, 'tooltip': None}), trait=sims.sim_info_tests.TraitTest.TunableFactory(participant_type_override=(ParticipantTypeActorTargetSim, ParticipantTypeActorTargetSim.Actor), locked_args={'tooltip': None}), zone=zone_tests.ZoneTest.TunableFactory(locked_args={'tooltip': None}), description=description, **kwargs)

class TunableSituationGoalPostTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableSituationGoalPostTestVariant(), **kwargs)

class TunableSituationGoalEnvironmentPreTestVariant(TunableVariant):

    def __init__(self, description='A single tunable test.', **kwargs):
        super().__init__(object_criteria=objects.object_tests.ObjectCriteriaTest.TunableFactory(locked_args={'tooltip': None}), region=event_testing.test_variants.RegionTest.TunableFactory(locked_args={'tooltip': None, 'subject': None}), festival_running=FestivalRunningTest.TunableFactory(locked_args={'tooltip': None}), description=description, **kwargs)

class TunableSituationGoalEnvironmentPreTestSet(event_testing.tests.TestListLoadingMixin):
    DEFAULT_LIST = event_testing.tests.TestList()

    def __init__(self, description=None, **kwargs):
        if description is None:
            description = 'A list of tests.  All tests must succeed to pass the TestSet.'
        super().__init__(description=description, tunable=TunableSituationGoalEnvironmentPreTestVariant(), **kwargs)

class SituationGoalLootActions(HasTunableReference, metaclass=TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.ACTION)):
    INSTANCE_TUNABLES = {'goal_loot_actions': TunableList(TunableVariant(statistics=TunableStatisticChange(locked_args={'subject': ParticipantType.Actor, 'advertise': False, 'chance': SuccessChance.ONE}), money_loot=MoneyChange.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'chance': SuccessChance.ONE, 'display_to_user': None, 'statistic_multipliers': None}), buff=buffs.buff_ops.BuffOp.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'chance': SuccessChance.ONE}), notification_and_dialog=DialogLootOp.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'advertise': False, 'chance': SuccessChance.ONE}), reaction=ReactionLootOp.TunableFactory(locked_args={'subject': ParticipantType.Actor, 'advertise': False, 'chance': SuccessChance.ONE}), state_change=StateChangeLootOp.TunableFactory(locked_args={'advertise': False, 'chance': SuccessChance.ONE})))}

    def __iter__(self):
        return iter(self.goal_loot_actions)

class UiSituationGoalStatus(enum.Int):
    COMPLETED = 0
    CANCELED = 1
SituationGoalDisplayMixin = get_display_mixin(has_icon=True, has_tooltip=True, use_string_tokens=True)
class SituationGoal(SituationGoalDisplayMixin, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL)):
    INSTANCE_SUBCLASSES_ONLY = True
    IS_TARGETED = False
    INSTANCE_TUNABLES = {'_pre_tests': TunableSituationGoalPreTestSet(description='\n            A set of tests on the player sim and environment that all must\n            pass for the goal to be given to the player. e.g. Player Sim\n            has cooking skill level 7.\n            ', tuning_group=GroupNames.TESTS), '_post_tests': TunableSituationGoalPostTestSet(description='\n            A set of tests that must all pass when the player satisfies the\n            goal_test for the goal to be consider completed. e.g. Player\n            has Drunk Buff when Kissing another sim at Night.\n            ', tuning_group=GroupNames.TESTS), '_cancel_on_travel': Tunable(description='\n            If set, this situation goal will cancel (technically, complete\n            with score overridden to 0 so that situation score is not\n            progressed) if situation changes zone.\n            ', tunable_type=bool, default=False, tuning_group=GroupNames.TESTS), '_environment_pre_tests': TunableSituationGoalEnvironmentPreTestSet(description='\n            A set of sim independent pre tests.\n            e.g. There are five desks.\n            ', tuning_group=GroupNames.TESTS), 'role_tags': TunableSet(TunableEnumEntry(Tag, Tag.INVALID), description='\n            This goal will only be given to Sims in SituationJobs or Role\n            States marked with one of these tags.\n            '), '_cooldown': TunableSimMinute(description='\n            The cooldown of this situation goal.  Goals that have been\n            completed will not be chosen again for the amount of time that\n            is tuned.\n            ', default=600, minimum=0), '_iterations': Tunable(description='\n             Number of times the player must perform the action to complete the goal\n             ', tunable_type=int, default=1), '_score': Tunable(description='\n            The number of points received for completing the goal.\n            ', tunable_type=int, default=10), 'score_on_iteration_complete': OptionalTunable(description='\n            If enabled then we will add an amount of score to the situation\n            with every iteration of the situation goal completing.\n            ', tunable=Tunable(description='\n                An amount of score that should be applied when an iteration\n                completes.\n                ', tunable_type=int, default=10)), '_pre_goal_loot_list': TunableList(description='\n            A list of pre-defined loot actions that will applied to every\n            sim in the situation when this situation goal is started.\n             \n            Do not use this loot list in an attempt to undo changes made by\n            the RoleStates to the sim. For example, do not attempt\n            to remove buffs or commodities added by the RoleState.\n            ', tunable=SituationGoalLootActions.TunableReference()), '_goal_loot_list': TunableList(description='\n            A list of pre-defined loot actions that will applied to every\n            sim in the situation when this situation goal is completed.\n             \n            Do not use this loot list in an attempt to undo changes made by\n            the RoleStates to the sim. For example, do not attempt\n            to remove buffs or commodities added by the RoleState.\n            ', tunable=SituationGoalLootActions.TunableReference()), 'noncancelable': Tunable(description='\n            Checking this box will prevent the player from canceling this goal in the whim system.', tunable_type=bool, default=False), 'time_limit': Tunable(description='\n            Timeout (in Sim minutes) for Sim to complete this goal. The default state of 0 means\n            time is unlimited. If the goal is not completed in time, any tuned penalty loot is applied.', tunable_type=int, default=0), 'penalty_loot_list': TunableList(description='\n            A list of pre-defined loot actions that will applied to the Sim who fails\n            to complete this goal within the tuned time limit.\n            ', tunable=SituationGoalLootActions.TunableReference()), 'goal_awarded_notification': OptionalTunable(description='\n            If enabled, this goal will have a notification associated with it.\n            It is up to whatever system awards the goal (e.g. the Whim system)\n            to display the notification when necessary.\n            ', tunable=TunableUiDialogNotificationSnippet()), 'goal_completion_notification': OptionalTunable(tunable=UiDialogNotification.TunableFactory(description='\n                A TNS that will fire when this situation goal is completed.\n                ')), 'goal_completion_notification_and_modal_target': OptionalTunable(description='\n            If enabled then we will use the tuned situation job to pick a\n            random sim in the owning situation with that job to be the target\n            sim of the notification and modal dialog.\n            ', tunable=TunableReference(description='\n                The situation job that will be used to find a sim in the owning\n                situation to be the target sim.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_JOB))), 'audio_sting_on_complete': TunableResourceKey(description='\n            The sound to play when this goal is completed.\n            ', resource_types=(sims4.resources.Types.PROPX,), default=None, allow_none=True, tuning_group=GroupNames.AUDIO), 'goal_completion_modal_dialog': OptionalTunable(tunable=UiDialogOk.TunableFactory(description='\n                A modal dialog that will fire when this situation goal is\n                completed.\n                ')), 'visible_minor_goal': Tunable(description='\n            Whether or not this goal should be displayed in the minor goals\n            list if this goal is for a player facing situation.\n            ', tunable_type=bool, default=True, tuning_group=GroupNames.UI), 'display_type': TunableEnumEntry(description='\n            How this goal is presented in user-facing situations.\n            ', tunable_type=SituationGoalDisplayType, default=SituationGoalDisplayType.NORMAL, tuning_group=GroupNames.UI)}

    @classmethod
    def can_be_given_as_goal(cls, actor, situation, **kwargs):
        if actor is not None:
            resolver = event_testing.resolver.DataResolver(actor.sim_info, None)
            result = cls._pre_tests.run_tests(resolver)
            if not result:
                return result
        else:
            resolver = GlobalResolver()
        environment_test_result = cls._environment_pre_tests.run_tests(resolver)
        if not environment_test_result:
            return environment_test_result
        return TestResult.TRUE

    def __init__(self, sim_info=None, situation=None, goal_id=0, count=0, locked=False, completed_time=None, secondary_sim_info=None, **kwargs):
        self._sim_info = sim_info
        self._secondary_sim_info = secondary_sim_info
        self._situation = situation
        self.id = goal_id
        self._on_goal_completed_callbacks = CallableList()
        self._completed_time = completed_time
        self._count = count
        self._locked = locked
        self._score_override = None
        self._goal_status_override = None
        self._setup = False

    def setup(self):
        self._setup = True

    def destroy(self):
        self.decommision()
        self._sim_info = None
        self._situation = None

    def decommision(self):
        if self._setup:
            self._decommision()

    def _decommision(self):
        self._on_goal_completed_callbacks.clear()

    def create_seedling(self):
        actor_id = 0 if self._sim_info is None else self._sim_info.sim_id
        target_sim_info = self.get_required_target_sim_info()
        target_id = 0 if target_sim_info is None else target_sim_info.sim_id
        secondary_target_id = 0 if self._secondary_sim_info is None else self._secondary_sim_info.sim_id
        seedling = situations.situation_serialization.GoalSeedling(type(self), actor_id, target_id, secondary_target_id, self._count, self._locked, self._completed_time)
        return seedling

    def register_for_on_goal_completed_callback(self, listener):
        self._on_goal_completed_callbacks.append(listener)

    def unregister_for_on_goal_completed_callback(self, listener):
        self._on_goal_completed_callbacks.remove(listener)

    def get_gsi_name(self):
        if self._iterations <= 1:
            return self.__class__.__name__
        return '{} {}/{}'.format(self.__class__.__name__, self._count, self._iterations)

    def on_goal_offered(self):
        if self._situation is None:
            return
        for sim in self._situation.all_sims_in_situation_gen():
            resolver = sim.get_resolver()
            for loots in self._pre_goal_loot_list:
                for loot in loots.goal_loot_actions:
                    loot.apply_to_resolver(resolver)

    def _display_goal_completed_dialogs(self):
        actor_sim_info = services.active_sim_info()
        target_sim_info = None
        if self.goal_completion_notification_and_modal_target is not None:
            possible_sims = list(self._situation.all_sims_in_job_gen(self.goal_completion_notification_and_modal_target))
            if possible_sims:
                target_sim_info = random.choice(possible_sims)
            if target_sim_info is None:
                return
        resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
        if self.goal_completion_notification is not None:
            notification = self.goal_completion_notification(actor_sim_info, resolver=resolver)
            notification.show_dialog()
        if self.goal_completion_modal_dialog is not None:
            dialog = self.goal_completion_modal_dialog(actor_sim_info, resolver=resolver)
            dialog.show_dialog()

    def _on_goal_completed(self, start_cooldown=True):
        if start_cooldown:
            self._completed_time = services.time_service().sim_now
        loot_sims = (self._sim_info,) if self._situation is None else tuple(self._situation.all_sims_in_situation_gen())
        for loots in self._goal_loot_list:
            for loot in loots.goal_loot_actions:
                for sim in loot_sims:
                    loot.apply_to_resolver(sim.get_resolver())
        self._display_goal_completed_dialogs()
        with situations.situation_manager.DelayedSituationDestruction():
            self._on_goal_completed_callbacks(self, True)

    def _on_iteration_completed(self):
        self._on_goal_completed_callbacks(self, False)

    def force_complete(self, target_sim=None, score_override=None, start_cooldown=True):
        self._score_override = score_override
        self._count = self._iterations
        self._on_goal_completed(start_cooldown=start_cooldown)

    def handle_event(self, sim_info, event, resolver):
        if self._sim_info is not None and self._sim_info is not sim_info:
            return
        if self._run_goal_completion_tests(sim_info, event, resolver):
            self._count += 1
            if self._count >= self._iterations:
                self._on_goal_completed()
            else:
                self._on_iteration_completed()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        return self._post_tests.run_tests(resolver)

    def should_autocomplete_on_load(self, previous_zone_id):
        if self._cancel_on_travel:
            zone_id = services.current_zone_id()
            if previous_zone_id != zone_id:
                return True
        return False

    def get_actual_target_sim_info(self):
        pass

    @property
    def sim_info(self):
        return self._sim_info

    def get_required_target_sim_info(self):
        pass

    def get_secondary_sim_info(self):
        return self._secondary_sim_info

    @property
    def created_time(self):
        pass

    @property
    def completed_time(self):
        return self._completed_time

    def is_on_cooldown(self):
        if self._completed_time is None:
            return False
        time_since_last_completion = services.time_service().sim_now - self._completed_time
        return time_since_last_completion < interval_in_sim_minutes(self._cooldown)

    def get_localization_tokens(self):
        target_sim_info = self.get_required_target_sim_info()
        return (self._numerical_token, self._sim_info, target_sim_info, self._secondary_sim_info)

    def get_display_name(self):
        display_name = self.display_name
        if display_name is not None:
            return display_name(*self.get_localization_tokens())

    def get_display_tooltip(self):
        display_tooltip = self.display_tooltip
        if display_tooltip is not None:
            return display_tooltip(*self.get_localization_tokens())

    @property
    def score(self):
        if self._score_override is not None:
            return self._score_override
        return self._score

    @property
    def goal_status_override(self):
        return self._goal_status_override

    @property
    def completed_iterations(self):
        return self._count

    @property
    def max_iterations(self):
        return self._iterations

    @property
    def _numerical_token(self):
        return self.max_iterations

    @property
    def locked(self):
        return self._locked

    def toggle_locked_status(self):
        self._locked = not self._locked

    def validate_completion(self):
        if self._completed_time is not None:
            return
        if self.completed_iterations < self.max_iterations:
            return
        self.force_complete()

    def show_goal_awarded_notification(self):
        if self.goal_awarded_notification is None:
            return
        icon_override = IconInfoData(icon_resource=self.display_icon)
        secondary_icon_override = IconInfoData(obj_instance=self._sim_info)
        notification = self.goal_awarded_notification(self._sim_info)
        notification.show_dialog(additional_tokens=self.get_localization_tokens(), icon_override=icon_override, secondary_icon_override=secondary_icon_override)
