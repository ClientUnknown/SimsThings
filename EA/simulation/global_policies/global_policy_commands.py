from server_commands.argument_helpers import TunableInstanceParamimport servicesimport sims4
@sims4.commands.Command('global_policy.set_progress', command_type=sims4.commands.CommandType.Automation)
def set_global_policy_progress(policy:TunableInstanceParam(sims4.resources.Types.SNIPPET), progress_amount:int, _connection=None):
    services.global_policy_service().add_global_policy_progress(policy, progress_amount)
