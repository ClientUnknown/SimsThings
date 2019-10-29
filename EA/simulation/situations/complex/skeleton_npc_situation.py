from event_testing.resolver import SingleSimResolverfrom situations.service_npcs.modify_lot_items_tuning import ModifyAllLotItemsfrom situations.situation import Situationfrom situations.situation_complex import CommonSituationState, SituationStateData, TunableSituationJobAndRoleState, SituationComplexCommon, CommonInteractionCompletedSituationStatefrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom world.dynamic_spawn_point import DynamicSpawnPointElementimport servicesimport situations
class BeSkeleton(CommonSituationState):

    def timer_expired(self):
        self._change_state(self.owner.end_skeleton_state())

class EndSkeleton(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'leaving_notification': TunableUiDialogNotificationSnippet(description='\n            The notification that is shown when a summoned Skeleton NPC leaves.\n            ')}

    def __init__(self, *args, leaving_notification, **kwargs):
        super().__init__(*args, **kwargs)
        self.leaving_notification = leaving_notification

    def _on_interaction_of_interest_complete(self, **kwargs):
        skeleton = self.owner.get_skeleton()
        resolver = SingleSimResolver(skeleton.sim_info)
        leaving_notification = self.leaving_notification(skeleton, resolver=resolver)
        leaving_notification.show_dialog()
        self.owner._self_destruct()

    def _additional_tests(self, sim_info, event, resolver):
        skeleton = self.owner.get_skeleton()
        if skeleton is not None and self.owner.get_skeleton().sim_info is sim_info:
            return True
        return False

class SkeletonNPCSituation(situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'skeleton_job_and_role_state': TunableSituationJobAndRoleState(description='\n            Job and Role State for the Skeleton Sim in this situation.\n            '), 'be_skeleton_state': BeSkeleton.TunableFactory(description='\n            Situation State used by the skeleton.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'end_skeleton_state': EndSkeleton.TunableFactory(description='\n            The state that the skeleton goes into when then situation ends.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP), 'skeleton_spawn_point': DynamicSpawnPointElement.TunableFactory(), 'fake_perform_job': ModifyAllLotItems.TunableFactory()}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._interaction = self._seed.extra_kwargs.get('interaction', None)
        self._dynamic_spawn_point = None

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _states(cls):
        return (SituationStateData(1, BeSkeleton, factory=cls.be_skeleton_state), SituationStateData(2, EndSkeleton, factory=cls.end_skeleton_state))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.skeleton_job_and_role_state.job, cls.skeleton_job_and_role_state.role_state)]

    def start_situation(self):
        super().start_situation()
        self._dynamic_spawn_point = self.skeleton_spawn_point(self._interaction)
        self._dynamic_spawn_point.start()
        self._change_state(self.be_skeleton_state())

    def _destroy(self):
        skeleton = self.get_skeleton()
        self._remove_skeleton_sim_info(skeleton)
        super()._destroy()
        if self._dynamic_spawn_point is not None:
            self._dynamic_spawn_point.stop()
            self._dynamic_spawn_point = None

    @classmethod
    def should_load_after_time_jump(cls, seed):
        elapsed_time = services.current_zone().time_elapsed_since_last_save().in_minutes()
        if elapsed_time > seed.duration_override:
            modifier = cls.fake_perform_job()
            modifier.modify_objects()
            skeleton = next(seed._guest_list.invited_sim_infos_gen(), None)
            cls._remove_skeleton_sim_info(skeleton)
            return False
        seed.duration_override -= elapsed_time
        return True

    def get_skeleton(self):
        for sim in self._situation_sims:
            return sim

    @classmethod
    def _remove_skeleton_sim_info(cls, skeleton):
        if skeleton is not None:
            services.sim_info_manager().remove_permanently(skeleton.sim_info)
