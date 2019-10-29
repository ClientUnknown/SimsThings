from clock import ClockSpeedModefrom sims4.tuning.instances import HashedTunedInstanceMetaclassfrom sims4.tuning.tunable import HasTunableReferencefrom situations.situation_curve import SituationCurvefrom venues.scheduling_zone_director import SchedulingZoneDirectorMixinimport servicesimport sims4.loglogger = sims4.log.Logger('WalkbyTuning')
class WalkbyTuning(HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.walk_by_manager()):
    INSTANCE_TUNABLES = {'walkby_desire_by_day_of_week': SituationCurve.TunableFactory(description='\n            The desire that walk-by Sims are spawned at specific times of the\n            day.\n            ', get_create_params={'user_facing': False})}

    @classmethod
    def get_desired_sim_count(cls):
        return cls.walkby_desire_by_day_of_week.get_desired_sim_count()

    @classmethod
    def get_ambient_walkby_situation(cls, sim_slots_available):
        lot_id = services.active_lot_id()

        def can_start_situation(situation):
            if services.game_clock_service().clock_speed == ClockSpeedMode.SUPER_SPEED3 and not situation.allowed_in_super_speed_3:
                return False
            return situation.can_start_walkby(lot_id, sim_slots_available)

        household = services.active_household()
        additional_walkbys = []
        if household is not None:
            additional_walkbys.extend(household.holiday_tracker.get_additional_holiday_walkbys(predicate=can_start_situation))
        return cls.walkby_desire_by_day_of_week.get_situation_and_params(predicate=can_start_situation, additional_situations=additional_walkbys)[0]

class SchedulingWalkbyBase:

    def on_startup(self):
        pass

    def on_shutdown(self):
        pass

    def create_situations_during_zone_spin_up(self):
        pass

    def _save_custom_zone_director(self, zone_director_proto, writer):
        pass

    def _load_custom_zone_director(self, zone_director_proto, reader):
        pass

class SchedulingWalkbyDirector(SchedulingZoneDirectorMixin, SchedulingWalkbyBase, HasTunableReference, metaclass=HashedTunedInstanceMetaclass, manager=services.get_instance_manager(sims4.resources.Types.WALK_BY)):

    def _prune_stale_situations(self, situation_ids):
        situation_manager = services.get_zone_situation_manager()
        return [situation_id for situation_id in situation_ids if situation_id in situation_manager]
