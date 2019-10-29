from sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableList, TunableReferenceimport servicesimport sims4.resourcesimport sims4.tuningimport situations.situation_goallogger = sims4.log.Logger('SituationGoalCompound', default_owner='bosee')
class SituationGoalCompound(situations.situation_goal.SituationGoal, AutoFactoryInit, HasTunableSingletonFactory):
    INSTANCE_TUNABLES = {'situation_goals': TunableList(description='\n            If any of the situation goal passes this situation goal will pass too.\n            ', tunable=TunableReference(description='\n                If this situation goal passes, pass this compound one.\n                ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION_GOAL)), unique_entries=True, minlength=2)}

    @classmethod
    def _verify_tuning_callback(cls):
        for situation_goal in cls.situation_goals:
            if isinstance(situation_goal, SituationGoalCompound):
                logger.error('Compound goal {} contains other compound goals. This might cause performance problems.', cls)

    def __init__(self, *args, reader=None, **kwargs):
        super().__init__(*args, reader=reader, **kwargs)
        self._situation_goal_instances = []
        for situation_goal in self.situation_goals:
            self._situation_goal_instances.append(situation_goal(*args, reader=reader, **kwargs))

    def setup(self):
        super().setup()
        for situation_goal in self._situation_goal_instances:
            situation_goal.setup()
            situation_goal.register_for_on_goal_completed_callback(self._sub_goal_completed_callback)

    def _decommision(self):
        super()._decommision()
        for situation_goal in self._situation_goal_instances:
            situation_goal._decommision()

    def _run_goal_completion_tests(self, sim_info, event, resolver):
        current_return = False
        for situation_goal in self._situation_goal_instances:
            current_return = current_return or situation_goal._run_goal_completion_tests(self, sim_info, event, resolver)
        return current_return

    @property
    def completed_iterations(self):
        goal_to_find = self._most_completed_sub_goal()
        return goal_to_find.completed_iterations

    @property
    def max_iterations(self):
        goal_to_find = self._most_completed_sub_goal()
        return goal_to_find.max_iterations

    def _sub_goal_completed_callback(self, goal, goal_completed):
        if goal_completed:
            self._on_goal_completed(start_cooldown=True)
        else:
            self._on_iteration_completed()

    def _most_completed_sub_goal(self):
        return max(self._situation_goal_instances, key=lambda x: x.completed_iterations/x.max_iterations)
sims4.tuning.instances.lock_instance_tunables(SituationGoalCompound, score_on_iteration_complete=None, _iterations=1)