import randomfrom distributor.shared_messages import IconInfoDatafrom event_testing.resolver import DoubleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableRangefrom sims4.tuning.tunable_base import GroupNamesfrom situations.base_situation import _RequestUserDatafrom situations.bouncer.bouncer_request import SelectableSimRequestFactoryfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_complex import SituationComplexCommon, SituationStateData, CommonSituationState, TunableSituationJobAndRoleStatefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOptionfrom ui.ui_dialog_notification import TunableUiDialogNotificationSnippetimport services
class _NeighborHangoutState(CommonSituationState):
    pass

class NeighborGroupHangoutSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'player_sim_job_and_default_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and role state to put player Sims in. \n            '), 'neighbor_job_and_default_role_state': TunableSituationJobAndRoleState(description='\n            The Situation Job and Role State for the neighbor.\n            '), 'number_of_neighbors': TunableRange(description="\n            The number of other neighbors to bring to the situation.  If\n            there aren't enough neighbors then none will be generated to\n            bring.\n            ", tunable_type=int, default=1, minimum=1), '_hangout_state': _NeighborHangoutState.TunableFactory(description='\n            The state for the neighbor to come in and hang out with the player.\n            ', tuning_group=GroupNames.STATE), '_arrival_notification': TunableUiDialogNotificationSnippet(description='\n            Localized string to display as a notification when the first Sim\n            arrives on the player lot.\n            '), 'scheduling_tests': TunableTestSet(description="\n            Tunable tests that run before scheduling this situation. If they\n            pass for at least one Sim we find that matches the job filter, the\n            situation is weighed and considered for scheduling. Otherwise it\n            does not take up a slot in the situation manager because the zone\n            director won't consider it. Participants: Actor = active sim,\n            TargetSim = Sim from Job filter. Tests fail if TargetSim is None.\n            ")}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._tns_popped = False

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _NeighborHangoutState, factory=cls._hangout_state),)

    @classmethod
    def situation_meets_starting_requirements(cls, **kwargs):
        neighbor_results = cls.get_filter_results_for_job()
        for neighbor_result in neighbor_results:
            resolver = DoubleSimResolver(services.active_sim_info(), neighbor_result.sim_info)
            if cls.scheduling_tests.run_tests(resolver):
                return True
        return False

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.neighbor_job_and_default_role_state.job, cls.neighbor_job_and_default_role_state.role_state), (cls.player_sim_job_and_default_role_state.job, cls.player_sim_job_and_default_role_state.role_state)]

    @classmethod
    def get_filter_results_for_job(cls):
        active_sim_info = services.active_sim_info()
        neighbor_results = services.sim_filter_service().submit_filter(cls.neighbor_job_and_default_role_state.job.filter, callback=None, requesting_sim_info=active_sim_info, allow_yielding=False, blacklist_sim_ids={sim_info.sim_id for sim_info in services.active_household()}, gsi_source_fn=cls.get_sim_filter_gsi_name)
        return neighbor_results

    @classmethod
    def get_predefined_guest_list(cls):
        neighbor_results = cls.get_filter_results_for_job()
        if not neighbor_results:
            return
        if len(neighbor_results) > cls.number_of_neighbors:
            neighbors = random.sample(neighbor_results, cls.number_of_neighbors)
        else:
            neighbors = neighbor_results
        active_sim_info = services.active_sim_info()
        guest_list = SituationGuestList(invite_only=True, host_sim_id=neighbor_results[0].sim_info.sim_id, filter_requesting_sim_id=active_sim_info.sim_id)
        for neighbor in neighbors:
            guest_list.add_guest_info(SituationGuestInfo(neighbor.sim_info.sim_id, cls.neighbor_job_and_default_role_state.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP, expectation_preference=True))
        return guest_list

    def start_situation(self):
        super().start_situation()
        services.get_event_manager().register_single_event(self, TestEvent.SimActiveLotStatusChanged)
        self._change_state(self._hangout_state())

    def _issue_requests(self):
        super()._issue_requests()
        request = SelectableSimRequestFactory(self, callback_data=_RequestUserData(), job_type=self.player_sim_job_and_default_role_state.job, exclusivity=self.exclusivity)
        self.manager.bouncer.submit_request(request)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.SimActiveLotStatusChanged and not self._tns_popped:
            sim = sim_info.get_sim_instance()
            if sim is not None and (sim.is_on_active_lot() and self.is_sim_in_situation(sim)) and self.sim_has_job(sim, self.neighbor_job_and_default_role_state.job):
                active_sim = services.get_active_sim()
                if active_sim is not None:
                    dialog = self._arrival_notification(active_sim)
                    dialog.show_dialog(icon_override=IconInfoData(obj_instance=sim), secondary_icon_override=IconInfoData(obj_instance=active_sim))
                    self._tns_popped = True
                    services.get_event_manager().unregister_single_event(self, TestEvent.SimActiveLotStatusChanged)
lock_instance_tunables(NeighborGroupHangoutSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)