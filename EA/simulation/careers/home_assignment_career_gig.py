import randomfrom careers.career_enums import GigResultfrom careers.career_gig import Gigfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableReference, OptionalTunable, TunablePercent, TunableTuplefrom tunable_time import TunableTimeSpanimport servicesimport sims4logger = sims4.log.Logger('HomeAssignmentGig', default_owner='rrodgers')
class HomeAssignmentGig(Gig):
    INSTANCE_TUNABLES = {'gig_picker_localization_format': TunableLocalizedStringFactory(description='\n            String used to format the description in the gig picker. Currently\n            has tokens for name, payout, gig time, tip title, and tip text.\n            '), 'gig_assignment_aspiration': TunableReference(description='\n            An aspiration to use as the assignment for this gig. The objectives\n            of this aspiration\n            ', manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='AspirationGig'), 'bonus_gig_aspiration_tuning': OptionalTunable(description='\n            Tuning for the bonus gig aspiration.  This is optional, but if the\n            aspiration is completed, it results in a chance for a better\n            outcome.\n            ', tunable=TunableTuple(bonus_gig_aspiration=TunableReference(description="\n                    The bonus aspiration to use as part of this gig's \n                    assignments.\n                    ", manager=services.get_instance_manager(sims4.resources.Types.ASPIRATION), class_restrictions='Aspiration'), great_success_chance=TunablePercent(description='\n                    Chance of a SUCCESS outcome being upgraded to \n                    GREAT_SUCCESS.\n                    ', default=0.0))), 'great_success_remaining_time': OptionalTunable(description='\n            If the aspiration for this gig is completed with more than this\n            amount of time left, the gig will be considered a great success.\n            ', tunable=TunableTimeSpan())}

    @classmethod
    def get_aspiration(cls):
        return cls.gig_assignment_aspiration

    def set_up_gig(self):
        super().set_up_gig()
        aspiration_tracker = self._owner.aspiration_tracker
        aspiration_tracker.reset_milestone(self.gig_assignment_aspiration)
        self.gig_assignment_aspiration.register_callbacks()
        aspiration_tracker.process_test_events_for_aspiration(self.gig_assignment_aspiration)
        if self.bonus_gig_aspiration_tuning is not None and self.bonus_gig_aspiration_tuning.bonus_gig_aspiration is not None:
            aspiration_tracker.reset_milestone(self.bonus_gig_aspiration_tuning.bonus_gig_aspiration)
            self.bonus_gig_aspiration_tuning.bonus_gig_aspiration.register_callbacks()
            aspiration_tracker.process_test_events_for_aspiration(self.bonus_gig_aspiration_tuning.bonus_gig_aspiration)

    def load_gig(self, gig_proto_buff):
        super().load_gig(gig_proto_buff)
        self.gig_assignment_aspiration.register_callbacks()

    def _determine_gig_outcome(self):
        completed_objectives = 0
        aspiration_tracker = self._owner.aspiration_tracker
        if aspiration_tracker is not None:
            for objective in self.gig_assignment_aspiration.objectives:
                if aspiration_tracker.objective_completed(objective):
                    completed_objectives += 1
            completed_bonus_objectives = 0
            if self.bonus_gig_aspiration_tuning.bonus_gig_aspiration is not None:
                for objective in self.bonus_gig_aspiration_tuning.bonus_gig_aspiration.objectives:
                    if aspiration_tracker.objective_completed(objective):
                        completed_bonus_objectives += 1
        else:
            completed_objectives = len(self.gig_assignment_aspiration.objectives)
            completed_bonus_objectives = 0
        remaining_time = self._upcoming_gig_time - services.time_service().sim_now
        if completed_objectives < len(self.gig_assignment_aspiration.objectives):
            if completed_objectives == 0:
                self._gig_result = GigResult.CRITICAL_FAILURE
            elif self.critical_failure_test is not None:
                resolver = self.get_resolver_for_gig()
                if self.critical_failure_test.run_tests(resolver=resolver):
                    self._gig_result = GigResult.CRITICAL_FAILURE
                else:
                    self._gig_result = GigResult.FAILURE
            else:
                self._gig_result = GigResult.FAILURE
        elif self.great_success_remaining_time and remaining_time > self.great_success_remaining_time():
            self._gig_result = GigResult.GREAT_SUCCESS
        elif completed_bonus_objectives > 0:
            if self.bonus_gig_aspiration_tuning and self.bonus_gig_aspiration_tuning.great_success_chance and random.random() <= self.bonus_gig_aspiration_tuning.great_success_chance:
                self._gig_result = GigResult.GREAT_SUCCESS
            else:
                self._gig_result = GigResult.SUCCESS
        else:
            self._gig_result = GigResult.SUCCESS

    def get_overmax_evaluation_result(self, reward_text, overmax_level, *args, **kwargs):
        return super().get_overmax_evaluation_result(reward_text, overmax_level, *args, **kwargs)

    def send_prep_task_update(self):
        pass

    @classmethod
    def build_gig_msg(cls, msg, sim, **kwargs):
        super().build_gig_msg(msg, sim, **kwargs)
        msg.aspiration_id = cls.gig_assignment_aspiration.guid64

    def treat_work_time_as_due_date(self):
        return True
lock_instance_tunables(HomeAssignmentGig, gig_prep_tasks=None, audio_on_prep_task_completion=None, career_events=None, gig_cast_rel_bit_collection_id=None, gig_cast=None, end_of_gig_dialog=None, payout_stat_data=None)