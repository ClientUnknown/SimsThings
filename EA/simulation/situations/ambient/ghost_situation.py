from role.role_state import RoleStatefrom sims4.utils import classpropertyfrom situations.situation_complex import SituationState, SituationStateDatafrom situations.situation_job import SituationJobimport alarmsimport clockimport sims4.tuning.tunableimport situations.bouncerimport situations.situation_complexDO_STUFF_TIMEOUT = 'do_stuff_timeout'
class GhostSituation(situations.situation_complex.SituationComplexCommon):
    INSTANCE_TUNABLES = {'role': sims4.tuning.tunable.TunableTuple(situation_job=SituationJob.TunableReference(description='\n                The situation job for the sim.\n                '), do_stuff_role_state=RoleState.TunableReference(description='\n                The role state for the sim doing stuff.  This is the initial state.\n                '), leave_role_state=RoleState.TunableReference(description='\n                The role state for the sim leaving.\n                ')), 'do_stuff_timeout': sims4.tuning.tunable.TunableSimMinute(description='\n            The amount of time the sim does stuff before leaving.\n            ', default=360)}
    REMOVE_INSTANCE_TUNABLES = situations.situation.Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _BeGhostState), SituationStateData(2, _LeaveState))

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.role.situation_job, cls.role.do_stuff_role_state)]

    @classmethod
    def default_job(cls):
        return cls.role.situation_job

    def start_situation(self):
        super().start_situation()
        self._change_state(_BeGhostState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @classmethod
    def _can_start_walkby(cls, lot_id:int):
        return True

    @property
    def _should_cancel_leave_interaction_on_premature_removal(self):
        return True

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.LOT
sims4.tuning.instances.lock_instance_tunables(GhostSituation, exclusivity=situations.bouncer.bouncer_types.BouncerExclusivityCategory.NORMAL, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE, duration=0)
class _BeGhostState(SituationState):

    def __init__(self):
        super().__init__()
        self._timeout_handle = None

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.role.situation_job, self.owner.role.do_stuff_role_state)
        timeout = self.owner.do_stuff_timeout
        if reader is not None:
            timeout = reader.read_float(DO_STUFF_TIMEOUT, timeout)
        self._timeout_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(timeout), lambda _: self._timer_expired())

    def save_state(self, writer):
        super().save_state(writer)
        if self._timeout_handle is not None:
            writer.write_float(DO_STUFF_TIMEOUT, self._timeout_handle.get_remaining_time().in_minutes())

    def on_deactivate(self):
        if self._timeout_handle is not None:
            alarms.cancel_alarm(self._timeout_handle)
            self._timeout_handle = None
        super().on_deactivate()

    def _timer_expired(self):
        self._change_state(_LeaveState())

class _LeaveState(SituationState):

    def on_activate(self, reader=None):
        super().on_activate(reader)
        self.owner._set_job_role_state(self.owner.role.situation_job, self.owner.role.leave_role_state)
