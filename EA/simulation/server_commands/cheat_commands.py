from sims4.commands import get_command_info_genimport pathsimport servicesimport sims4.commandsimport ui.ui_dialog
class CheatDialogTuning:
    CONFIRM_CHEAT_DIALOG = ui.ui_dialog.UiDialogOkCancel.TunableFactory(description='\n         This dialog asks the player to confirm whether they want to enable cheats.\n         ')

@sims4.commands.Command('testingcheats', command_type=sims4.commands.CommandType.Live)
def testing_cheats(enable:bool=False, _connection=None):
    if paths.IS_DESKTOP:
        _testing_cheats_common(enable=enable, _connection=_connection)
    else:
        cheat_service = services.get_cheat_service()
        if cheat_service.cheats_ever_enabled or not enable:
            _testing_cheats_common(enable=enable, _connection=_connection)
        else:

            def _on_confirm_cheat_decision(_dialog):
                if _dialog.accepted:
                    _testing_cheats_common(enable=enable, _connection=_connection)

            dialog = CheatDialogTuning.CONFIRM_CHEAT_DIALOG(None)
            dialog.show_dialog(on_response=_on_confirm_cheat_decision)

@sims4.commands.Command('AutomationTestingCheats', command_type=sims4.commands.CommandType.Live)
def automation_testing_cheats(enable:bool=False, _connection=None):
    _testing_cheats_common(enable=enable, _connection=_connection)

@sims4.commands.Command('cheat.override_enabled', command_type=sims4.commands.CommandType.DebugOnly)
def override_enabled(enable:bool=False, _connection=None):
    cheat_service = services.get_cheat_service()
    cheat_service.cheats_enabled = enable
    _send_to_client(_connection)
    return True

@sims4.commands.Command('cheat.override_ever_enabled', command_type=sims4.commands.CommandType.DebugOnly)
def override_ever_enabled(enable:bool=False, _connection=None):
    cheat_service = services.get_cheat_service()
    cheat_service.cheats_ever_enabled = enable
    _send_to_client(_connection)
    return True

@sims4.commands.Command('cheat.status', command_type=sims4.commands.CommandType.Live)
def display_cheat_status(enable:bool=False, _connection=None):
    cheat_service = services.get_cheat_service()
    output = sims4.commands.CheatOutput(_connection)
    if cheat_service.cheats_enabled:
        if cheat_service.cheats_ever_enabled:
            output('Cheats are enabled.')
        else:
            output('Cheats are enabled (but were never enabled!)')
    elif cheat_service.cheats_ever_enabled:
        output('Cheats disabled, but were enabled.')
    else:
        output('Cheats never enabled.')
    return True

@sims4.commands.Command('cheat.list')
def display_cheat_list(_connection=None):
    output = sims4.commands.Output(_connection)
    for (command_name, command_type, command_restriction) in get_command_info_gen():
        output('{}, {}, {}'.format(command_name, command_type.name, command_restriction.name))
    return True

def _testing_cheats_common(enable:bool=False, _connection=None):
    output = sims4.commands.CheatOutput(_connection)
    cheat_service = services.get_cheat_service()
    if enable:
        cheat_service.enable_cheats()
        output('Cheats are enabled.')
    else:
        cheat_service.disable_cheats()
        output('Cheats are disabled.')
    _send_to_client(_connection)
    return True

def _send_to_client(_connection):
    client = services.client_manager().get(_connection)
    cheat_service = services.get_cheat_service()
    cheat_service.send_to_client(client)
