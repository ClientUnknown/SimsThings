from interactions.utils.loot_basic_op import BaseLootOperationfrom sickness import loggerfrom sims4.callback_utils import CallableTestListfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableReference, Tunable, HasTunableSingletonFactory, AutoFactoryInit, TunableVariant, OptionalTunable, TunableIntervalfrom tag import TunableTagsimport services
class _GiveSpecificSickness(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'sickness': TunableReference(description='\n            Sickness to give to the subject.\n            ', manager=services.get_instance_manager(Types.SICKNESS), class_restrictions=('Sickness',), pack_safe=True)}

    def give_sickness(self, subject):
        services.get_sickness_service().make_sick(subject, sickness=self.sickness)

class _SicknessMatchingCritera(HasTunableSingletonFactory, AutoFactoryInit):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        if value.tags is None and value.difficulty_range is None:
            logger.error('_SicknessMatchingCritera: {} has a sickness criteria {} that sets no criteria.', source, tunable_name)

    FACTORY_TUNABLES = {'tags': OptionalTunable(description='\n            Optionally, only sicknesses that share any of the tags specified are considered. \n            ', tunable=TunableTags(filter_prefixes=('Sickness',))), 'difficulty_range': OptionalTunable(description="\n            Optionally define the difficulty rating range that is required\n            for the Sim's sickness.\n            ", tunable=TunableInterval(description="\n                The difficulty rating range, this maps to 'difficulty_rating'\n                values in Sickness tuning.\n                ", tunable_type=float, default_lower=0, default_upper=10, minimum=0, maximum=10)), 'verify_tunable_callback': _verify_tunable_callback}

    def give_sickness(self, subject):
        sickness_criteria = CallableTestList()
        if self.tags is not None:
            sickness_criteria.append(lambda s: self.tags & s.sickness_tags)
        if self.difficulty_range is not None:
            sickness_criteria.append(lambda s: s.difficulty_rating in self.difficulty_range)
        services.get_sickness_service().make_sick(subject, criteria_func=sickness_criteria, only_auto_distributable=False)

class GiveSicknessLootOp(BaseLootOperation):
    FACTORY_TUNABLES = {'sickness': TunableVariant(description='\n            Sickness to give to the subject.\n            ', locked_args={'random': None}, specific_sickness=_GiveSpecificSickness.TunableFactory(), sickness_criteria=_SicknessMatchingCritera.TunableFactory(), default='random'), 'reset_diagnosis_progress': Tunable(description='\n            If checked then reset the diagnosis progress, make all\n            exams available, and clear the list of treatments performed.\n            ', tunable_type=bool, default=True)}

    def __init__(self, sickness, reset_diagnosis_progress, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.sickness = sickness
        self.reset_diagnosis_progress = reset_diagnosis_progress

    def _apply_to_subject_and_target(self, subject, target, resolver):
        if self.sickness is None:
            services.get_sickness_service().make_sick(subject)
        else:
            self.sickness.give_sickness(subject)
        if self.reset_diagnosis_progress:
            services.get_sickness_service().clear_diagnosis_data(subject)

class RemoveSicknessLootOp(BaseLootOperation):

    def _apply_to_subject_and_target(self, subject, target, resolver):
        services.get_sickness_service().remove_sickness(subject)
