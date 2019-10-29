import server_commands.argument_helpersimport servicesimport sims4.commandsfrom server_commands.argument_helpers import TunableInstanceParamlogger = sims4.log.Logger('Rewards')
@sims4.commands.Command('rewards.give_reward')
def give_reward(reward_type:TunableInstanceParam(sims4.resources.Types.REWARD), opt_sim:server_commands.argument_helpers.OptionalTargetParam=None, _connection=None):
    output = sims4.commands.Output(_connection)
    sim = server_commands.argument_helpers.get_optional_target(opt_sim, _connection)
    reward_type.give_reward(sim.sim_info)
    output('Successfully gave the reward.')
