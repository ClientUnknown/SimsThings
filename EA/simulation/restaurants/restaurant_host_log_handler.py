from gsi_handlers.gameplay_archiver import GameplayArchiver
def log_host_action(action, result):
    archive_data = {'action': action, 'result': result}
    host_archiver.archive(data=archive_data)
