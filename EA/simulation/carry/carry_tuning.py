from sims4.tuning.tunable import TunableReferenceimport servicesimport sims4.resources
class CarryPostureStaticTuning:
    POSTURE_CARRY_NOTHING = TunableReference(description='\n            Reference to the posture that represents carrying nothing\n            ', manager=services.get_instance_manager(sims4.resources.Types.POSTURE), class_restrictions='CarryingNothing')
    POSTURE_CARRY_OBJECT = TunableReference(description='\n        Reference to the posture that represents carrying an Object\n        ', manager=services.get_instance_manager(sims4.resources.Types.POSTURE), class_restrictions='CarryingObject')
