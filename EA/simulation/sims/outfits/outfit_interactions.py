import functoolsfrom animation.animation_utils import flush_all_animationsfrom element_utils import build_critical_sectionfrom elements import ParentElementfrom event_testing.resolver import SingleSimResolverfrom event_testing.tests import TunableTestSetfrom interactions import ParticipantTypefrom interactions.aop import AffordanceObjectPairfrom interactions.base.super_interaction import SuperInteractionfrom sims.outfits.outfit_enums import OutfitCategory, OutfitChangeReasonfrom sims.outfits.outfit_tuning import OutfitTuningfrom sims.outfits.outfit_utils import OutfitGeneratorRandomizationMixinfrom sims4.tuning.tunable import TunableVariant, HasTunableSingletonFactory, AutoFactoryInit, TunableTuple, TunableList, TunableEnumEntry, Tunable, OptionalTunablefrom sims4.utils import flexmethodfrom singletons import DEFAULTfrom tag import TunableTag, TunableTagsimport servicesimport sims4.loglogger = sims4.log.Logger('Outfits', default_owner='camilogarcia')
class OutfitChangeSituation(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'situation_tags': TunableTags(description='\n            Tags for situations that will be considered for the outfit\n            interactions.\n            ', filter_prefixes=['situation'])}

    def outfit_affordances_gen(self, sim, target, affordance, **kwargs):
        resolver = SingleSimResolver(sim.sim_info)
        for situation in services.get_zone_situation_manager().get_situations_by_tags(self.situation_tags):
            situation_job = situation.get_current_job_for_sim(sim)
            if situation_job is not None and situation_job.job_uniform is not None:
                outfit_generators = situation_job.job_uniform.situation_outfit_generators
                if outfit_generators is None:
                    pass
                else:
                    for entry in outfit_generators:
                        if entry.tests.run_tests(resolver):
                            yield AffordanceObjectPair(affordance, target, affordance, None, pie_menu_cateogory=affordance.category, outfit_tags=entry.generator.tags, **kwargs)

    def get_outfit_tags(self):
        outfit_tags = set()
        situation_manager = services.get_instance_manager(sims4.resources.Types.SITUATION)
        for situation in situation_manager.types.values():
            if self.situation_tags and any(tag in situation.tags for tag in self.situation_tags):
                for situation_job in situation.get_tuned_jobs():
                    if situation_job.job_uniform is None:
                        pass
                    else:
                        outfit_generators = situation_job.job_uniform.situation_outfit_generators
                        if outfit_generators is None:
                            pass
                        else:
                            for entry in outfit_generators:
                                for tag in entry.generator.tags:
                                    outfit_tags.add(tag)
        return outfit_tags

    def get_outfit_for_clothing_change(self, sim_info, outfit_change_category):
        return sim_info.get_outfit_for_clothing_change(None, OutfitChangeReason.DefaultOutfit, resolver=SingleSimResolver(sim_info))

class OutfitChangeTags(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'outfit_change_data': TunableList(description='\n            List of data corresponding at possible outfits and tests that will\n            generate change outfit affordances.\n            ', tunable=TunableTuple(description='\n                Outfits and tests that will generate the change outfit\n                interactions.\n                ', outfit_tag=TunableTag(description='\n                    Outfit tag that will generate the outfit change \n                    interactions.\n                    ', filter_prefixes=('Uniform', 'OutfitCategory', 'Style', 'Situation')), outfit_tests=TunableTestSet(description='\n                    Tests the Sim should pass to be able to change into the\n                    outfit.\n                    ')))}

    def outfit_affordances_gen(self, sim, target, affordance, **kwargs):
        resolver = SingleSimResolver(sim.sim_info)
        for outfit_data in self.outfit_change_data:
            if outfit_data.outfit_tests.run_tests(resolver):
                yield AffordanceObjectPair(affordance, target, affordance, None, pie_menu_cateogory=affordance.category, outfit_tags=(outfit_data.outfit_tag,), **kwargs)

    def get_outfit_tags(self):
        outfit_tags = set()
        for outfit_data in self.outfit_change_data:
            outfit_tags.add(outfit_data.outfit_tag)
        return outfit_tags

    def get_outfit_for_clothing_change(self, sim_info, outfit_change_category):
        return (outfit_change_category, 0)

class _XevtOutfitChangeElement(ParentElement):

    def __init__(self, interaction, sequence, xevt_id, outfit_category, tag_list, filter_flag, body_type_chance_overrides, body_type_match_not_found_policy):
        super().__init__()
        self._interaction = interaction
        self._sequence = sequence
        self._outfit_category = outfit_category
        self._tag_list = tag_list
        self._filter_flag = filter_flag
        self._body_type_chance_overrides = body_type_chance_overrides
        self._body_type_match_not_found_policy = body_type_match_not_found_policy
        self._xevt_id = xevt_id
        self._xevt_handle = None

    def _run_xevt_outfit_change(self):
        sim = self._interaction.get_participant(ParticipantType.Actor)
        sim.sim_info.generate_outfit(self._outfit_category, outfit_index=0, tag_list=self._tag_list, filter_flag=self._filter_flag, body_type_chance_overrides=self._body_type_chance_overrides, body_type_match_not_found_overrides=self._body_type_match_not_found_policy)
        sim.sim_info.set_current_outfit((self._outfit_category, 0))

    def _run(self, timeline):
        sequence = self._sequence

        def register_xevt(_):
            self._xevt_handle = self._interaction.animation_context.register_event_handler(lambda _: self._run_xevt_outfit_change(), handler_id=self._xevt_id)

        def release_xevt(_):
            self._xevt_handle.release()
            self._xevt_handle = None

        sequence = build_critical_section(register_xevt, sequence, release_xevt)
        return timeline.run_child(sequence)

class OutfitChangeSelfInteraction(OutfitGeneratorRandomizationMixin, SuperInteraction):
    INSTANCE_TUNABLES = {'outfit_change_type': TunableVariant(description='\n            Possible ingredient mapping by object definition of by \n            catalog object Tag.\n            ', from_situation=OutfitChangeSituation.TunableFactory(), from_outfit_tags=OutfitChangeTags.TunableFactory()), 'outfit_change_category': TunableEnumEntry(description='\n            The outfit category the change will be tied to.\n            ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY), 'xevt_id': OptionalTunable(description="\n            If enabled, the outfit change will run at the specified xevt,\n            otherwise the outfit change will run at the end of the \n            interaction's basic content.\n            ", tunable=Tunable(description='\n                Xevt id to trigger outfit change on.\n                ', tunable_type=int, default=100))}

    def __init__(self, aop, context, outfit_tags=None, **kwargs):
        super().__init__(aop, context, **kwargs)
        self.outfit_tags = outfit_tags

    @classmethod
    def _shared_potential_interactions(cls, sim, target, context, **kwargs):
        if sim is None:
            return
        yield from cls.outfit_change_type.outfit_affordances_gen(sim, target, cls, **kwargs)

    def build_basic_elements(self, sequence=()):
        sequence = super().build_basic_elements(sequence=sequence)
        if self.xevt_id is None:
            outfit = self.sim.get_current_outfit()
            generate_outfit_fn = functools.partial(self._generate_outfit, self.sim.sim_info, self.outfit_change_category, outfit_index=0, tag_list=self.outfit_tags)
            if outfit == (self.outfit_change_category, 0):
                self.sim.sim_info.set_outfit_dirty(outfit[0])
                generate_outfit_element = lambda _: generate_outfit_fn()
            else:
                generate_outfit_element = None
                generate_outfit_fn()
            new_outfit = self.outfit_change_type.get_outfit_for_clothing_change(self.sim.sim_info, self.outfit_change_category)
            sequence = build_critical_section(sequence, self.sim.sim_info.get_change_outfit_element_and_archive_change_reason(new_outfit, interaction=self, change_reason=self), flush_all_animations)
            return build_critical_section(sequence, generate_outfit_element)
        else:
            outfit_change_element = _XevtOutfitChangeElement(self, sequence, self.xevt_id, self.outfit_change_category, self.outfit_tags, self.filter_flag, self.body_type_chance_overrides, self.body_type_match_not_found_policy)
            return outfit_change_element

    @classmethod
    def potential_interactions(cls, target, context, **kwargs):
        change_outfit_target = None if context.sim is target else target
        return cls._shared_potential_interactions(context.sim, change_outfit_target, context)

    @staticmethod
    def _get_interaction_name(cls, outfit_tags, target=DEFAULT, context=DEFAULT, **interaction_parameters):
        for tag in outfit_tags:
            localized_string = OutfitTuning.COSTUMES_LOCALIZATION_TUNING.get(tag)
            if localized_string is not None:
                return cls.create_localized_string(localized_string, context=context, target=target)
        logger.error('Outfit interaction {} has a situation with tags {} not tuned on sim_outfits module tuning', cls, outfit_tags, owner='camilogarcia')

    @flexmethod
    def _get_name(cls, inst, target=DEFAULT, context=DEFAULT, outfit_tags=None, **interaction_parameters):
        if inst is not None:
            return cls._get_interaction_name(cls, inst.outfit_tags, target=inst.target, context=inst.context, **interaction_parameters)
        return cls._get_interaction_name(cls, outfit_tags, target=target, context=context, **interaction_parameters)
