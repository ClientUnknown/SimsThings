import itertoolsfrom cas.cas import get_caspart_bodytypefrom sims.outfits.outfit_enums import OutfitCategory, CLOTHING_BODY_TYPES, OutfitFilterFlag, BodyType, MatchNotFoundPolicy, BodyTypeFlagfrom sims4.tuning.tunable import TunableEnumFlags, TunableMapping, TunablePercent
def get_maximum_outfits_for_category(outfit_category):
    if outfit_category == OutfitCategory.BATHING or outfit_category == OutfitCategory.SITUATION:
        return 1
    if outfit_category == OutfitCategory.SPECIAL:
        return 2
    elif outfit_category == OutfitCategory.CAREER:
        return 3
    return 5

def is_sim_info_wearing_all_outfit_parts(sim_info, outfit, outfit_key):
    outfit_data = outfit.get_outfit(*outfit_key)
    current_outfit_data = sim_info.get_outfit(*sim_info.get_current_outfit())
    return set(part_id for part_id in outfit_data.part_ids if get_caspart_bodytype(part_id) in CLOTHING_BODY_TYPES).issubset(set(current_outfit_data.part_ids))

class OutfitGeneratorRandomizationMixin:
    INSTANCE_TUNABLES = {'filter_flag': TunableEnumFlags(description='\n            Define how to handle part randomization for the generated outfit.\n            ', enum_type=OutfitFilterFlag, default=OutfitFilterFlag.USE_EXISTING_IF_APPROPRIATE | OutfitFilterFlag.USE_VALID_FOR_LIVE_RANDOM, allow_no_flags=True), 'body_type_chance_overrides': TunableMapping(description='\n            Define body type chance overrides for the generate outfit. For\n            example, if BODYTYPE_HAT is mapped to 100%, then the outfit is\n            guaranteed to have a hat if any hat matches the specified tags.\n            \n            If used in an appearance modifier, these body types will contribute\n            to the flags that determine which body types can be generated,\n            regardless of their percent chance.\n            ', key_type=BodyType, value_type=TunablePercent(description='\n                The chance that a part is applied to the corresponding body\n                type.\n                ', default=100)), 'body_type_match_not_found_policy': TunableMapping(description='\n            The policy we should take for a body type that we fail to find a\n            match for. Primary example is to use MATCH_NOT_FOUND_KEEP_EXISTING\n            for generating a tshirt and making sure a sim wearing full body has\n            a lower body cas part.\n            \n            If used in an appearance modifier, these body types will contribute\n            to the flags that determine which body types can be generated.\n            ', key_type=BodyType, value_type=MatchNotFoundPolicy)}
    FACTORY_TUNABLES = INSTANCE_TUNABLES

    def get_body_type_flags(self):
        tuned_flags = 0
        for body_type in itertools.chain(self.body_type_chance_overrides.keys(), self.body_type_match_not_found_policy.keys()):
            tuned_flags |= 1 << body_type
        return tuned_flags or BodyTypeFlag.CLOTHING_ALL

    def _generate_outfit(self, sim_info, outfit_category, outfit_index=0, tag_list=(), seed=None):
        sim_info.generate_outfit(outfit_category, outfit_index=outfit_index, tag_list=tag_list, filter_flag=self.filter_flag, body_type_chance_overrides=self.body_type_chance_overrides, body_type_match_not_found_overrides=self.body_type_match_not_found_policy, seed=seed)
