from cas.cas import set_caspart, get_caspart_bodytype, randomize_part_color, randomize_skintone_from_tags, randomize_caspartfrom sims.outfits.outfit_enums import BodyType, OutfitCategory, BodyTypeFlagfrom sims.outfits.outfit_generator import OutfitGeneratorfrom sims.sim_info_base_wrapper import SimInfoBaseWrapperfrom sims4.repr_utils import standard_reprfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import HasTunableSingletonFactory, AutoFactoryInit, TunableCasPart, TunableEnumEntry, TunableList, TunableVariant, Tunable, OptionalTunable, TunableTuple, TunableSet, TunableMappingfrom tag import TagCategory, TunableTagfrom tunable_multiplier import TunableMultiplierfrom tunable_utils.tunable_white_black_list import TunableWhiteBlackListimport enumimport sims4import taglogger = sims4.log.Logger('Appearance')
class AppearanceModifierType(enum.Int):
    SET_CAS_PART = 0
    RANDOMIZE_BODY_TYPE_COLOR = 1
    RANDOMIZE_SKINTONE_FROM_TAGS = 2
    GENERATE_OUTFIT = 3
    RANDOMIZE_CAS_PART = 4

class AppearanceModifierPriority(DynamicEnum):
    INVALID = 0

class AppearanceModifier(HasTunableSingletonFactory, AutoFactoryInit):

    class BaseAppearanceModification(HasTunableSingletonFactory, AutoFactoryInit):
        FACTORY_TUNABLES = {'_is_combinable_with_same_type': Tunable(description='\n                True if this modifier type is able to be combined with another\n                of its type. If True, and two modifiers conflict, then the tuned\n                priority will be used to resolve the conflict. If False, only\n                a single modifier of this type with the highest priority will be shown.\n                ', tunable_type=bool, default=True), 'outfit_type_compatibility': OptionalTunable(description='\n                If enabled, will verify when switching outfits if the new\n                outfit is compatible with this appearance modifier.\n                ', disabled_name="Don't_Test", tunable=TunableWhiteBlackList(description='\n                    The outfit category must match the whitelist and blacklist\n                    to be applied.\n                    ', tunable=TunableEnumEntry(description='\n                        The outfit category want to test against the \n                        apperance modifier.\n                        ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY))), 'appearance_modifier_tag': OptionalTunable(description='\n                If enabled, a tag used to reference this appearance modifier.\n                ', tunable=TunableTag(description='\n                    Tag associated with this appearance modifier.\n                    '))}

        def modify_sim_info(self, source_sim_info, modified_sim_info, random_seed):
            raise NotImplementedError('Attempting to use the BaseAppearanceModification base class, use sub-classes instead.')

        @property
        def is_permanent_modification(self):
            return False

        @property
        def modifier_type(self):
            raise NotImplementedError('Attempting to use the BaseAppearanceModification base class, use sub-classes instead.')

        @property
        def is_combinable_with_same_type(self):
            return self._is_combinable_with_same_type

        @property
        def combinable_sorting_key(self):
            raise NotImplementedError('Attempting to use the BaseAppearanceModification base class, use sub-classes instead.')

        def is_compatible_with_outfit(self, outfit_category):
            if self.outfit_type_compatibility is None:
                return True
            return self.outfit_type_compatibility.test_item(outfit_category)

    class SetCASPart(BaseAppearanceModification):
        FACTORY_TUNABLES = {'cas_part': TunableCasPart(description='\n                The CAS part that will be modified.\n                '), 'should_toggle': Tunable(description="\n                Whether or not to toggle this part. e.g. if it exists, remove\n                it, if it doesn't exist, add it. If set to false, the part will\n                be added if it doesn't exist, but not removed if it does exist.\n                ", tunable_type=bool, default=False), 'replace_with_random': Tunable(description='\n                Whether or not to replace the tuned cas part with a random\n                variant.\n                ', tunable_type=bool, default=False), 'remove_conflicting': Tunable(description='\n                If checked, conflicting parts are removed from the outfit. For\n                instance, a full body outfit might be removed if a part would\n                conflict with it.\n                \n                e.g.\n                 The Cone of Shame removes conflicting full-body pet outfits.\n                ', tunable_type=bool, default=False), 'update_genetics': Tunable(description='\n                Whether or not to update the genetics of the sim with this\n                modification to make it a permanent modification. NOTE: DO NOT\n                tune permanent with temporary modifications on the same\n                appearance modifier.\n                ', tunable_type=bool, default=False), 'expect_invalid_parts': Tunable(description="\n                Whether or not parts that are invalid for a sim should log an\n                error.  If we are expecting invalid parts, (say, buff gives one\n                part that applies to adults and a different part for children,)\n                then we should set this to True so that it doesn't throw the\n                error when it tries to apply the adult part on the child and\n                vice versa.\n                ", tunable_type=bool, default=False)}

        def modify_sim_info(self, source_sim_info, modified_sim_info, random_seed):
            if set_caspart(source_sim_info._base, modified_sim_info._base, self.cas_part, self.should_toggle, self.replace_with_random, self.update_genetics, random_seed, remove_conflicting=self.remove_conflicting):
                return BodyTypeFlag.make_body_type_flag(get_caspart_bodytype(self.cas_part))
            if not self.expect_invalid_parts:
                sis = []
                instanced_sim = source_sim_info.get_sim_instance()
                if instanced_sim is not None:
                    sis = instanced_sim.get_all_running_and_queued_interactions()
                active_mods = source_sim_info.appearance_tracker.active_displayed_appearance_modifiers()
                logger.error('Unable to set cas part {}\nSim: {}, Gender: {}, Age: {} \nActive Modifiers: \n{} \nInteractions: \n{}', self, source_sim_info, source_sim_info.gender, source_sim_info.age, active_mods, sis)
            return BodyTypeFlag.NONE

        @property
        def is_permanent_modification(self):
            return self.update_genetics

        @property
        def modifier_type(self):
            return AppearanceModifierType.SET_CAS_PART

        @property
        def combinable_sorting_key(self):
            return get_caspart_bodytype(self.cas_part)

        def __repr__(self):
            return standard_repr(self, cas_part=self.cas_part, should_toggle=self.should_toggle, replace_with_random=self.replace_with_random, update_genetics=self.update_genetics)

    class ReplaceCASPart(BaseAppearanceModification):

        @staticmethod
        def _verify_tunable_callback(instance_class, tunable_name, source, value, **kwargs):
            if len(value.replace_part_map) == 0 and value.default_set_part is None:
                logger.error('Cannot use ReplaceCASPart without a mapping or a default for {}', instance_class, owner='bosee')

        FACTORY_TUNABLES = {'replace_part_map': TunableMapping(description="\n                The CAS part (value) that will replace another CAS part (key)\n                if sim has that equipped. It currently only replaces the first \n                one which it finds. Nothing will be replaced if the sim doesn't\n                have any of the key CAS parts set. \n                ", key_type=TunableCasPart(description='\n                    CAS part to look up.\n                    '), value_type=TunableCasPart(description='\n                    If key CAS part is set, replace it with this CAS part.\n                    ')), 'default_set_part': OptionalTunable(description='\n                If set, this CAS part will be set if no parts are replaced with the \n                previous mapping.\n                ', tunable=TunableCasPart(description="\n                    The CAS part that will be modified. This doesn't take into account\n                    what has already been set on the sim.\n                    ")), 'update_genetics': Tunable(description='\n                Whether or not to update the genetics of the sim with this\n                modification to make it a permanent modification. NOTE: DO NOT\n                tune permanent with temporary modifications on the same\n                appearance modifier.\n                ', tunable_type=bool, default=False), 'expect_invalid_parts': Tunable(description="\n                Whether or not parts that are invalid for a sim should log an\n                error.  If we are expecting invalid parts, (say, buff gives one\n                part that applies to adults and a different part for children,)\n                then we should set this to True so that it doesn't throw the\n                error when it tries to apply the adult part on the child and\n                vice versa.\n                ", tunable_type=bool, default=False), 'verify_tunable_callback': _verify_tunable_callback}

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._last_modified_type = None

        def modify_sim_info(self, source_sim_info, modified_sim_info, random_seed):
            self._last_modified_type = None
            part_to_set = None
            for (key_part, value_part) in self.replace_part_map.items():
                if source_sim_info.get_outfits().has_cas_part(key_part):
                    part_to_set = value_part
                    break
            if self.default_set_part is not None:
                part_to_set = self.default_set_part
            if part_to_set is None and part_to_set is None:
                return BodyTypeFlag.NONE
            self._last_modified_type = get_caspart_bodytype(part_to_set)
            if set_caspart(source_sim_info._base, modified_sim_info._base, part_to_set, False, False, self.update_genetics, random_seed, remove_conflicting=True):
                return BodyTypeFlag.make_body_type_flag(get_caspart_bodytype(part_to_set))
            if not self.expect_invalid_parts:
                sis = []
                instanced_sim = source_sim_info.get_sim_instance()
                if instanced_sim is not None:
                    sis = instanced_sim.get_all_running_and_queued_interactions()
                active_mods = source_sim_info.appearance_tracker.active_displayed_appearance_modifiers()
                logger.error('Unable to set cas part {}\nSim: {}, Gender: {}, Age: {} \nActive Modifiers: \n{} \nInteractions: \n{}', self, source_sim_info, source_sim_info.gender, source_sim_info.age, active_mods, sis)
            return BodyTypeFlag.NONE

        @property
        def is_permanent_modification(self):
            return self.update_genetics

        @property
        def modifier_type(self):
            return AppearanceModifierType.SET_CAS_PART

        @property
        def combinable_sorting_key(self):
            return self._last_modified_type

        def __repr__(self):
            return standard_repr(self, default_set_part=self.default_set_part, update_genetics=self.update_genetics, expect_invalid_parts=self.expect_invalid_parts)

    class RandomizeCASPart(BaseAppearanceModification):
        FACTORY_TUNABLES = {'body_type': TunableEnumEntry(description='\n                The body type that will have its part randomized.\n                ', tunable_type=BodyType, default=BodyType.NONE, invalid_enums=(BodyType.NONE,)), 'tag_categories_to_keep': TunableSet(description='\n                Match tags from the existing CAS part of the specified body \n                type that belong to these tag categories when searching\n                for a new random part.\n                ', tunable=TunableEnumEntry(description='\n                    Tags that belong to this category that are on the existing\n                    CAS part of the specified body type will be used to find\n                    a new random part.\n                    ', tunable_type=TagCategory, default=TagCategory.INVALID, invalid_enums=(TagCategory.INVALID,)))}

        def modify_sim_info(self, source_sim_info, modified_sim_info, random_seed):
            if randomize_caspart(source_sim_info._base, modified_sim_info._base, self.body_type, list(self.tag_categories_to_keep), random_seed):
                return BodyTypeFlag.make_body_type_flag(self.body_type)
            return BodyTypeFlag.NONE

        @property
        def modifier_type(self):
            return AppearanceModifierType.RANDOMIZE_CAS_PART

        @property
        def combinable_sorting_key(self):
            return self.body_type

        def __repr__(self):
            return standard_repr(self, body_type=self.body_type)

    class RandomizeBodyTypeColor(BaseAppearanceModification):
        FACTORY_TUNABLES = {'body_type': TunableEnumEntry(description='\n                The body type that will have its color randomized.\n                ', tunable_type=BodyType, default=BodyType.NONE)}

        def modify_sim_info(self, source_sim_info, modified_sim_info, random_seed):
            if randomize_part_color(source_sim_info._base, modified_sim_info._base, self.body_type, random_seed):
                return BodyTypeFlag.make_body_type_flag(self.body_type)
            return BodyTypeFlag.NONE

        @property
        def modifier_type(self):
            return AppearanceModifierType.RANDOMIZE_BODY_TYPE_COLOR

        @property
        def combinable_sorting_key(self):
            return self.body_type

        def __repr__(self):
            return standard_repr(self, body_type=self.body_type)

    class RandomizeSkintoneFromTags(BaseAppearanceModification):
        FACTORY_TUNABLES = {'tag_list': TunableList(TunableEnumEntry(description='\n                    A specific tag.\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID)), 'locked_args': {'_is_combinable_with_same_type': False}}

        def modify_sim_info(self, source_sim_info, modified_sim_info, random_seed):
            randomize_skintone_from_tags(source_sim_info._base, modified_sim_info._base, list(self.tag_list), random_seed)
            return BodyTypeFlag.NONE

        @property
        def modifier_type(self):
            return AppearanceModifierType.RANDOMIZE_SKINTONE_FROM_TAGS

        def __repr__(self):
            return standard_repr(self, tag_list=self.tag_list)

    class GenerateOutfit(BaseAppearanceModification):
        FACTORY_TUNABLES = {'outfit_generator': OutfitGenerator.TunableFactory(description='\n                Inputs to generate the type of outfit we want.\n                '), 'outfit_override': OptionalTunable(description="\n                If enabled, we will generate the outfit on the tuned outfit\n                category and index. Otherwise, we use the Sim's current outfit\n                in the generator.\n                ", disabled_name='Current_Outfit', tunable=TunableEnumEntry(description='\n                    The outfit category we want to generate the outfit on.\n                    ', tunable_type=OutfitCategory, default=OutfitCategory.EVERYDAY))}

        @property
        def combinable_sorting_key(self):
            if self.outfit_override is not None:
                return self.outfit_override
            return OutfitCategory.EVERYDAY

        def modify_sim_info(self, source_sim_info, modified_sim_info, random_seed):
            (outfit_category, outfit_index) = (self.outfit_override, 0) if self.outfit_override is not None else source_sim_info.get_current_outfit()
            SimInfoBaseWrapper.copy_base_attributes(modified_sim_info, source_sim_info)
            SimInfoBaseWrapper.copy_physical_attributes(modified_sim_info, source_sim_info)
            modified_sim_info.load_outfits(source_sim_info.save_outfits())
            body_type_flags = self.outfit_generator.get_body_type_flags()
            with modified_sim_info.set_temporary_outfit_flags(outfit_category, outfit_index, body_type_flags):
                self.outfit_generator(modified_sim_info, outfit_category, outfit_index=outfit_index, seed=random_seed)
            return body_type_flags

        @property
        def modifier_type(self):
            return AppearanceModifierType.GENERATE_OUTFIT

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value, **kwargs):
        is_permanent_modification = None
        for tuned_modifiers in value.appearance_modifiers:
            if len(tuned_modifiers) == 1 and tuned_modifiers[0].weight.base_value != 1:
                logger.error('An appearance modifier has only one entry\n                                    in the list of modifiers and the weight of\n                                    that modifier is != 0. Instead it is {}', tuned_modifiers[0].weight.base_value, owner='rfleig')
            for entry in tuned_modifiers:
                if is_permanent_modification is None:
                    is_permanent_modification = entry.modifier.is_permanent_modification
                elif is_permanent_modification != entry.modifier.is_permanent_modification:
                    logger.error('An appearance modifier is attempting to combine a permanent\n                                        modifier with a temporary one. This is not supported.', owner='jwilkinson')
                    return

    FACTORY_TUNABLES = {'priority': TunableEnumEntry(description='\n            The priority of the appearance request. Higher priority will\n            take precedence over lower priority. Equal priority will favor\n            recent requests.\n            ', tunable_type=AppearanceModifierPriority, default=AppearanceModifierPriority.INVALID), 'appearance_modifiers': TunableList(description='\n            The specific appearance modifiers to use for this buff.\n            ', tunable=TunableList(description='\n                A tunable list of weighted modifiers. When applying modifiers\n                one of the modifiers in this list will be applied. The weight\n                will be used to run a weighted random selection.\n                ', tunable=TunableTuple(description='\n                    A Modifier to apply and weight for the weighted random \n                    selection.\n                    ', modifier=TunableVariant(set_cas_part=SetCASPart.TunableFactory(), replace_cas_part=ReplaceCASPart.TunableFactory(), randomize_cas_part=RandomizeCASPart.TunableFactory(), randomize_body_type_color=RandomizeBodyTypeColor.TunableFactory(), randomize_skintone_between_tags=RandomizeSkintoneFromTags.TunableFactory(), generate_outfit=GenerateOutfit.TunableFactory(), default='set_cas_part'), weight=TunableMultiplier.TunableFactory(description='\n                        A weight with testable multipliers that is used to \n                        determine how likely this entry is to be picked when \n                        selecting randomly.\n                        ')))), 'apply_to_all_outfits': Tunable(description='\n            If checked, the appearance modifiers will be applied to all outfits,\n            otherwise they will only be applied to the current outfit.\n            ', tunable_type=bool, default=True), 'verify_tunable_callback': _verify_tunable_callback}
