from business.business_employee_situation_mixin import BusinessEmployeeSituationMixinfrom event_testing import test_eventsfrom event_testing.test_events import TestEventfrom interactions.context import InteractionContextfrom interactions.priority import Priorityfrom restaurants.restaurant_host_log_handler import log_host_actionfrom restaurants.restaurant_tuning import get_restaurant_zone_directorfrom sims4.tuning.tunable import TunablePackSafeReference, Tunable, TunableReferencefrom situations.complex.staffed_object_situation_mixin import StaffedObjectSituationMixinfrom situations.situation import Situationfrom situations.situation_complex import CommonInteractionCompletedSituationState, SituationComplexCommon, SituationStateData, CommonSituationState, TunableInteractionOfInterestfrom situations.situation_job import SituationJobfrom socials import groupimport alarmsimport clockimport servicesimport sims4.resources
class HostSituationStateMixin:

    def get_valid_group_to_seat(self):
        group = self.owner.get_group_to_seat()
        if group is None:
            return
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return
        situation = situation_manager.get(group)
        if situation is None or situation.num_of_sims <= 0:
            self.owner.remove_group_to_seat(group)
            return
        else:
            zone_director = get_restaurant_zone_director()
            if zone_director is not None and not zone_director.can_find_seating_for_group(situation.get_num_sims_in_job(None), consider_occupied=situation.is_player_group()):
                return
        return situation

class _ArrivingState(CommonInteractionCompletedSituationState, HostSituationStateMixin):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self._test_event_register(TestEvent.GroupWaitingToBeSeated)
        log_host_action('Starting Arriving State', 'Success')

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if self.owner is not None and self.owner.get_staff_member() is not None:
            group = self.get_valid_group_to_seat()
            if group is None:
                return
            log_host_action('Leaving Arriving State for Right This Way State because there is someone waiting for a table.', 'Success')
            self._change_state(self.owner._right_this_way_situation_state())

    def _on_interaction_of_interest_complete(self, **kwargs):
        log_host_action('Leaving Arriving State', 'Success')
        self._change_state(self.owner._host_station_situation_state())

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner.sim_of_interest(sim_info):
            return True
        return False

class _HostStationState(CommonSituationState, HostSituationStateMixin):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        log_host_action('Starting Host Station State', 'Success')
        self._test_event_register(TestEvent.GroupWaitingToBeSeated)
        self._test_event_register(TestEvent.InteractionComplete)
        group = self.get_valid_group_to_seat()
        if group is None:
            return
        log_host_action('Leaving Host Station State for existing waiting table', 'Success')
        self._change_state(self.owner._right_this_way_situation_state())

    def handle_event(self, sim_info, event, resolver):
        group = None
        if event == TestEvent.GroupWaitingToBeSeated:
            group = self.get_valid_group_to_seat()
        if self.owner.sim_of_interest(sim_info):
            group = self.get_valid_group_to_seat()
        if event == TestEvent.InteractionComplete and self.owner is not None and group is None:
            return
        log_host_action('Leaving Host Station State for discovered waiting table', 'Success')
        self._change_state(self.owner._right_this_way_situation_state())

class _RightThisWayState(CommonInteractionCompletedSituationState, HostSituationStateMixin):
    FACTORY_TUNABLES = {'max_attempts_to_run_social': Tunable(description='\n            The number of times that a host can fail to run the Right This Way\n            social before giving up and just showing the Sims to their table.\n            ', tunable_type=int, default=5)}

    def __init__(self, *args, max_attempts_to_run_social=0, **kwargs):
        super().__init__(*args, **kwargs)
        self._group = None
        self._fail_count = 0
        self.max_attempts_to_run_social = max_attempts_to_run_social

    def on_activate(self, reader=None):
        super().on_activate(reader=reader)
        log_host_action('Starting Right This Way State', 'Success')
        self._group = self.get_valid_group_to_seat()
        if self._group is None:
            self.owner._change_state(self.owner._arriving_situation_state())
            return
        if not self.owner.push_right_this_way_social(self._group):
            log_host_action('Leaving Right This Way State', 'Failed to Push Right This Way Interaction')
            self.owner._change_state(self.owner._show_to_table_situation_state())
            return
        log_host_action('During Right This Way State', 'Pushed Right This Way Interaction')
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.InteractionExitedPipeline and (resolver(self._interaction_of_interest) and self.owner.sim_of_interest(sim_info)) and not resolver.interaction.is_finishing_naturally:
            log_host_action('During Right This Way State', 'Interaction left pipeline without finishing naturally.')
            self._fail_count += 1
            if self._fail_count < self.max_attempts_to_run_social and self.owner.push_right_this_way_social(self._group):
                log_host_action('During Right This Way State', 'Pushed Right This Way Interaction Again.')
                return
            log_host_action('Leaving Right This Way State', 'Max Attempts to Push Affordance')
            self.owner._change_state(self.owner._show_to_table_situation_state())

    def _on_interaction_of_interest_complete(self, **kwargs):
        log_host_action('Leaving Right This Way State', 'Success')
        self.owner._change_state(self.owner._show_to_table_situation_state())

    def _additional_tests(self, sim_info, event, resolver):
        if self.owner is not None and self.owner.sim_of_interest(sim_info):
            return True
        return False

    def timer_expired(self):
        log_host_action('During Right This Way State', 'Failed - Timer expired.')
        self.owner._change_state(self.owner._show_to_table_situation_state())

class _ShowToTableState(CommonSituationState, HostSituationStateMixin):
    FACTORY_TUNABLES = {'interaction_of_interest': TunableInteractionOfInterest(description='\n                 The interaction that when it exits the interaction \n                 pipeline causes this particular state to change back to the\n                 arrival state.\n                 ')}

    def __init__(self, *args, interaction_of_interest, **kwargs):
        super().__init__(*args, **kwargs)
        self._group = None
        self._interaction_of_interest = interaction_of_interest

    def handle_event(self, sim_info, event, resolver):
        if event != TestEvent.InteractionExitedPipeline:
            return
        if self.owner is None or not self.owner.sim_of_interest(sim_info):
            return
        if not resolver(self._interaction_of_interest):
            return
        if self._group is not None:
            for sim in self._group.all_sims_in_situation_gen():
                services.get_event_manager().process_event(test_events.TestEvent.RestaurantTableClaimed, sim_info=sim.sim_info)
        log_host_action('Leaving Show To Table State', 'Success')
        self._change_state(self.owner._arriving_situation_state())

    def on_activate(self, reader=None):
        super().on_activate(reader)
        log_host_action('Starting Show To Table State', 'Success')
        self._group = self.get_valid_group_to_seat()
        if self._group is None:
            self._change_state(self.owner._arriving_situation_state())
            return
        if not self.owner.push_show_table_interactions(self._group):
            log_host_action('Leaving Show To Table State', 'Failed - Leaving without performing interactions.')
            self._change_state(self.owner._arriving_situation_state())
        for custom_key in self._interaction_of_interest.custom_keys_gen():
            self._test_event_register(TestEvent.InteractionExitedPipeline, custom_key)

    def timer_expired(self):
        log_host_action('During Show To Table State', 'Failed - Timeout occured.')
        self.owner._change_state(self.owner._arriving_situation_state())

class HostSituation(BusinessEmployeeSituationMixin, StaffedObjectSituationMixin, SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_job': SituationJob.TunableReference(description='\n            The job that a staff member will be in during the situation.\n            '), '_arriving_situation_state': _ArrivingState.TunableFactory(description='\n            The situation state used for when a Sim is arriving as a staff \n            member.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_arriving_situation_state'), '_host_station_situation_state': _HostStationState.TunableFactory(description='\n            The situation state used for when a Host is idling at the host station.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_host_station_situation_state'), '_show_to_table_situation_state': _ShowToTableState.TunableFactory(description='\n            The situation state used for when a Host is showing a group to\n            their table.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_show_to_table_situation_state'), '_right_this_way_situation_state': _RightThisWayState.TunableFactory(description='\n            The situation state used to get the Host to run the "Right this way" \n            social before routing to the table with the guests.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='04_right_this_way_situation_state'), 'right_this_way_interaction': TunableReference(description='\n            The interaction that the Host runs before both the Host and the\n            guests start routing to the table.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), class_restrictions='SuperInteraction'), 'host_show_to_table_interaction': TunablePackSafeReference(description='\n            The interaction to push on the host that will "show" the guests\n            to their table.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'requesting_sim_show_to_table_interaction': TunablePackSafeReference(description='\n            The interaction to push on the sim requesting a table that will \n            get the guest close to their table so a social can be pushed on them\n            to show them the table.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'guest_take_seat_interaction': TunablePackSafeReference(description='\n            The interaction to push on each of the guests in the group that\n            targets their chosen seat.\n            ', manager=services.get_instance_manager(sims4.resources.Types.INTERACTION)), 'host_head_start_in_sim_minutes': Tunable(description='\n            The number of sim minutes that the guests will wait after the host\n            begins to show them to their table before they start to follow.\n            ', tunable_type=int, default=1)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._alarm_handle = None

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _ArrivingState, factory=cls._arriving_situation_state), SituationStateData(2, _HostStationState, factory=cls._host_station_situation_state), SituationStateData(3, _ShowToTableState, factory=cls._show_to_table_situation_state), SituationStateData(4, _RightThisWayState, factory=cls._right_this_way_situation_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls._arriving_situation_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(self._arriving_situation_state())

    def _on_set_sim_job(self, sim, job_type):
        super()._on_set_sim_job(sim, job_type)
        self._start_work_duration()

    def get_group_to_seat(self):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return
        return zone_director.get_next_group_id_to_seat()

    def remove_group_to_seat(self, group_id):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return
        return zone_director.remove_group_waiting_to_be_seated(group_id)

    def push_right_this_way_social(self, group):
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            return False
        else:
            host = self.get_staff_member()
            target = group.get_main_sim()
            if target is None:
                target = next(group.all_sims_in_situation_gen())
            context = InteractionContext(host, InteractionContext.SOURCE_SCRIPT, Priority.High)
            if not host.push_super_affordance(self.right_this_way_interaction, target, context):
                return False
        return True

    def push_show_table_interactions(self, group):
        if self.host_show_to_table_interaction is None or self.guest_take_seat_interaction is None:
            log_host_action('During Show To Table State', 'Failed - No Interactions to push on one of the Sims.')
            return False
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            log_host_action('During Show To Table State', "Failed - Can't find the zone director.")
            return False
        master_sim = group.get_main_sim()
        if master_sim is None:
            master_sim = next(group.all_sims_in_situation_gen())
        zone_director.claim_table(master_sim)
        return self.push_host_show_table_interaction(group, zone_director, master_sim)

    def push_host_show_table_interaction(self, group, zone_director, master_sim):
        host = self.get_staff_member()
        group_tables = zone_director.get_tables_by_group_id(group.id)
        if not group_tables:
            log_host_action('During Show To Table', 'Failed to push show to table interactions. Unable to find tables the group reserved.')
            return False
        context = InteractionContext(host, InteractionContext.SOURCE_SCRIPT, Priority.High)
        master_sim_context = InteractionContext(master_sim, InteractionContext.SOURCE_SCRIPT, Priority.High)
        object_manager = services.current_zone().object_manager
        table_id = group_tables.pop()
        table = object_manager.get(table_id)
        (master_sim_chair_id, _) = zone_director.get_sims_seat(master_sim)
        master_sim_chair = object_manager.get(master_sim_chair_id)
        if not host.push_super_affordance(self.host_show_to_table_interaction, table, context, saved_participants=[master_sim, master_sim_chair, None, None]):
            log_host_action('During Show To Table State', 'Failed to Push Host Interaction on {}'.format(host))
            return False
        log_host_action('During Show To Table State', 'Pushed Host Interaction on {}'.format(host))

        def timer_expired(handle):
            self.push_master_sim_interaction(group, table, master_sim, master_sim_context, host, master_sim_chair)
            self._alarm_handle = None

        self._alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(self.host_head_start_in_sim_minutes), timer_expired)
        return True

    def push_master_sim_interaction(self, group, table, master_sim, master_sim_context, host, master_sim_chair):
        if not master_sim.push_super_affordance(self.requesting_sim_show_to_table_interaction, table, master_sim_context, saved_participants=[host, master_sim_chair, None, None]):
            log_host_action('During Show To Table State', 'Failed to Push Master Sim Interaction on {}'.format(master_sim))
        else:
            log_host_action('During Show To Table State', 'Pushed Master Sim Interaction on {}'.format(master_sim))
        zone_director = get_restaurant_zone_director()
        if zone_director is None:
            log_host_action('During Show To Table State', 'Failed - unable to find zone director.')
            return
        for guest in group.all_sims_in_situation_gen():
            if guest is not master_sim:
                self.push_guest_take_seat_interaction(guest, zone_director)

    def push_guest_take_seat_interaction(self, guest, zone_director):
        (seat_id, _) = zone_director.get_sims_seat(guest)
        if seat_id is None:
            log_host_action('During Show To Table Seat', "Failed - couldn't find a seat for the Sim {}.".format(guest))
            return
        seat = services.current_zone().object_manager.get(seat_id)
        if seat is None:
            log_host_action('During Show To Table Seat', "Failed - couldn't find a seat for the Sim {}.".format(guest))
            return
        context = InteractionContext(guest, InteractionContext.SOURCE_SCRIPT, Priority.High)
        if not guest.push_super_affordance(self.guest_take_seat_interaction, seat, context):
            log_host_action('During Show To Table State', 'Failed to Push Guest Interaction')
        else:
            log_host_action('During Show To Table State', 'Push Guest Interaction on {}'.format(guest))

    def on_remove(self):
        super().on_remove()
        if self._alarm_handle is not None:
            self._alarm_handle.cancel()
            self._alarm_handle = None
