from sims4.commands import CommandTypeimport pathsimport servicesimport sims4.commands
def is_command_available(command_type:CommandType):
    if command_type >= CommandType.Live:
        return True
    cheat_service = services.get_cheat_service()
    cheats_enabled = cheat_service.cheats_enabled
    if command_type >= CommandType.Cheat and cheats_enabled:
        return True
    elif command_type >= CommandType.Automation and paths.AUTOMATION_MODE:
        return True
    return False
sims4.commands.is_command_available = is_command_available