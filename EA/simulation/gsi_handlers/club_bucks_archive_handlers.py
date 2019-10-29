from gsi_handlers.gameplay_archiver import GameplayArchiverfrom sims4.gsi.schema import GsiGridSchemaclub_bucks_archive_schema = GsiGridSchema(label='Club Bucks Archive', sim_specific=False)club_bucks_archive_schema.add_field('club_id', label='Club ID', hidden=False)club_bucks_archive_schema.add_field('amount', label='Amount', hidden=False)club_bucks_archive_schema.add_field('reason', label='Reason', hidden=False)archiver = GameplayArchiver('club_bucks_archive', club_bucks_archive_schema, add_to_archive_enable_functions=True)
def is_archive_enabled():
    return archiver.enabled

def archive_club_bucks_reward(club_id, amount, reason):
    archive_data = {'club_id': club_id, 'amount': amount, 'reason': reason}
    archiver.archive(archive_data)
