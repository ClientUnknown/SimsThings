from sims4.utils import classpropertyfrom situations.situation_complex import SituationState, SituationStateDataimport sims4.tuning.instancesimport situations.situation_complex
class EmptyLotSituation(situations.situation_complex.SituationComplexCommon):
    REMOVE_INSTANCE_TUNABLES = situations.situation.Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _EmptyLotSituationState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return []

    @classmethod
    def default_job(cls):
        pass

    def start_situation(self):
        super().start_situation()
        self._change_state(_EmptyLotSituationState())

    @classmethod
    def get_sims_expected_to_be_in_situation(cls):
        return 1

    @classmethod
    def _can_start_walkby(cls, _):
        return True

    @classproperty
    def situation_serialization_option(cls):
        return situations.situation_types.SituationSerializationOption.LOT
sims4.tuning.instances.lock_instance_tunables(EmptyLotSituation, creation_ui_option=situations.situation_types.SituationCreationUIOption.NOT_AVAILABLE)
class _EmptyLotSituationState(SituationState):
    pass
