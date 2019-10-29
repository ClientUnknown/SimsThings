from situations.situation import Situationimport situations.situation_compleximport situations.situation_types
class VisitingNPCSituation(situations.situation_complex.SituationComplexCommon):
    INSTANCE_SUBCLASSES_ONLY = True
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    @classmethod
    def _get_greeted_status(cls):
        return situations.situation_types.GreetedStatus.GREETED
