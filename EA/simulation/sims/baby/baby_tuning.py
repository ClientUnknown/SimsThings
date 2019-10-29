import randomfrom sims4.tuning.tunable import TunableReference, TunableMapping, TunableEnumEntry, TunableSkinTone, TunableList, TunableTuplefrom sims4.tuning.tunable_base import ExportModesfrom traits.traits import Traitimport enumimport services
class BabySkinTone(enum.Int):
    LIGHT = 0
    MEDIUM = 1
    DARK = 2
    BLUE = 3
    GREEN = 4
    RED = 5
    ALIEN_BLUE = 6
    ALIEN_BLUE_LIGHT = 7
    ALIEN_GREEN = 8
    ALIEN_GREEN_LIGHT = 9
    ALIEN_PURPLE = 10
    ALIEN_PURPLE_LIGHT = 11
    ALIEN_TEAL = 12
    ALIEN_TEAL_LIGHT = 13
    ALIEN_WHITE = 14
    ADULT_SIM = 15

class BabyTuning:
    BABY_THUMBNAIL_DEFINITION = TunableReference(description='\n        The thumbnail definition for client use only.\n        ', manager=services.definition_manager(), export_modes=(ExportModes.ClientBinary,))
    BABY_BASSINET_DEFINITION_MAP = TunableMapping(description='\n        The corresponding mapping for each definition pair of empty bassinet and\n        bassinet with baby inside. The reason we need to have two of definitions\n        is one is deletable and the other one is not.\n        ', key_name='Baby', key_type=TunableReference(description='\n            The definition of an object that is a bassinet containing a fully\n            functioning baby.\n            ', manager=services.definition_manager(), pack_safe=True), value_name='EmptyBassinet', value_type=TunableReference(description='\n            The definition of an object that is an empty bassinet.\n            ', manager=services.definition_manager(), pack_safe=True))
    BABY_DEFAULT_BASSINETS = TunableList(description='\n        A list of trait to default bassinet definitions. This is used when\n        generating default bassinets for specific babies. The list is evaluated\n        in order. Should no element be selected, an entry from\n        BABY_BASSINET_DEFINITION_MAP is selected instead.\n        ', tunable=TunableTuple(description='\n            Should the baby have any of the specified traits, select a bassinet\n            from the list of bassinets.\n            ', traits=TunableList(description='\n                This entry is selected should the Sim have any of these traits.\n                ', tunable=Trait.TunableReference(pack_safe=True)), bassinets=TunableList(description='\n                Should this entry be selected, a random bassinet from this list\n                is chosen.\n                ', tunable=TunableReference(manager=services.definition_manager(), pack_safe=True))))
    BABY_SKIN_TONE_TO_CAS_SKIN_TONE = TunableMapping(description='\n        A mapping from the Skin Tone enum to a CAS skin tone ID.\n        ', key_type=TunableEnumEntry(tunable_type=BabySkinTone, default=BabySkinTone.MEDIUM), value_type=TunableList(description='\n            The skin tone CAS reference.\n            ', tunable=TunableSkinTone(pack_safe=True)), export_modes=ExportModes.All, tuple_name='BabySkinToneToCasTuple')

    @staticmethod
    def get_default_definition(sim_info):
        for entry in BabyTuning.BABY_DEFAULT_BASSINETS:
            if not entry.bassinets:
                pass
            else:
                if entry.traits:
                    if any(sim_info.has_trait(trait) for trait in entry.traits):
                        return random.choice(entry.bassinets)
                return random.choice(entry.bassinets)
        return next(iter(BabyTuning.BABY_BASSINET_DEFINITION_MAP), None)

    @staticmethod
    def get_corresponding_definition(definition):
        if definition in BabyTuning.BABY_BASSINET_DEFINITION_MAP:
            return BabyTuning.BABY_BASSINET_DEFINITION_MAP[definition]
        for (baby_def, bassinet_def) in BabyTuning.BABY_BASSINET_DEFINITION_MAP.items():
            if bassinet_def is definition:
                return baby_def

    @staticmethod
    def get_baby_skin_tone_enum(sim_info):
        if sim_info.is_baby:
            skin_tone_id = sim_info.skin_tone
            for (skin_enum, tone_ids) in BabyTuning.BABY_SKIN_TONE_TO_CAS_SKIN_TONE.items():
                if skin_tone_id in tone_ids:
                    return skin_enum
            return BabySkinTone.LIGHT
        return BabySkinTone.ADULT_SIM
