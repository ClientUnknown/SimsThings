import randomfrom filters.sim_template import SimTemplateType, TunableSimTemplatefrom relationships.global_relationship_tuning import RelationshipGlobalTuningfrom sims.genealogy_tracker import FamilyRelationshipIndexfrom sims.sim_info_types import Agefrom sims.sim_spawner import SimSpawnerfrom sims.sim_spawner_enums import SimNameTypefrom sims4.tuning.tunable import HasTunableReference, TunableList, TunableTuple, TunableEnumEntry, TunableRange, TunableEnumWithFilter, Tunable, TunablePercentfrom sims4.utils import classproperty, flexmethodfrom world.premade_sim_template import PremadeSimTemplateimport id_generatorimport relationships.relationship_bitimport servicesimport sims4.logimport sims4.resourcesimport sims4.tuning.instancesimport taglogger = sims4.log.Logger('HouseholdTemplate', default_owner='msantander')HOUSEHOLD_FILTER_PREFIX = ['household_member']
def _get_tunable_household_member_list(template_type, is_optional=False):
    if template_type == SimTemplateType.PREMADE_HOUSEHOLD:
        template_reference_type = PremadeSimTemplate
    else:
        template_reference_type = TunableSimTemplate
    tuple_elements = {'sim_template': template_reference_type.TunableReference(description='            \n            A template to use for creating a household member. If this\n            references a resource that is not installed, the household member is\n            ignored and the family is going to be created without this\n            individual.\n            ', pack_safe=is_optional), 'household_member_tag': TunableEnumWithFilter(description='            \n            Tag to be used to create relationship between sim members. This does\n            NOT have to be unique for all household templates. If you want to\n            add more tags in the tag tuning just add with prefix of\n            household_member.r.\n            ', tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=HOUSEHOLD_FILTER_PREFIX)}
    if is_optional:
        tuple_elements['chance'] = TunablePercent(description='\n            The chance that this household member is created when the household\n            is created. This is useful for "optional" Sims. For example, you\n            might want to tune a third of typical nuclear families to own a dog,\n            should the resource be available.\n            ', default=100)
    else:
        tuple_elements['locked_args'] = {'chance': 1}
    return TunableList(description='\n        A list of sim templates that will make up the sims in this household.\n        ', tunable=TunableTuple(**tuple_elements))

class HouseholdTemplate(HasTunableReference, metaclass=sims4.tuning.instances.TunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE)):
    INSTANCE_TUNABLES = {'_household_members': _get_tunable_household_member_list(template_type=SimTemplateType.HOUSEHOLD, is_optional=True), '_household_funds': TunableRange(description='\n            Starting funds for this household.\n            ', tunable_type=int, default=20000, minimum=0, maximum=99999999), '_household_relationship': TunableList(description='\n            Matrix of relationship that should be applied to household members.\n            ', tunable=TunableTuple(x=TunableEnumWithFilter(description='\n                    Tag of the household member to apply relationship to.\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=HOUSEHOLD_FILTER_PREFIX), y=TunableEnumWithFilter(description='\n                    Tag of the household member to be the target of relationship.\n                    ', tunable_type=tag.Tag, default=tag.Tag.INVALID, filter_prefixes=HOUSEHOLD_FILTER_PREFIX), is_spouse=Tunable(description='\n                    Check if x and y are spouses.\n                    ', tunable_type=bool, default=False), is_parentless_sibling=Tunable(description='\n                    Sibling relationship is automatically identified if x and y\n                    share a parent. If there is no parent in this household,\n                    checking this will establish their sibling relationship.\n                    \n                    At the moment, no additional family relationships are\n                    supported on these Sims. For example, these Sims cannot\n                    have an actual parent nor any children/grandchildren. If\n                    you require this functionality, please talk to a GPE.\n                    ', tunable_type=bool, default=False), family_relationship=TunableEnumEntry(description='\n                    This is the family relationship between x and y.\n                    Example: if set to Father, x is the the father of y.\n                    ', tunable_type=FamilyRelationshipIndex, default=None), relationship_bits=TunableList(description='\n                    Relationship bits that should be applied to x with\n                    the target y. Any bits with a relationship track will add\n                    relationship track at value that will add the bit to both\n                    sims.  Any bits without Triggered track will only be\n                    applied only to x unless it is a Siginificant other Bit.\n                    \n                    Example: If friendship-friend bit is supplied which has a\n                    triggered track of LTR_Friendship_Main, then\n                    LTR_Frienship_main will be added to both sims with a random\n                    value of the min/max value of the bit data tuning that will\n                    supply bit.\n                    ', tunable=relationships.relationship_bit.RelationshipBit.TunableReference())))}

    @classmethod
    def _verify_tuning_callback(cls):
        tag_to_household_member_index = {}
        for (index, household_member_data) in enumerate(cls._household_members):
            if household_member_data.household_member_tag != tag.Tag.INVALID:
                household_member_tag = household_member_data.household_member_tag
                if household_member_tag in tag_to_household_member_index:
                    logger.error('Multiple household member have the same tag {}.  Orginally found at index:{}, but also set for index:{}', household_member_tag, tag_to_household_member_index[household_member_tag], index)
                else:
                    tag_to_household_member_index[household_member_tag] = index
        if cls._household_relationship and not tag_to_household_member_index:
            logger.error('Houshold relationship has been added but there are no tag info for household members.  Please update tuning and add tags to household members: {}.', cls.__name__)
            return
        family_relationship_mapping = {}
        spouse_pairs = []
        parentless_members = set()
        for (index, member_relationship_data) in enumerate(cls._household_relationship):
            x_member = member_relationship_data.x
            if x_member == tag.Tag.INVALID:
                logger.error('No tag set for x in household relationship at index {}. Please update tuning and set a tag', index)
            else:
                y_member = member_relationship_data.y
                if y_member == tag.Tag.INVALID:
                    logger.error('No tag set for y in household relationship at index {}. Please update tuning and set a tag', index)
                else:
                    if x_member not in tag_to_household_member_index:
                        logger.error('The tag set for x :{} does not exist in household members. Please update tuning and update tag or set a household member with tag', x_member)
                    if y_member not in tag_to_household_member_index:
                        logger.error('The tag set for y :{} does not exist in household members. Please update tuning and update tag or set a household member with tag', y_member)
                    if member_relationship_data.is_spouse:
                        for member in (x_member, y_member):
                            member_index = tag_to_household_member_index[member]
                            sim_template = cls._household_members[member_index].sim_template
                            if sim_template.can_validate_age() and not sim_template.matches_creation_data(age_min=Age.YOUNGADULT):
                                logger.error('Trying set spouse with sims of the inappropriate age. Check sim_template at index {} if set correctly.', member_index)
                        spouse_pairs.append((x_member, y_member, index))
                        spouse_pairs.append((y_member, x_member, index))
                    if member_relationship_data.is_parentless_sibling:
                        parentless_members.add(x_member)
                        parentless_members.add(y_member)
                    family_set_at_index = family_relationship_mapping.get((x_member, y_member))
                    if family_set_at_index is not None:
                        logger.error('There is already a family relationship between x_member and y_member.Family set at index:{} but also set at index: {}', family_set_at_index, index)
                    if member_relationship_data.family_relationship is not None:
                        family_relationship_mapping[(x_member, y_member)] = index
                        family_relationship_mapping[(y_member, x_member)] = index
        if parentless_members:
            for (index, member_relationship_data) in enumerate(cls._household_relationship):
                if member_relationship_data.family_relationship is None:
                    pass
                else:
                    if not member_relationship_data.y in parentless_members:
                        if member_relationship_data.x in parentless_members:
                            logger.error('{} is a parentless sibling but has a family relationship at index: {}', member_relationship_data.y, index)
                    logger.error('{} is a parentless sibling but has a family relationship at index: {}', member_relationship_data.y, index)
        for (x_member, y_member, household_relationship_index) in spouse_pairs:
            family_set_at_index = family_relationship_mapping.get((x_member, y_member))
            if family_set_at_index is not None:
                logger.error('Spouse is set for {} and {}, but also have family relationship. Update tuning: either uncheck spouse at index: {} or remove family relationship in household relationshipat index {}', x_member, y_member, household_relationship_index, family_set_at_index)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._household_members_instance = []
        for household_member in self._household_members:
            if random.random() > household_member.chance:
                pass
            else:
                self._household_members_instance.append(household_member)

    @classproperty
    def template_type(cls):
        return SimTemplateType.HOUSEHOLD

    @flexmethod
    def get_household_members(cls, inst):
        if inst is not None:
            return inst._household_members_instance
        return cls._household_members

    @flexmethod
    def get_household_member_templates(cls, inst):
        inst_or_cls = inst if inst is not None else cls
        return tuple(household_member.sim_template for household_member in inst_or_cls.get_household_members())

    @classproperty
    def has_teen_or_below(cls):
        return any(not household_member_data.sim_template.matches_creation_data(age_min=Age.YOUNGADULT) for household_member_data in cls._household_members)

    @classmethod
    def get_number_of_guaranteed_members(cls):
        return sum(1 for entry in cls._household_members if entry.chance >= 1)

    @classproperty
    def has_spouse(cls):
        for household_relationship in cls._household_relationship:
            if not household_relationship.is_spouse:
                if RelationshipGlobalTuning.MARRIAGE_RELATIONSHIP_BIT in set(household_relationship.relationship_bits):
                    return True
            return True
        return False

    def matches_creation_data(self, *args, **kwargs):
        return any(household_member_template.matches_creation_data(*args, **kwargs) for household_member_template in self.get_household_member_templates())

    @flexmethod
    def create_household(cls, inst, zone_id, account=None, sim_creator=None, sim_name_type=SimNameType.DEFAULT, creation_source:str='household_template'):
        inst_or_cls = inst if inst is not None else cls
        sim_templates = inst_or_cls.get_household_member_templates()
        sim_creators = [sim_template.sim_creator for sim_template in sim_templates]
        matching_sim_creator_index = None
        if sim_creator is not None:
            matching_sim_creator_indices = [index for (index, sim_template) in enumerate(sim_templates) if sim_template.matches_creation_data(sim_creator=sim_creator)]
            if matching_sim_creator_indices:
                matching_sim_creator_index = random.choice(matching_sim_creator_indices)
                sim_creators[matching_sim_creator_index] = sim_creator
        home_zone_id = zone_id or 0
        (created_sim_infos, household) = SimSpawner.create_sim_infos(sim_creators, zone_id=home_zone_id, account=account, starting_funds=cls._household_funds, sim_name_type=sim_name_type, creation_source=creation_source)
        household.set_household_lot_ownership(zone_id=home_zone_id)
        for (index, (created_sim_info, sim_creator, sim_template)) in enumerate(zip(created_sim_infos, sim_creators, sim_templates)):
            sim_template.add_template_data_to_sim(created_sim_info, sim_creator)
        inst_or_cls.set_household_relationships(created_sim_infos, household)
        if matching_sim_creator_index is not None:
            return (household, created_sim_infos[matching_sim_creator_index])
        return household

    @flexmethod
    def set_household_relationships(cls, inst, created_sim_infos, household):
        inst_or_cls = inst if inst is not None else cls
        tag_to_sim_info = {household_member.household_member_tag: sim_info for (household_member, sim_info) in zip(inst_or_cls.get_household_members(), created_sim_infos) if household_member.household_member_tag != tag.Tag.INVALID}
        cls.set_household_relationships_by_tags(tag_to_sim_info, household)

    @classmethod
    def set_household_relationships_by_tags(cls, tag_to_sim_info, household):
        for member_relationship_data in cls._household_relationship:
            source_sim_info = tag_to_sim_info.get(member_relationship_data.x)
            target_sim_info = tag_to_sim_info.get(member_relationship_data.y)
            if not source_sim_info is None:
                if target_sim_info is None:
                    pass
                else:
                    if member_relationship_data.is_spouse:
                        source_sim_info.update_spouse_sim_id(target_sim_info.id)
                        target_sim_info.update_spouse_sim_id(source_sim_info.id)
                    if member_relationship_data.is_parentless_sibling:
                        parent_id = source_sim_info.genealogy.get_family_relation(FamilyRelationshipIndex.MOTHER) or (target_sim_info.genealogy.get_family_relation(FamilyRelationshipIndex.MOTHER) or id_generator.generate_object_id())
                        source_sim_info.genealogy.set_family_relation(FamilyRelationshipIndex.MOTHER, parent_id)
                        target_sim_info.genealogy.set_family_relation(FamilyRelationshipIndex.MOTHER, parent_id)
                    if member_relationship_data.family_relationship is not None:
                        target_sim_info.set_and_propagate_family_relation(member_relationship_data.family_relationship, source_sim_info)
        household.set_default_relationships()
        for member_relationship_data in cls._household_relationship:
            source_sim_info = tag_to_sim_info.get(member_relationship_data.x)
            target_sim_info = tag_to_sim_info.get(member_relationship_data.y)
            if not source_sim_info is None:
                if target_sim_info is None:
                    pass
                else:
                    for bit_to_add in member_relationship_data.relationship_bits:
                        bit_triggered_track = bit_to_add.triggered_track
                        if bit_triggered_track is not None:
                            bit_track_node = bit_to_add.triggered_track.get_bit_track_node_for_bit(bit_to_add)
                        else:
                            bit_track_node = None
                        if bit_track_node is not None:
                            if bit_track_node.remove_value > bit_track_node.add_value:
                                rand_score = random.randint(bit_track_node.add_value, bit_track_node.remove_value)
                            else:
                                rand_score = random.randint(bit_track_node.remove_value, bit_track_node.add_value)
                            source_sim_info.relationship_tracker.add_relationship_score(target_sim_info.id, rand_score, bit_triggered_track)
                        else:
                            source_sim_info.relationship_tracker.add_relationship_bit(target_sim_info.id, bit_to_add, force_add=True)
