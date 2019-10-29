from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchemaoutfit_change_archive_schema = GsiGridSchema(label='Outfit Change Archive', sim_specific=True)outfit_change_archive_schema.add_field('change_from', label='Change From')outfit_change_archive_schema.add_field('change_to', label='Change To')outfit_change_archive_schema.add_field('change_reason', label='Change Reason')archiver = GameplayArchiver('OutfitChanges', outfit_change_archive_schema, add_to_archive_enable_functions=True)
def log_outfit_change(sim_info, change_to, change_reason):
    if sim_info is None:
        return
    entry = {'change_from': repr(sim_info._current_outfit), 'change_to': repr(change_to), 'change_reason': repr(change_reason)}
    archiver.archive(data=entry, object_id=sim_info.id)
