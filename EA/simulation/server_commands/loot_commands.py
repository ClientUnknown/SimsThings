from event_testing.resolver import SingleSimResolver, DoubleObjectResolverfrom server_commands.argument_helpers import TunableInstanceParam, OptionalSimInfoParam, get_optional_target, RequiredTargetParamimport servicesimport sims4.commands
@sims4.commands.Command('loot.apply_to_sim', command_type=sims4.commands.CommandType.DebugOnly)
def loot_apply_to_sim(loot_type:TunableInstanceParam(sims4.resources.Types.ACTION), opt_sim_id:OptionalSimInfoParam=None, _connection=None):
    sim_info = get_optional_target(opt_sim_id, target_type=OptionalSimInfoParam, _connection=_connection)
    if sim_info is None:
        sims4.commands.output('No sim_info specified', _connection)
        return
    resolver = SingleSimResolver(sim_info)
    loot_type.apply_to_resolver(resolver)

@sims4.commands.Command('loot.apply_to_sim_and_target', command_type=sims4.commands.CommandType.DebugOnly)
def loot_apply_to_sim_and_target(loot_type:TunableInstanceParam(sims4.resources.Types.ACTION), actor_sim:RequiredTargetParam=None, target_obj:RequiredTargetParam=None, _connection=None):
    actor = actor_sim.get_target(manager=services.sim_info_manager())
    if actor is None:
        sims4.commands.output('No actor', _connection)
        return
    target = target_obj.get_target(manager=services.object_manager())
    if target is None:
        sims4.commands.output('No target', _connection)
        return
    resolver = DoubleObjectResolver(actor, target)
    loot_type.apply_to_resolver(resolver)
