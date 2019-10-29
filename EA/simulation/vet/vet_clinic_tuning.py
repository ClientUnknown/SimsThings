from interactions import ParticipantTypefrom sims4.resources import Typesfrom sims4.tuning.tunable import TunablePackSafeResourceKey, TunablePackSafeReference, TunableRange, TunableTuple, TunableList, TunableThreshold, TunableReferencefrom sims4.tuning.tunable_base import ExportModesfrom statistics.skill import Skillfrom statistics.skill_tests import SkillRangeTest, SkillThresholdimport enumimport servicesimport sims4logger = sims4.log.Logger('VetClinicTuning', default_owner='jdimailig')
class VetEmployeeOutfitType(enum.Int, export=False):
    MALE_EMPLOYEE = 0
    FEMALE_EMPLOYEE = 1

def verify_value_of_service(instance_class, tunable_name, source, value, **kwargs):
    if value:
        previous_threshold_value = None
        for item in reversed(value):
            if previous_threshold_value is not None and item.markup_threshold.value > previous_threshold_value:
                logger.error('Thresholds should be ordered from less to greater thresholds {}', value)
            previous_threshold_value = item.markup_threshold.value

def verify_difficulty_bonuses(instance_class, tunable_name, source, value, **kwargs):
    if value:
        previous_threshold_value = None
        for item in reversed(value):
            if previous_threshold_value is not None and item.threshold.value > previous_threshold_value:
                logger.error('Thresholds should be ordered from less to greater thresholds {}', value)
            previous_threshold_value = item.threshold.value

def set_vet_skill_on_threshold_test(instance_class, tunable_name, source, value):
    value.skill = VetClinicTuning.VET_SKILL

class VetClinicTuning:
    UNIFORM_EMPLOYEE_MALE = TunablePackSafeResourceKey(description='\n        The SimInfo file to use to edit male employee uniforms.\n        ', default=None, resource_types=(sims4.resources.Types.SIMINFO,), export_modes=ExportModes.All)
    UNIFORM_EMPLOYEE_FEMALE = TunablePackSafeResourceKey(description='\n        The SimInfo file to use to edit female employee uniforms.\n        ', default=None, resource_types=(sims4.resources.Types.SIMINFO,), export_modes=ExportModes.All)
    VET_CLINIC_VENUE = TunablePackSafeReference(description='\n        This is a tunable reference to the type of this Venue.\n        ', manager=services.get_instance_manager(sims4.resources.Types.VENUE))
    DEFAULT_PROFIT_PER_TREATMENT_FOR_OFF_LOT_SIMULATION = TunableRange(description='\n        This is used as the default profit for a treatment for off-lot simulation.\n        Once enough actual treatments have been performed, this value becomes \n        irrelevant and the MAX_COUNT_FOR_OFF_LOT_PROFIT_PER_TREATMENT tunable comes into use. \n        ', tunable_type=int, default=20, minimum=1)
    MAX_COUNT_FOR_OFF_LOT_PROFIT_PER_TREATMENT = TunableRange(description='\n        The number of treatments to keep a running average of for the profit\n        per treatment calculations during off lot simulations.\n        ', tunable_type=int, default=10, minimum=2)
    VET_SKILL = Skill.TunablePackSafeReference(description='\n        The vet skill for reference in code.  This can resolve to None\n        if the pack providing the skill is not installed, so beware.\n        ')
    VALUE_OF_SERVICE_AWARDS = TunableList(description='\n        A threshold matrix that maps buffs to level of markup and vet skill.\n\n        Order is important.  The list is processed in reverse order.\n        The first threshold that passes returns the amount associated with it.\n        Because of this, optimal order is thresholds is ordered from lesser \n        to greater threshold values.\n        ', tunable=TunableTuple(description='\n            A pair of markup threshold and skill threshold-to-buff list.\n            ', markup_threshold=TunableThreshold(description='The threshold at which this item will match.'), skill_to_buffs=TunableList(description='\n                Mapping of skill threshold to the value of service that is applied.\n                \n                Order is important.  The list is processed in reverse order.\n                The first threshold that passes returns the amount associated with it.\n                Because of this, optimal order is thresholds is ordered from lesser \n                to greater threshold values.\n                ', tunable=TunableTuple(description="\n                    A pair of skill threshold to the buff that will apply\n                    if this threshold is met when the patient is billed\n                    for a vet's services.\n                    ", skill_range=SkillRangeTest.TunableFactory(skill_range=SkillThreshold.TunableFactory(), callback=set_vet_skill_on_threshold_test, locked_args={'subject': ParticipantType.Actor, 'skill': None, 'tooltip': None}), value_of_service_buff=TunableReference(manager=services.get_instance_manager(Types.BUFF), pack_safe=True)))), verify_tunable_callback=verify_value_of_service)
    DIFFICULTY_BONUS_PAYMENT = TunableList(description='\n        When an NPC or player Sim treats an NPC Sim, they can get a difficulty\n        bonus depending on the difficulty of the sickness (if it is the correct\n        and ideal treatment for the sickness).\n        \n        Order is important.  The list is processed in reverse order.\n        The first threshold that passes returns the amount associated with it.\n        Because of this, optimal order is thresholds is ordered from lesser \n        to greater threshold values.\n        \n        If no thresholds pass, returned bonus amount is 0.\n        ', tunable=TunableTuple(description='\n            A pair of payment amount and threshold that the payment applies to.\n            ', bonus_amount=TunableRange(tunable_type=int, default=100, minimum=0), threshold=TunableThreshold()), verify_tunable_callback=verify_difficulty_bonuses)
