import randomfrom objects.definition_manager import TunableDefinitionListfrom sims4.tuning.dynamic_enum import DynamicEnumimport enumimport objects.systemimport sims4.reloadwith sims4.reload.protected(globals()):
    _puddle_lookup = {}
class PuddleSize(enum.Int):
    NoPuddle = 0
    SmallPuddle = 1
    MediumPuddle = 2
    LargePuddle = 3

class PuddleLiquid(DynamicEnum, partitioned=True):
    INVALID = -1
    WATER = 0

def create_puddle(puddle_size, puddle_liquid=PuddleLiquid.WATER):
    key = (puddle_liquid, puddle_size)
    if key not in _puddle_lookup:
        return
    available_definitions = _puddle_lookup[key]

    def init(obj):
        obj.opacity = 0

    return objects.system.create_object(random.choice(available_definitions), init=init)

def populuate_puddle_choices_lookup(instance_class, tunable_name, source, value):
    _puddle_lookup.clear()
    for definition in value:
        cls = definition.cls
        key = (cls.puddle_liquid, cls.puddle_size)
        if key not in _puddle_lookup:
            _puddle_lookup[key] = []
        _puddle_lookup[key].append(definition)

class PuddleChoices:
    PUDDLE_DEFINITIONS = TunableDefinitionList(description='\n        All puddles that can be created through gameplay. Should not include\n        block models and other dev-only puddles.\n        ', pack_safe=True, callback=populuate_puddle_choices_lookup)
