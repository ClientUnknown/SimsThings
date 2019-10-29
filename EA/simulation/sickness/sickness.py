import itertoolsimport operatorimport randomfrom event_testing.resolver import SingleSimResolver, DoubleSimResolverfrom event_testing.test_events import TestEventfrom event_testing.tests import TunableTestSetfrom sickness.sickness_enums import DiagnosticActionResultType, SicknessDiagnosticActionTypefrom sickness.sickness_tuning import SicknessTuningfrom sickness.symptom import Symptomfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.resources import Typesfrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReference, HasTunableSingletonFactory, AutoFactoryInit, TunableMapping, TunableReference, TunableVariant, TunableRange, TunableList, TunableSet, TunableEnumEntry, OptionalTunable, Tunablefrom sims4.tuning.tunable_base import GroupNamesfrom tag import TunableTagsfrom tunable_multiplier import TestedSumimport servicesimport sims4import snippets
class _DiagnosticActionLoots(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'default_loots': TunableSet(description='\n            Default loots to apply.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), pack_safe=True)), 'interaction_overrides': TunableMapping(description='\n            Overrides by specific interaction.  This can be used to\n            adjust loots depending on a treatment or examination as it\n            applies to a sickness.\n            ', key_type=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.INTERACTION), pack_safe=True), value_type=TunableSet(tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), pack_safe=True)))}

    def apply_loots(self, resolver):
        affordance = resolver.interaction.affordance
        loots_to_apply = self.default_loots
        if affordance in self.interaction_overrides:
            loots_to_apply = self.interaction_overrides[affordance]
        for loot in loots_to_apply:
            loot.apply_to_resolver(resolver)

class _DiscoverSymptomThresholdAction(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'symptom': TunableReference(description='\n            Symptom discovered by this threshold action.\n            ', manager=services.get_instance_manager(Types.SICKNESS), class_restrictions=(Symptom,), pack_safe=True)}

    def perform(self, patient_sim, **__):
        if not patient_sim.has_sickness_tracking():
            return
        if patient_sim.was_symptom_discovered(self.symptom):
            return
        patient_sim.discover_symptom(self.symptom)
        services.get_sickness_service().add_sickness_event(patient_sim.sim_info, patient_sim.current_sickness, 'Discovered {}'.format(self.symptom.__name__))
        services.get_event_manager().process_event(TestEvent.DiagnosisUpdated, sim_info=patient_sim, custom_keys=(patient_sim.sim_id,), discovered_symptom=self.symptom)

class _DiscoverSicknessThresholdAction(HasTunableSingletonFactory, AutoFactoryInit):

    def perform(self, patient_sim, **__):
        if not patient_sim.has_sickness_tracking():
            return
        if patient_sim.sickness_tracker.has_discovered_sickness:
            return
        sickness = patient_sim.current_sickness
        for treatment in itertools.chain(sickness.available_treatments, sickness.available_treatment_lists):
            if treatment not in sickness.correct_treatments:
                patient_sim.rule_out_treatment(treatment)
        patient_sim.sickness_tracker.discover_sickness()
        services.get_sickness_service().add_sickness_event(patient_sim.sim_info, patient_sim.current_sickness, 'Discovered Sickness')
        services.get_event_manager().process_event(TestEvent.DiagnosisUpdated, sim_info=patient_sim, custom_keys=(patient_sim.sim_id,), discovered_sickness=patient_sim.current_sickness)

class _RuleOutTreatmentThresholdAction(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'rule_out_reason': OptionalTunable(description='\n            The reason based on which treatments are ruled out.\n            \n            By default, it will rule out treatments that contain any of the\n            interaction category tags of the exam that was performed. This can\n            be overridden to rule out treatments with specific tags.\n            ', tunable=TunableTags(description='\n                Only rule out treatments with one of the specified tags.\n                '), disabled_name='interaction_tags', enabled_name='specified_tags')}

    def perform(self, patient_sim, interaction=None):
        sickness = patient_sim.current_sickness
        if sickness is None:
            return
        applicable = set(itertools.chain(sickness.available_treatments, sickness.available_treatment_lists))
        ruled_out = set(itertools.chain(patient_sim.sickness_tracker.treatments_performed, patient_sim.sickness_tracker.ruled_out_treatments))
        correct = set(sickness.correct_treatments)
        available_for_ruling_out = tuple(applicable - ruled_out - correct)
        if self.rule_out_reason is None and interaction is not None:
            interaction_tags = SicknessTuning.EXAM_TYPES_TAGS & interaction.interaction_category_tags
            available_for_ruling_out = tuple(treatment for treatment in available_for_ruling_out if interaction_tags & treatment.interaction_category_tags)
        elif self.rule_out_reason is not None:
            available_for_ruling_out = tuple(treatment for treatment in available_for_ruling_out if self.rule_out_reason & treatment.interaction_category_tags)
        if not available_for_ruling_out:
            return
        to_rule_out = random.choice(available_for_ruling_out)
        patient_sim.rule_out_treatment(to_rule_out)
        services.get_sickness_service().add_sickness_event(patient_sim.sim_info, patient_sim.current_sickness, 'Ruled out {}'.format(to_rule_out.__name__))

class _ApplyLootThresholdAction(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'loots_to_apply': TunableSet(description='\n            The loots to apply.\n            ', tunable=TunableReference(manager=services.get_instance_manager(sims4.resources.Types.ACTION), pack_safe=True))}

    def perform(self, patient_sim, interaction=None):
        resolver = DoubleSimResolver(services.active_sim_info(), patient_sim) if interaction is None else interaction.get_resolver()
        for loot in self.loots_to_apply:
            loot.apply_to_resolver(resolver)

class _DiagnosticThresholdActions(TunableVariant):

    def __init__(self, *args, **kwargs):
        super().__init__(discover_symptom=_DiscoverSymptomThresholdAction.TunableFactory(), discover_sickness=_DiscoverSicknessThresholdAction.TunableFactory(), rule_out_treatment=_RuleOutTreatmentThresholdAction.TunableFactory(), apply_loots=_ApplyLootThresholdAction.TunableFactory(), default='discover_symptom')

class Sickness(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SICKNESS)):
    INSTANCE_TUNABLES = {'diagnosis_stat': TunableReference(description='\n            Statistic we are using to track diagnostic progress for this sickness.\n            This is used for the threshold actions checks.\n            ', manager=services.get_instance_manager(Types.STATISTIC)), 'threshold_actions': TunableMapping(description='\n            After passing specific values of the diagnosis stat, perform\n            the appropriate actions.\n            ', key_type=int, value_type=TunableList(description='\n                List of actions to process when this threshold is reached \n                or passed.', tunable=_DiagnosticThresholdActions())), 'display_name': TunableLocalizedStringFactory(description="\n            The sickness's display name. This string is provided with the owning\n            Sim as its only token.\n            ", tuning_group=GroupNames.UI), 'difficulty_rating': TunableRange(description='\n            The difficulty rating for treating this sickness.\n            ', tunable_type=float, tuning_group=GroupNames.UI, default=5, minimum=0, maximum=10), 'symptoms': TunableSet(description='\n            Symptoms associated with this sickness.  When the sickness\n            is applied to a Sim, all symptoms are applied.', tunable=TunableReference(manager=services.get_instance_manager(Types.SICKNESS), class_restrictions=(Symptom,), pack_safe=True)), 'associated_buffs': TunableSet(description='\n            The associated buffs that will be added to the Sim when the sickness\n            is applied, and removed when the sickness is removed.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.BUFF), pack_safe=True)), 'associated_statistics': TunableSet(description="\n            The associated stats that will be added to the Sim when the sickness\n            is applied, and removed when the sickness is removed.\n            \n            These are added at the statistic's default value.\n            ", tunable=TunableReference(manager=services.get_instance_manager(Types.STATISTIC), pack_safe=True)), 'restrictions': TunableTestSet(description='\n            Test set specifying whether or not this sickness can be applied.\n            One set of tests must pass in order for the sickness to be valid.\n            (This is an OR of ANDS.)\n            '), 'weight': TestedSum.TunableFactory(description='\n            Weighted value of this sickness versus other valid sicknesses that\n            are possible for the Sim to apply a sickness to.\n            \n            Tests, if defined here, may adjust the weight in addition \n            to the tuned base value.\n            '), 'difficulty_rating': TunableRange(description='\n            The difficulty rating for treating this sickness.\n            ', tunable_type=float, tuning_group=GroupNames.UI, default=5, minimum=0, maximum=10), 'examination_loots': TunableMapping(description='\n            Mapping of examination result types to loots to apply\n            as a result of the interaction.\n            ', key_type=TunableEnumEntry(tunable_type=DiagnosticActionResultType, default=DiagnosticActionResultType.DEFAULT), value_type=_DiagnosticActionLoots.TunableFactory()), 'treatment_loots': TunableMapping(description='\n            Mapping of treatment result types to loots to apply\n            as a result of the interaction.\n            ', key_type=TunableEnumEntry(tunable_type=DiagnosticActionResultType, default=DiagnosticActionResultType.DEFAULT), value_type=_DiagnosticActionLoots.TunableFactory()), 'available_treatments': TunableSet(description='\n            Treatments that are available for this sickness.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.INTERACTION), pack_safe=True)), 'available_treatment_lists': TunableSet(description='\n            Treatments that are available for this sickness.\n            ', tunable=snippets.TunableAffordanceListReference()), 'correct_treatments': TunableSet(description='\n            Treatments that can cure this sickness.  These sicknesses\n            will never be ruled out as exams are performed.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.INTERACTION), pack_safe=True)), 'sickness_tags': TunableTags(description='\n            Tags that help categorize this sickness.\n            ', filter_prefixes=('Sickness',)), 'track_in_history': Tunable(description='\n            If checked, this is tracked in sickness history.\n            ', tunable_type=bool, default=True), 'considered_sick': Tunable(description='\n            Considered as sickness.  Most sickness should have this tuned.\n            Examinations, which are pseudo-sicknesses will have this tuned false.\n            \n            If this is checked, the sickness will pass is_sick tests.\n            ', tunable_type=bool, default=True), 'distribute_manually': Tunable(description='\n            If checked, this is not distributed by the sickness service,\n            and must be done by a game system or loot.\n            ', tunable_type=bool, default=False)}

    @classmethod
    def _can_be_applied(cls, resolver=None, sim_info=None):
        if resolver or not sim_info:
            raise ValueError('Must specify a Sim info or a resolver')
        if not resolver:
            resolver = SingleSimResolver(sim_info)
        return cls.restrictions.run_tests(resolver)

    @classmethod
    def get_sickness_weight(cls, resolver=None, sim_info=None):
        if resolver or not sim_info:
            raise ValueError('Must specify a Sim info or a resolver')
        if not cls._can_be_applied(resolver=resolver):
            return 0
        return max(cls.weight.get_modified_value(resolver), 0)

    @classmethod
    def apply_to_sim_info(cls, sim_info, from_load=False):
        if not cls._can_be_applied(resolver=SingleSimResolver(sim_info)):
            return
        for symptom in cls.symptoms:
            symptom.apply_to_sim_info(sim_info)
        for buff in cls.associated_buffs:
            if buff.can_add(sim_info) and not sim_info.has_buff(buff):
                sim_info.add_buff(buff, buff_reason=cls.display_name)
        for stat in cls.associated_statistics:
            if not sim_info.get_tracker(stat).has_statistic(stat):
                sim_info.add_statistic(stat, stat.default_value)
        if not from_load:
            sim_info.sickness_tracker.add_sickness(cls)

    @classmethod
    def remove_from_sim_info(cls, sim_info):
        if sim_info is None:
            return
        for symptom in cls.symptoms:
            symptom.remove_from_sim_info(sim_info)
        for buff in cls.associated_buffs:
            sim_info.remove_buff_by_type(buff)
        for stat in cls.associated_statistics:
            sim_info.remove_statistic(stat)
        sim_info.remove_statistic(cls.diagnosis_stat)
        if sim_info.has_sickness(cls):
            sim_info.sickness_tracker.remove_sickness()

    @classmethod
    def is_available_treatment(cls, affordance):
        return affordance in itertools.chain(cls.available_treatments, cls.available_treatment_lists)

    @classmethod
    def is_correct_treatment(cls, affordance):
        return affordance in cls.correct_treatments

    @classmethod
    def apply_loots_for_action(cls, action_type, result_type, interaction):
        loots_to_apply = None
        if action_type == SicknessDiagnosticActionType.EXAM:
            if result_type in cls.examination_loots:
                loots_to_apply = cls.examination_loots[result_type]
        elif result_type in cls.treatment_loots:
            loots_to_apply = cls.treatment_loots[result_type]
        if loots_to_apply is not None:
            loots_to_apply.apply_loots(interaction.get_resolver())
        cls._handle_threshold_actions(interaction.get_resolver())

    @classmethod
    def _handle_threshold_actions(cls, resolver):
        cls.update_diagnosis(resolver.target.sim_info, interaction=resolver.interaction)

    @classmethod
    def update_diagnosis(cls, sim_info, interaction=None):
        diagnostic_progress = sim_info.get_statistic(cls.diagnosis_stat).get_value()
        last_progress = sim_info.sickness_tracker.last_progress
        if diagnostic_progress == last_progress:
            return
        for (threshold, actions) in cls._get_sorted_threshold_actions():
            if threshold <= last_progress:
                pass
            else:
                if diagnostic_progress < threshold:
                    break
                for action in actions:
                    action.perform(sim_info, interaction=interaction)
        sim_info.sickness_record_last_progress(diagnostic_progress)

    @classmethod
    def _get_sorted_threshold_actions(cls):
        return sorted(cls.threshold_actions.items(), key=operator.itemgetter(0))

    @classmethod
    def on_zone_load(cls, sim_info):
        cls.on_sim_info_loaded(sim_info)

    @classmethod
    def on_sim_info_loaded(cls, sim_info):
        if not sim_info.has_sickness_tracking():
            return
        sim_info.sickness_record_last_progress(sim_info.get_statistic(cls.diagnosis_stat).get_value())
        cls.apply_to_sim_info(sim_info, from_load=True)

    @classmethod
    def get_ordered_symptoms(cls):
        ordered_symptoms = []
        for (_, action_list) in cls._get_sorted_threshold_actions():
            for action in action_list:
                if isinstance(action, _DiscoverSymptomThresholdAction):
                    ordered_symptoms.append(action.symptom)
        return ordered_symptoms
