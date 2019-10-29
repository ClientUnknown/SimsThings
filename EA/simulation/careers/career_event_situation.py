from distributor.ops import BuildBuyLockUnlockfrom event_testing.resolver import SingleSimResolverfrom role.role_state import RoleStatefrom sims4.localization import TunableLocalizedStringfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableTuple, OptionalTunable, TunableEnumEntry, TunableList, TunableReferencefrom situations.bouncer.bouncer_types import BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateDatafrom situations.situation_job import SituationJobfrom situations.situation_time_jump import SITUATION_TIME_JUMP_DISALLOWfrom situations.situation_travel_behavior import _SituationTravelRequestDisallow, SituationTravelRequestTypefrom situations.situation_types import SituationCreationUIOption, SituationUserFacingTypeimport distributor.systemimport servicesimport sims4.resourcesCAREER_SESSION_EXTENDED = 'career_session_extended'
class CareerEventSituation(SituationComplexCommon):

    class _SituationTravelRequestCareerEvent(_SituationTravelRequestDisallow):

        def __call__(self, user_facing_situation, travel_situation_type, travel_request_fn, is_career_event=False, **kwargs):
            if is_career_event:
                return travel_request_fn()
            if self.dialog is not None:
                dialog = self.dialog(user_facing_situation._sim, SingleSimResolver(user_facing_situation._sim))
                dialog.show_dialog()

        @property
        def restrict(self):
            return SituationTravelRequestType.CAREER_EVENT

    INSTANCE_TUNABLES = {'user_job': TunableTuple(description='\n            The job and role which the career Sim is placed into.\n            ', situation_job=SituationJob.TunableReference(description='\n                A reference to a SituationJob that can be performed at this Situation.\n                '), role_state=RoleState.TunableReference(description='\n                A role state the sim assigned to the job will perform.\n                ')), 'build_buy_lock_reason': OptionalTunable(description='\n            If enabled then build buy will be disabled during this situation.\n            ', tunable=TunableLocalizedString(description='\n                The reason build buy is locked. For this case, it is because \n                build buy is not allowed during active career. Used on the disabled \n                buildbuy button in the HUD.\n                ')), 'travel_request_behavior': _SituationTravelRequestCareerEvent.TunableFactory(), 'user_facing_type_override': OptionalTunable(description="\n            If enabled, sets and override for the type of user facing career\n            event this is. If this is disabled, it'll be defaulted to\n            CAREER_EVENT. This is mostly used by UI and in general should not be\n            necessary. In some cases, like Acting, we want to indicate to UI\n            that this is different from other career events.\n            ", tunable=TunableEnumEntry(description='\n                The situation event type to override this to.\n                ', tunable_type=SituationUserFacingType, default=SituationUserFacingType.CAREER_EVENT, invalid_enums=(SituationUserFacingType.CAREER_EVENT,))), 'destroy_situations_on_remove': TunableList(description='\n            Other situations to destroy when this situation is being destroyed.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.SITUATION)))}
    REMOVE_INSTANCE_TUNABLES = ('_resident_job', 'recommended_job_object_notification', 'recommended_job_object_text', 'force_invite_only', 'duration', 'targeted_situation', '_relationship_between_job_members', '_implies_greeted_status', '_survives_active_household_change') + Situation.SITUATION_START_FROM_UI_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._sim = None
        self._career_session_extended = False
        reader = self._seed.custom_init_params_reader
        if reader is not None:
            self._career_session_extended = reader.read_bool(CAREER_SESSION_EXTENDED, False)

    @classmethod
    def _states(cls):
        return (SituationStateData(1, CareerEventSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.user_job.situation_job, cls.user_job.role_state)]

    @classmethod
    def default_job(cls):
        return cls.user_job.situation_job

    def _send_build_buy_lock(self):
        if self.build_buy_lock_reason is not None:
            op = BuildBuyLockUnlock(True, self.build_buy_lock_reason)
            distributor.system.Distributor.instance().add_op_with_no_owner(op)

    def start_situation(self):
        super().start_situation()
        self._change_state(CareerEventSituationState())
        self._send_build_buy_lock()

    def load_situation(self):
        result = super().load_situation()
        if result:
            self._send_build_buy_lock()
        return result

    def on_remove(self):
        super().on_remove()
        if self.build_buy_lock_reason is not None:
            op = BuildBuyLockUnlock(False)
            distributor.system.Distributor.instance().add_op_with_no_owner(op)
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is not None:
            for situation_type in self.destroy_situations_on_remove:
                for situation_to_destroy in situation_manager.get_situations_by_type(situation_type):
                    if situation_to_destroy is not None:
                        situation_manager.destroy_situation_by_id(situation_to_destroy.id)

    @property
    def user_facing_type(self):
        if self.user_facing_type_override:
            return self.user_facing_type_override
        return SituationUserFacingType.CAREER_EVENT

    def build_situation_start_message(self):
        msg = super().build_situation_start_message()
        msg.is_active_career = True
        msg.has_stayed_late = self._career_session_extended
        return msg

    def build_situation_duration_change_op(self):
        msg = super().build_situation_duration_change_op()
        msg.has_stayed_late = self._career_session_extended
        return msg

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._sim = sim

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        writer.write_bool(CAREER_SESSION_EXTENDED, self._career_session_extended)

    def get_situation_goal_actor(self):
        return self._sim.sim_info

    def on_career_session_extended(self, new_duration):
        self._career_session_extended = True
        self.change_duration(new_duration)
lock_instance_tunables(CareerEventSituation, exclusivity=BouncerExclusivityCategory.NEUTRAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, time_jump=SITUATION_TIME_JUMP_DISALLOW)
class CareerEventSituationState(SituationState):
    pass
