from event_testing import test_eventsfrom event_testing.event_data_tracker import EventDataTrackerfrom event_testing.resolver import SingleSimResolverimport servicesimport sims4.resources
class HouseholdMilestoneTracker(EventDataTracker):

    def _get_milestone_manager(self):
        return services.get_instance_manager(sims4.resources.Types.HOUSEHOLD_MILESTONE)

    @property
    def simless(self):
        return True

    @property
    def owner_sim_info(self):
        client = services.client_manager().get_first_client()
        if client is not None:
            return client.active_sim_info

    def post_to_gsi(self, message):
        pass

    def send_if_dirty(self):
        pass

    def update_objective(self, objective, current_value, objective_value, is_money, from_init=False):
        pass

    def complete_milestone(self, milestone, sim_info):
        super().complete_milestone(milestone, sim_info)
        if milestone.notification is not None:
            dialog = milestone.notification(sim_info, SingleSimResolver(sim_info))
            dialog.show_dialog()
        services.get_event_manager().process_event(test_events.TestEvent.UnlockEvent, sim_info=sim_info, unlocked=milestone)
