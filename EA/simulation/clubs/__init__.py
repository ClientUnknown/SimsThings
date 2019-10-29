import services
class UnavailableClubError(Exception):
    pass

class UnavailableClubCriteriaError(Exception):
    pass

def on_sim_killed_or_culled(sim_info):
    club_service = services.get_club_service()
    if club_service is not None:
        club_service.on_sim_killed_or_culled(sim_info)
