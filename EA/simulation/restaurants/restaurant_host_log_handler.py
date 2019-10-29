from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchemaimport servicesimport sims4.loglogger = sims4.log.Logger('GSI')restaurant_host_schema = GsiGridSchema(label='Restaurant Host Log')restaurant_host_schema.add_field('game_time', label='Game Time', width=2)restaurant_host_schema.add_field('action', label='Action', width=2)restaurant_host_schema.add_field('result', label='Result', width=2)host_archiver = GameplayArchiver('hostActions', restaurant_host_schema, add_to_archive_enable_functions=True)
def log_host_action(action, result):
    archive_data = {'action': action, 'result': result}
    host_archiver.archive(data=archive_data)
