from event_testing.milestone import Milestonefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import OptionalTunablefrom ui.ui_dialog_notification import UiDialogNotificationimport servicesimport sims4.logimport sims4.resourceslogger = sims4.log.Logger('Milestone')
class HouseholdMilestone(Milestone, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.HOUSEHOLD_MILESTONE)):
    INSTANCE_TUNABLES = {'notification': OptionalTunable(description='\n            If enabled then we will display a notification when this milestone\n            is completed.\n            ', tunable=UiDialogNotification.TunableFactory(description='\n                This text will display in a notification pop up when completed.\n                '))}

    @classmethod
    def handle_event(cls, sim_info, event, resolver):
        if sim_info is None:
            return
        if sim_info.household is None:
            logger.error("Household doesn't exist for milestone {} and SimInfo {}", cls, sim_info, owner='camilogarcia')
            return
        household_milestone_tracker = sim_info.household.household_milestone_tracker
        if household_milestone_tracker is None:
            return
        household_milestone_tracker.handle_event(cls, event, resolver)

    @classmethod
    def register_callbacks(cls):
        tests = [objective.objective_test for objective in cls.objectives]
        services.get_event_manager().register_tests(cls, tests)
