from situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, CommonSituationState, SituationStateData
class _SimpleState(CommonSituationState):
    pass

class RestaurantEventSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'simple_state': _SimpleState.TunableFactory(description='\n            The basic state that all Sims in this situation will be in during\n            this situation.\n            ')}
    REMOVE_INSTANCE_TUNABLES = Situation.SITUATION_EVENT_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return [SituationStateData(1, _SimpleState, factory=cls.simple_state)]

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return list(cls.simple_state._tuned_values.job_and_role_changes.items())

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(self.simple_state())
