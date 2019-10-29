from event_testing.resolver import DoubleSimResolverfrom relationships.relationship_bit import RelationshipBitfrom relationships.relationship_track import RelationshipTrackfrom sims.sim_info_types import Speciesfrom sims4.tuning.dynamic_enum import DynamicEnumfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, Tunable, TunableSet, TunableMapping, TunableEnumEntry, TunableList, TunableTuplefrom tunable_multiplier import TunableMultiplierfrom tunable_utils.tested_list import TunableTestedListimport servicesimport sims4.random
class DefaultGenealogyLink(DynamicEnum):
    Roommate = 0
    FamilyMember = 1
    Spouse = 2

class DefaultRelationship(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'relationship_tracks': TunableList(description='\n            A list of relationship track and value pairs. E.g. a spouse has\n            Romantic relationship track value of 75.\n            ', tunable=TunableTuple(track=RelationshipTrack.TunableReference(description='\n                    The relationship track that is added to the relationship\n                    between the two sims.\n                    ', pack_safe=True), value=Tunable(description='\n                    The relationship track is set to this value.\n                    ', tunable_type=int, default=0))), 'relationship_bits': TunableSet(description='\n            A set of untracked relationship bits that are applied to the\n            relationship between the two sims. These are bits that are provided\n            outside of the relationship_track being set. E.g. everyone in the\n            household should have the Has Met bit and the spouse should have the\n            First Kiss bit.\n            ', tunable=RelationshipBit.TunableReference(pack_safe=True)), 'random_relationship_bits': TunableList(description='\n            A list of random relationship bits that can be applied.\n            ', tunable=TunableList(description='\n                A list of relationship bits and weights that that relationship\n                bit can be chosen to add.\n                ', tunable=TunableTuple(description='\n                    A number of weighted relationship bits that have a chance\n                    of being applied.\n                    ', bit=RelationshipBit.TunableReference(pack_safe=True), weight=TunableMultiplier.TunableFactory(description='\n                        A tunable list of tests and multipliers to apply to the \n                        weight of this relationship bit being applied.\n                        '))))}

    def apply(self, relationship, actor_sim_id, target_sim_id, bits_only=False):
        sim_to_target_tracker = relationship.relationship_track_tracker
        if not bits_only:
            try:
                sim_to_target_tracker.suppress_callback_setup_during_load = True
                sim_to_target_tracker.load_in_progress = True
                for data in self.relationship_tracks:
                    track = data.track
                    value = data.value
                    relationship_track = sim_to_target_tracker.get_statistic(track, True)
                    if relationship_track is None:
                        pass
                    else:
                        if relationship_track.get_value() < value:
                            sim_to_target_tracker.set_value(track, value, apply_initial_modifier=True)
                        (old_bit, new_bit) = relationship_track.update_instance_data()
                        if old_bit is not None and old_bit is not new_bit:
                            relationship.remove_bit(actor_sim_id, target_sim_id, old_bit)
                        if new_bit is not None and not relationship.has_bit(actor_sim_id, new_bit):
                            relationship.add_relationship_bit(actor_sim_id, target_sim_id, new_bit)
                        relationship_track.fixup_callbacks_during_load()
            finally:
                sim_to_target_tracker.suppress_callback_setup_during_load = False
                sim_to_target_tracker.load_in_progress = False
        for bit in self.relationship_bits:
            relationship.add_relationship_bit(actor_sim_id, target_sim_id, bit)
        sim_info_manager = services.sim_info_manager()
        actor_sim_info = sim_info_manager.get(actor_sim_id)
        target_sim_info = sim_info_manager.get(target_sim_id)
        resolver = DoubleSimResolver(actor_sim_info, target_sim_info)
        for random_relationships in self.random_relationship_bits:
            weights = []
            for random_bit in random_relationships:
                weight = random_bit.weight.get_multiplier(resolver)
                if weight > 0:
                    weights.append((weight, random_bit.bit))
            if weights:
                selected_bit = sims4.random.weighted_random_item(weights)
                relationship.add_relationship_bit(actor_sim_id, target_sim_id, selected_bit)

class DefaultRelationshipInHousehold:
    RelationshipSetupMap = TunableMapping(description='\n        A mapping of the possible genealogy links in a family to the default \n        relationship values that we want to start our household members. \n        ', key_name='Family Link', key_type=TunableEnumEntry(description='\n            A genealogy link between the two Sims in the household.\n            ', tunable_type=DefaultGenealogyLink, default=DefaultGenealogyLink.Roommate), value_name='Default Relationship Setup', value_type=TunableTestedList(description='\n            A list of relationship actions to apply.\n            ', tunable_type=DefaultRelationship.TunableFactory()))
    SPECIES_TO_ROOMATE_LINK = TunableList(description='\n        Define what the "roommate" relationship, i.e. two Sims unrelated by\n        blood or marriage within the same household translates to. For instance,\n        two humans would use the regular "Roommate" link, but a human and a dog\n        would use an "owner/pet" link.\n        ', tunable=TunableTuple(description='\n            An entry that defines the "roommate" mapping for two Sims.\n            ', species_actor=TunableEnumEntry(description='\n                The species of the actor Sim, i.e. the Sim that is going to own\n                any applied bits.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), species_target=TunableEnumEntry(description='\n                The species of the target Sim, i.e. the Sim that is going to be\n                the target of any bit applied to the actor.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), genealogy_link=TunableEnumEntry(description='\n                The default genealogy link to create between two Sims of the\n                specified species.\n                ', tunable_type=DefaultGenealogyLink, default=DefaultGenealogyLink.Roommate)))
    SPECIES_TO_FAMILY_MEMBER_LINK = TunableList(description='\n        Define what the "family member" relationship, i.e. two Sims related by\n        blood or marriage within the same household translates to. For instance,\n        humans would use the regular "FamilyMember" link, but dogs would use a\n        dog specific link.\n        \n        It\'s assumed that the two sims involved are the same species.\n        ', tunable=TunableTuple(description='\n            An entry that defines the "family member" mapping for two Sims.\n            ', species=TunableEnumEntry(description='\n                The species of the family members.\n                ', tunable_type=Species, default=Species.HUMAN, invalid_enums=(Species.INVALID,)), genealogy_link=TunableEnumEntry(description='\n                The default genealogy link to create between two Sims of the\n                specified species.\n                ', tunable_type=DefaultGenealogyLink, default=DefaultGenealogyLink.FamilyMember)))
