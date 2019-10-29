from sims4.common import Pack, is_available_packfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import OptionalTunable, TunableEnumEntryfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import BouncerRequestFactoryfrom situations.bouncer.bouncer_types import BouncerRequestPriority, BouncerExclusivityCategoryfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, TunableSituationJobAndRoleState, SituationStateDatafrom situations.situation_types import SituationCreationUIOptionfrom tunable_time import TunableTimeOfDayfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetfrom world.region import Regionimport services
class _BarSpecialNightSituationState(SituationState):
    pass

class BarSpecialNightSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'end_time': TunableTimeOfDay(description='\n            The time that this situation will end.\n            '), 'special_night_patron': TunableSituationJobAndRoleState(description='\n            The job and role of the special night patron.\n            '), 'notification': TunableUiDialogNotificationSnippet(description='\n            The notification to display when this object reward is granted\n            to the Sim. There is one additional token provided: a string\n            representing a bulleted list of all individual rewards granted.\n            '), 'starting_entitlement': OptionalTunable(description='\n            If enabled, this situation is locked by an entitlement. Otherwise,\n            this situation is available to all players.\n            ', tunable=TunableEnumEntry(description='\n                Pack required for this event to start.\n                ', tunable_type=Pack, default=Pack.BASE_GAME)), 'valid_regions': TunableWhiteBlackList(description='\n            A white/black list of regions in which this schedule entry is valid.\n            For instance, some bar nights might not be valid in the Jungle bar.\n            ', tunable=Region.TunableReference(pack_safe=True))}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _BarSpecialNightSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.special_night_patron.job, cls.special_night_patron.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        if not cls.valid_regions.test_item(services.current_region()):
            return False
        if cls.starting_entitlement is None:
            return True
        return is_available_pack(cls.starting_entitlement)

    def _get_duration(self):
        time_now = services.time_service().sim_now
        return time_now.time_till_next_day_time(self.end_time).in_minutes()

    def start_situation(self):
        super().start_situation()
        self._change_state(_BarSpecialNightSituationState())
        dialog = self.notification(services.active_sim_info())
        dialog.show_dialog()

    def _issue_requests(self):
        request = BouncerRequestFactory(self, callback_data=_RequestUserData(role_state_type=self.special_night_patron.role_state), job_type=self.special_night_patron.job, request_priority=BouncerRequestPriority.BACKGROUND_LOW, user_facing=self.is_user_facing, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)
lock_instance_tunables(BarSpecialNightSituation, exclusivity=BouncerExclusivityCategory.VENUE_BACKGROUND, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE, duration=0, _implies_greeted_status=False)