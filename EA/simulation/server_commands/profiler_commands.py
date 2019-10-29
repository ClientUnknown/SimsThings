from sims4.commands import CommandTypeimport sims4.commandsimport sims4.profiler
@sims4.commands.Command('pyprofile.on', command_type=CommandType.Automation)
def pyprofile_on(_connection=None):
    sims4.profiler.enable_profiler()
    return True

@sims4.commands.Command('pyprofile.off', command_type=CommandType.Automation)
def pyprofile_off(_connection=None):
    sims4.profiler.disable_profiler()
    sims4.profiler.flush()
    return True

@sims4.commands.Command('pyprofile.flush', command_type=CommandType.Automation)
def pyprofile_flush(_connection=None):
    sims4.profiler.flush()
    return True
