from server_commands.argument_helpers import TunableInstanceParamimport servicesimport sims4
@sims4.commands.Command('tutorial.activate_tutorial_tip', command_type=sims4.commands.CommandType.Live)
def activate_tutorial_tip(tutorial_tip:TunableInstanceParam(sims4.resources.Types.TUTORIAL_TIP), _connection=None):
    tutorial_tip.activate()
    return True

@sims4.commands.Command('tutorial.deactivate_tutorial_tip', command_type=sims4.commands.CommandType.Live)
def deactivate_tutorial_tip(tutorial_tip:TunableInstanceParam(sims4.resources.Types.TUTORIAL_TIP), _connection=None):
    tutorial_tip.deactivate()
    return True

@sims4.commands.Command('tutorial.set_tutorial_mode', command_type=sims4.commands.CommandType.Live)
def set_tutorial_mode(mode:int=0, _connection=None):
    tutorial_service = services.get_tutorial_service()
    if tutorial_service is not None:
        tutorial_service.set_tutorial_mode(mode)
    return True
