import services
class TempleUtils:

    @classmethod
    def get_temple_zone_director(cls):
        zone_director = services.venue_service().get_zone_director()
        if hasattr(zone_director, '_temple_data'):
            return zone_director
