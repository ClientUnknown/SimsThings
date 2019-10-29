from _sims4_collections import frozendictimport randomfrom sims4.tuning.tunable import OptionalTunable, TunableTuple, TunableSimMinute, Tunable, TunableMapping, TunableReferencefrom situations.complex.staff_member_situation import StaffMemberSituationfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateData, CommonInteractionCompletedSituationStatefrom situations.situation_job import SituationJobimport servicesimport sims4EXERCISE_TIMEOUT = 'exercise'DO_STUFF_TIMEOUT = 'do_stuff'
class _ExerciseState(CommonSituationState):
    FACTORY_TUNABLES = {'exercise_timeout': OptionalTunable(description='\n            Optional tunable for when to end the exercise state. If this is\n            enabled then the exercise state will end and will take shower\n            afterwards. If this is disabled the situation will just stay in the\n            exercise state forever.\n            ', tunable=TunableTuple(min_time=TunableSimMinute(description='\n                    The length of time to wait before advancing to the\n                    take shower state.\n                    ', default=60), max_time=TunableSimMinute(description='\n                    The maximum time a visitor will spend on exercise state.\n                    ', default=60)))}

    def __init__(self, exercise_timeout, **kwargs):
        super().__init__(**kwargs)
        self._exercise_timeout = exercise_timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._exercise_timeout is not None:
            duration = random.uniform(self._exercise_timeout.min_time, self._exercise_timeout.max_time)
            self._create_or_load_alarm(EXERCISE_TIMEOUT, duration, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(EXERCISE_TIMEOUT)

    def timer_expired(self):
        self.owner._change_state(self.owner.take_shower_state())

class _TakeShowerState(CommonInteractionCompletedSituationState):
    FACTORY_TUNABLES = {'do_stuff_afterwards': Tunable(description='\n            If True then the Sim will do stuff in the gym after exercise.\n            ', tunable_type=bool, default=True)}

    def __init__(self, do_stuff_afterwards, **kwargs):
        super().__init__(**kwargs)
        self._do_stuff_afterwards = do_stuff_afterwards

    def _on_interaction_of_interest_complete(self, **kwargs):
        if self._do_stuff_afterwards:
            self.owner._change_state(self.owner.do_stuff_state())
        else:
            self.owner._self_destruct()

class _DoStuffState(CommonSituationState):
    FACTORY_TUNABLES = {'job_and_role_gym_stuff': TunableMapping(description='\n                A mapping between situation jobs and role states that defines\n                what role states we want to switch to for sims on which jobs\n                when this situation state is entered.\n                ', key_type=TunableReference(description="\n                    A reference to a SituationJob that we will use to change\n                    sim's role state.\n                    ", manager=services.situation_job_manager(), pack_safe=True), key_name='Situation Job', value_type=TunableReference(description='\n                    The role state that we will switch sims of the linked job\n                    into.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.ROLE_STATE), pack_safe=True), value_name='Role State'), 'do_stuff_timeout': OptionalTunable(description='\n                Optional tunable for when to end the Do Stuff state. \n    \n                If this is enabled then the Do Stuff state will eventually time\n                out and end the situation.\n                \n                If this is disabled the situation will just stay in the Do Stuff\n                state forever.\n                ', tunable=TunableTuple(description='\n                \n                    ', min_time=TunableSimMinute(description='\n                        The length of time to wait before advancing to the\n                        Change Clothes state.\n                        ', default=60), max_time=TunableSimMinute(description='\n                        The maximum time a visitor will spend on the relaxation\n                        venue as a guest.\n                        ', default=60))), 'locked_args': {'job_and_role_changes': frozendict()}}

    def __init__(self, job_and_role_gym_stuff, do_stuff_timeout, **kwargs):
        super().__init__(**kwargs)
        self._job_and_role_gym_stuff = job_and_role_gym_stuff
        self._do_stuff_timeout = do_stuff_timeout

    def on_activate(self, reader=None):
        super().on_activate(reader)
        if self._do_stuff_timeout is not None:
            duration = random.uniform(self._do_stuff_timeout.min_time, self._do_stuff_timeout.max_time)
            self._create_or_load_alarm(DO_STUFF_TIMEOUT, duration, lambda _: self.timer_expired(), should_persist=True, reader=reader)

    def _set_job_role_state(self):
        for (job, role_state) in self._job_and_role_gym_stuff.items():
            if job is not None and role_state is not None:
                self.owner._set_job_role_state(job, role_state)

    def _get_remaining_time_for_gsi(self):
        return self._get_remaining_alarm_time(DO_STUFF_TIMEOUT)

    def timer_expired(self):
        self.owner._self_destruct()

class GymVisitorSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'situation_default_job': SituationJob.TunableReference(description='\n            The default job that a visitor will be in during the situation.\n            '), 'exercise_state': _ExerciseState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            everything except for arrive and leave.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='01_exercise_state'), 'take_shower_state': _TakeShowerState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            everything except for arrive and leave.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='02_take_shower_state'), 'do_stuff_state': _DoStuffState.TunableFactory(description='\n            The main state of the situation. This is where Sims will do \n            everything except for arrive and leave.\n            ', tuning_group=SituationComplexCommon.SITUATION_STATE_GROUP, display_name='03_do_stuff_state')}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def default_job(cls):
        return cls.situation_default_job

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _ExerciseState, factory=cls.exercise_state), SituationStateData(2, _TakeShowerState, factory=cls.take_shower_state), SituationStateData(3, _DoStuffState, factory=cls.do_stuff_state)]

    def start_situation(self):
        super().start_situation()
        self._change_state(self.exercise_state())

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.exercise_state._tuned_values.job_and_role_changes.items())

class GymTrainerSituation(StaffMemberSituation):
    pass
