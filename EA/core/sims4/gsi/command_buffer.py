import collectionstry:
    import threading
    _threading_enabled = True
except ImportError:
    import dummy_threading as threading
    _threading_enabled = Falseimport sims4.commandsimport sims4.logimport sims4.service_managerlogger = sims4.log.Logger('GSI')_Command = collections.namedtuple('_Command', ('command_string', 'callback', 'output_override', 'zone_id', 'connection_id'))
def _execute_command(command):
    real_output = sims4.commands.output
    sims4.commands.output = command.output_override
    result = False
    try:
        if command.zone_id is not None:
            sims4.commands.execute(command.command_string, command.connection_id)
        else:
            sims4.commands.execute(command.command_string, None)
        result = True
    except Exception:
        result = False
        logger.exception('Error while executing game command for')
    finally:
        sims4.commands.output = real_output
        command.callback(result)
if _threading_enabled:

    class CommandBufferService(sims4.service_manager.Service):

        def __init__(self):
            self.pending_commands = None
            self._lock = threading.Lock()

        def start(self):
            with self._lock:
                self.pending_commands = []

        def stop(self):
            with self._lock:
                self.pending_commands = None

        def add_command(self, command_string, callback=None, output_override=None, zone_id=None, connection_id=None):
            with self._lock:
                if self.pending_commands is not None:
                    command = _Command(command_string, callback, output_override, zone_id, connection_id)
                    self.pending_commands.append(command)

        def on_tick(self):
            with self._lock:
                if not self.pending_commands:
                    return
                local_pending_commands = list(self.pending_commands)
                del self.pending_commands[:]
            for command in local_pending_commands:
                _execute_command(command)

else:

    class CommandBufferService(sims4.service_manager.Service):

        def add_command(self, command_string, callback=None, output_override=None, zone_id=None, connection_id=None):
            command = _Command(command_string, callback, output_override, zone_id, connection_id)
            _execute_command(command)

        def on_tick(self):
            pass
