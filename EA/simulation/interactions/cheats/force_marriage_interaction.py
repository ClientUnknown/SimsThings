from interactions.aop import AffordanceObjectPairfrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom sims4.localization import TunableLocalizedStringFactoryfrom sims4.utils import flexmethodfrom singletons import DEFAULTimport servicesimport sims4
class ForceMarriageInteraction(ImmediateSuperInteraction):
    INSTANCE_TUNABLES = {'clear_all_marriage_interaction_name': TunableLocalizedStringFactory(description='\n            Display name for the interaction to remove all marriage links for this sim.\n            ')}

    def __init__(self, *args, spouse_sim_info, **kwargs):
        super().__init__(*args, **kwargs)
        self.spouse_sim_info = spouse_sim_info

    @classmethod
    def _get_all_spouse_for_sim(cls, actor_sim_id):
        spouses = set()
        actor_sim_info = services.sim_info_manager().get(actor_sim_id)
        actor_spouse_sim_id = actor_sim_info.relationship_tracker.spouse_sim_id
        if actor_spouse_sim_id is not None:
            spouses.add(services.sim_info_manager().get(actor_spouse_sim_id))
        for sim_info in services.sim_info_manager().values():
            spouse_id = sim_info.relationship_tracker.spouse_sim_id
            if spouse_id == actor_sim_id:
                spouses.add(sim_info)
            if not actor_sim_info.relationship_tracker.has_bit(sim_info.id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT):
                if sim_info.relationship_tracker.has_bit(actor_sim_info.id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT):
                    spouses.add(sim_info)
            spouses.add(sim_info)
        return spouses

    @classmethod
    def enforce_marriage(cls, source, target, _connection=None):

        def clear_spouse_bit(a, b):
            if a.relationship_tracker.has_bit(b.id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT):
                a.relationship_tracker.remove_relationship_bit(b.id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT)

        def clear_invalid_spouse_links(sim):
            spouses = cls._get_all_spouse_for_sim(sim.id)
            for spouse_sim_info in spouses:
                if spouse_sim_info is None:
                    pass
                else:
                    clear_spouse_bit(sim, spouse_sim_info)
                    clear_spouse_bit(spouse_sim_info, sim)

        def add_spouse_bit(a, b):
            if not a.relationship_tracker.has_bit(b.id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT):
                a.relationship_tracker.add_relationship_bit(b.id, RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT)

        clear_invalid_spouse_links(source)
        if target is not None:
            clear_invalid_spouse_links(target)
            add_spouse_bit(source, target)
            add_spouse_bit(target, source)

    def _run_interaction_gen(self, timeline):
        self.enforce_marriage(self.target, self.spouse_sim_info)

    @flexmethod
    def _get_name(cls, inst, spouse_sim_info=None, **interaction_parameters):
        inst_or_cls = inst if inst is not None else cls
        if spouse_sim_info is None:
            return inst_or_cls.create_localized_string(inst_or_cls.clear_all_marriage_interaction_name, spouse_sim_info=spouse_sim_info, **interaction_parameters)
        else:
            return super(__class__, inst_or_cls)._get_name(spouse_sim_info=spouse_sim_info, **interaction_parameters)

    @flexmethod
    def create_localized_string(cls, inst, localized_string_factory, *tokens, spouse_sim_info, **kwargs):
        inst_or_cls = inst if inst is not None else cls
        interaction_tokens = inst_or_cls.get_localization_tokens(**kwargs)
        return localized_string_factory(*interaction_tokens + (spouse_sim_info,))

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        spouses = cls._get_all_spouse_for_sim(target.sim_id)
        spouses.add(None)
        for sim_info in spouses:
            yield AffordanceObjectPair(cls, target, cls, None, spouse_sim_info=sim_info, pie_menu_cateogory=cls.category, **kwargs)
