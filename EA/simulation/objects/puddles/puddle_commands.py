from objects.puddles import create_puddle, PuddleSize, PuddleLiquidfrom objects.puddles.puddle import Puddlefrom server_commands.argument_helpers import OptionalTargetParam, get_optional_target, RequiredTargetParamimport sims4.commands
@sims4.commands.Command('puddles.create')
def puddle_create(count:int=1, size:PuddleSize=PuddleSize.MediumPuddle, liquid=PuddleLiquid.WATER, obj:OptionalTargetParam=None, _connection=None):
    obj = get_optional_target(obj, _connection)
    if obj is None:
        return False
    for _ in range(count):
        puddle = create_puddle(size, liquid)
        if puddle is None:
            return False
        puddle.place_puddle(obj, max_distance=8)
    return True

@sims4.commands.Command('puddles.evaporate')
def puddle_evaporate(obj_id:RequiredTargetParam, _connection=None):
    obj = obj_id.get_target()
    if obj is None:
        return False
    if not isinstance(obj, Puddle):
        return False
    obj.evaporate(None)
    return True

@sims4.commands.Command('puddles.grow')
def puddle_grow(obj_id:RequiredTargetParam, _connection=None):
    obj = obj_id.get_target()
    if obj is None:
        return False
    if not isinstance(obj, Puddle):
        return False
    obj.try_grow_puddle()
    return True
