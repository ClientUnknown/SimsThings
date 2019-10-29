import randomfrom event_testing.resolver import DoubleSimResolverfrom interactions.utils.loot import LootActionsfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableListfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, TunableSituationJobAndRoleState, CommonSituationState, SituationStateData, CommonInteractionCompletedSituationState, SituationStatefrom situations.situation_guest_list import SituationGuestInfo, SituationGuestListfrom situations.situation_types import SituationCreationUIOptionfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport services
class _StartSituationState(SituationState):

    def _on_set_sim_role_state(self, sim, *args, **kwargs):
        super()._on_set_sim_role_state(sim, *args, **kwargs)
        relationship_tracker = sim.sim_info.relationship_tracker
        for sim_info in services.active_household():
            if relationship_tracker.has_bit(sim_info.sim_id, RelationshipGlobalTuning.NEIGHBOR_GIVEN_KEY_RELATIONSHIP_BIT):
                self._change_state(self.owner._hangout_state())
                return
        self._change_state(self.owner._knock_on_door_state())

class _KnockOnDoorState(CommonInteractionCompletedSituationState):

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner._wait_to_be_greeted())

class _NeighborWaitToBeGreetedState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'early_exit_loot': TunableList(description='\n            A list of loot to apply between the neighbor and the active\n            household Sims if this stiuation state times out.\n            ', tunable=LootActions.TunableReference(description='\n                A loot action applied to all of the active household Sims if this\n                situation state times out.\n                ')), 'early_exit_notification': TunableUiDialogNotificationSnippet(description='\n            Notification that will be shown when this situation state times\n            out.\n            ')}

    def __init__(self, *args, early_exit_loot=tuple(), early_exit_notification=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._early_exit_loot = early_exit_loot
        self._early_exit_notification = early_exit_notification

    def _on_interaction_of_interest_complete(self, **kwargs):
        self._change_state(self.owner._hangout_state())

    def timer_expired(self):
        for sim_info in services.active_household():
            resolver = DoubleSimResolver(sim_info, self.owner._neighbor_sim.sim_info)
            for loot_action in self._early_exit_loot:
                loot_action.apply_to_resolver(resolver)
        resolver = DoubleSimResolver(services.active_sim_info(), self.owner._neighbor_sim.sim_info)
        early_exit_notification = self._early_exit_notification(services.active_sim_info(), resolver=resolver)
        early_exit_notification.show_dialog()
        self.owner._self_destruct()

class _NeighborHangoutState(CommonSituationState):

    def timer_expired(self):
        self.owner._self_destruct()

class NeighborReactToYouSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'_knock_on_door_state': _KnockOnDoorState.TunableFactory(description='\n            Situation State for the Sim to knock on the door.\n            ', locked_args={'time_out': None, 'allow_join_situation': True}), '_wait_to_be_greeted': _NeighborWaitToBeGreetedState.TunableFactory(description='\n            Situation State for the Sim to wait to be greeted.\n            ', locked_args={'allow_join_situation': True}), '_hangout_state': _NeighborHangoutState.TunableFactory(description='\n            Situation state for the Sim to hang out for a while.\n            ', locked_args={'allow_join_situation': True}), '_starting_neighbor_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the neighbor.\n            ')}
    REMOVE_INSTANCE_TUNABLES = ('_buff', 'targeted_situation', '_resident_job', '_relationship_between_job_members', 'audio_sting_on_start', 'force_invite_only', 'screen_slam_gold', 'screen_slam_silver', 'screen_slam_bronze', 'screen_slam_no_medal') + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES + Situation.SITUATION_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _StartSituationState), SituationStateData(2, _KnockOnDoorState, factory=cls._knock_on_door_state), SituationStateData(3, _NeighborWaitToBeGreetedState, factory=cls._wait_to_be_greeted), SituationStateData(4, _NeighborHangoutState, factory=cls._hangout_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls._starting_neighbor_job_and_role_state.job, cls._starting_neighbor_job_and_role_state.role_state)]

    @classmethod
    def default_job(cls):
        pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._neighbor_sim = None

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._neighbor_sim = sim

    @classmethod
    def get_predefined_guest_list(cls):
        active_sim_info = services.active_sim_info()
        neighbor_sim_id = cls._get_neighbor()
        if neighbor_sim_id is None:
            return
        guest_list = SituationGuestList(invite_only=True, host_sim_id=neighbor_sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        guest_list.add_guest_info(SituationGuestInfo(neighbor_sim_id, cls._starting_neighbor_job_and_role_state.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_MEDIUM, expectation_preference=True))
        return guest_list

    @classmethod
    def _get_neighbor(cls):
        active_sim_info = services.active_sim_info()
        neighbors = services.sim_filter_service().submit_filter(cls._starting_neighbor_job_and_role_state.job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not neighbors:
            return
        neighbor_sim_infos_at_home = [result.sim_info for result in neighbors if result.sim_info.is_at_home]
        neighbor_sim_id = random.choice(neighbor_sim_infos_at_home).sim_id if neighbor_sim_infos_at_home else None
        return neighbor_sim_id

    def start_situation(self):
        super().start_situation()
        self._change_state(_StartSituationState())
lock_instance_tunables(NeighborReactToYouSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)