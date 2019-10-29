from situations.complex.yoga_class import YogaClassScheduleMixinfrom venues.scheduling_zone_director import SchedulingZoneDirectorfrom venues.visitor_situation_on_arrival_zone_director_mixin import VisitorSituationOnArrivalZoneDirectorMixinimport sims4logger = sims4.log.Logger('RelaxationCenterZoneDirector')
class RelaxationCenterZoneDirector(YogaClassScheduleMixin, VisitorSituationOnArrivalZoneDirectorMixin, SchedulingZoneDirector):
    pass
