from gsi_handlers.gameplay_archiver import GameplayArchiver
def is_archive_enabled():
    return archiver.enabled

def archive_club_bucks_reward(club_id, amount, reason):
    archive_data = {'club_id': club_id, 'amount': amount, 'reason': reason}
    archiver.archive(archive_data)
