from zone_director import ZoneDirectorBaseimport services
class ZoneDirectorVenueProxy(ZoneDirectorBase):

    def __new__(cls, *args, proxy=True, **kwargs):
        if not proxy:
            new = super().__new__
            if new is object.__new__:
                return new(cls)
            raise TypeError('super() of _ZoneDirectorVenueProxy cannot override __new__')
        venue_zone_director = services.venue_service().venue.zone_director()

        class _ZoneDirectorVenueProxy(cls, type(venue_zone_director)):

            def __init__(self, *args, proxy=None, **kwargs):
                return super().__init__(*args, **kwargs)

        return _ZoneDirectorVenueProxy(*args, proxy=False, **kwargs)

    INSTANCE_SUBCLASSES_ONLY = True
