from _collections import defaultdictfrom event_testing.resolver import DoubleSimResolverfrom filters.sim_template import SimTemplateTypefrom interactions.utils.loot import LootActionsfrom sims4.tuning.tunable import TunableTuple, TunableListfrom world.premade_sim_template import PremadeSimTemplateimport servicesimport sims4.loglogger = sims4.log.Logger('PremadeSimRelationships', default_owner='tingyul')
class PremadeSimRelationships:

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value):
        sim_to_household = {}
        for household in services.get_instance_manager(sims4.resources.Types.SIM_TEMPLATE).types.values():
            if household.template_type != SimTemplateType.PREMADE_HOUSEHOLD:
                pass
            else:
                for sim in household.get_household_members():
                    sim_to_household[sim.sim_template] = household
        pairs = set()
        for entry in value:
            a = entry.sim_a
            b = entry.sim_b
            if a is None:
                if b is not None:
                    logger.error('Premade Sim has rel with a Sim in unloaded pack. a: {}', a.__name__)
                    if b is None:
                        if a is not None:
                            logger.error('Premade Sim has rel with a Sim in unloaded pack. b: {}', b.__name__)
                            if entry.relationship_loot is None:
                                logger.error('Premade Sims have relationship loot in unloaded pack. a: {}, b: {}', a.__name__, b.__name__)
                            elif a is b:
                                logger.error('Premade Sim has rel with himself/herself. a: {}, b: {}', a.__name__, b.__name__)
                            elif sim_to_household[a] is sim_to_household[b]:
                                logger.error('Premade Sim has rel with Sim in same household. a: {}, b: {}', a.__name__, b.__name__)
                            else:
                                key = (a.guid64, b.guid64)
                                reverse_key = (b.guid64, a.guid64)
                                if key in pairs or reverse_key in pairs:
                                    logger.error('Multiple rel tuning between preamde Sims. a: {}, b: {}', a.__name__, b.__name__)
                                pairs.add(key)
                    elif entry.relationship_loot is None:
                        logger.error('Premade Sims have relationship loot in unloaded pack. a: {}, b: {}', a.__name__, b.__name__)
                    elif a is b:
                        logger.error('Premade Sim has rel with himself/herself. a: {}, b: {}', a.__name__, b.__name__)
                    elif sim_to_household[a] is sim_to_household[b]:
                        logger.error('Premade Sim has rel with Sim in same household. a: {}, b: {}', a.__name__, b.__name__)
                    else:
                        key = (a.guid64, b.guid64)
                        reverse_key = (b.guid64, a.guid64)
                        if key in pairs or reverse_key in pairs:
                            logger.error('Multiple rel tuning between preamde Sims. a: {}, b: {}', a.__name__, b.__name__)
                        pairs.add(key)
            elif b is None:
                if a is not None:
                    logger.error('Premade Sim has rel with a Sim in unloaded pack. b: {}', b.__name__)
                    if entry.relationship_loot is None:
                        logger.error('Premade Sims have relationship loot in unloaded pack. a: {}, b: {}', a.__name__, b.__name__)
                    elif a is b:
                        logger.error('Premade Sim has rel with himself/herself. a: {}, b: {}', a.__name__, b.__name__)
                    elif sim_to_household[a] is sim_to_household[b]:
                        logger.error('Premade Sim has rel with Sim in same household. a: {}, b: {}', a.__name__, b.__name__)
                    else:
                        key = (a.guid64, b.guid64)
                        reverse_key = (b.guid64, a.guid64)
                        if key in pairs or reverse_key in pairs:
                            logger.error('Multiple rel tuning between preamde Sims. a: {}, b: {}', a.__name__, b.__name__)
                        pairs.add(key)
            elif entry.relationship_loot is None:
                logger.error('Premade Sims have relationship loot in unloaded pack. a: {}, b: {}', a.__name__, b.__name__)
            elif a is b:
                logger.error('Premade Sim has rel with himself/herself. a: {}, b: {}', a.__name__, b.__name__)
            elif sim_to_household[a] is sim_to_household[b]:
                logger.error('Premade Sim has rel with Sim in same household. a: {}, b: {}', a.__name__, b.__name__)
            else:
                key = (a.guid64, b.guid64)
                reverse_key = (b.guid64, a.guid64)
                if key in pairs or reverse_key in pairs:
                    logger.error('Multiple rel tuning between preamde Sims. a: {}, b: {}', a.__name__, b.__name__)
                pairs.add(key)

    RELATIONSHIP_MAP = TunableList(description='\n        Relationship to give between premade Sims in different households.\n        ', tunable=TunableTuple(description='\n            Two Sims and a loot. The two Sims must be in different premade\n            households, and there can only be one entry per pair of Sims.\n            ', sim_a=PremadeSimTemplate.TunablePackSafeReference(description='\n                Relationship Loot uses this Sim as Actor.\n                '), sim_b=PremadeSimTemplate.TunablePackSafeReference(description='\n                Relationship Loot uses this Sim as TargetSim.\n                '), relationship_loot=LootActions.TunablePackSafeReference(description='\n                Loot that contains relationship to add between the two Sims.\n                Sim A is Actor and Sim B is TargetSim.\n                ')), verify_tunable_callback=_verify_tunable_callback)

    @classmethod
    def apply_relationships(cls, premade_sim_infos):
        loot_matrix = defaultdict(dict)
        for entry in PremadeSimRelationships.RELATIONSHIP_MAP:
            if not entry.sim_a is None:
                if entry.sim_b is None:
                    pass
                else:
                    loot_matrix[entry.sim_a][entry.sim_b] = entry.relationship_loot
        for (premade_sim_template, sim_info) in premade_sim_infos.items():
            if premade_sim_template not in loot_matrix:
                pass
            else:
                for (other_template, rel_loot) in loot_matrix[premade_sim_template].items():
                    if other_template not in premade_sim_infos:
                        pass
                    else:
                        other_sim_info = premade_sim_infos[other_template]
                        resolver = DoubleSimResolver(sim_info, other_sim_info)
                        rel_loot.apply_to_resolver(resolver)
