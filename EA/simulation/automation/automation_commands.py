from automation import automation_utilsimport sims4.commands
@sims4.commands.Command('qa.automation.enable_events', command_type=sims4.commands.CommandType.Automation)
def automation_events(enabled:bool=True, _connection=None):
    automation_utils.dispatch_automation_events = enabled
