from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchemaambient_archive_schema = GsiGridSchema(label='Situations/Ambient Log')ambient_archive_schema.add_field('sources', label='Sources')ambient_archive_schema.add_field('created_situation', label='Created Situation')archiver = GameplayArchiver('ambient', ambient_archive_schema)
def archive_ambient_data(description, created_situation=''):
    entry = {}
    entry['sources'] = description
    entry['created_situation'] = created_situation
    archiver.archive(data=entry)
