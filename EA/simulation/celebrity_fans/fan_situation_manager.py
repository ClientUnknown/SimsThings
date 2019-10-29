from bucks.bucks_utils import BucksUtilsfrom celebrity_fans.fan_tuning import FanTuningfrom date_and_time import create_time_spanfrom event_testing.resolver import GlobalResolverfrom fame.fame_tuning import FameTunablesfrom interactions.utils.tested_variant import TunableTestedVariantfrom sims4.resources import Typesfrom sims4.tuning.tunable import HasTunableFactory, AutoFactoryInit, TunableSimMinute, TunableMapping, TunableRange, TunablePackSafeReference, TunableVariantfrom situations.bouncer.bouncer_types import BouncerRequestPriority, RequestSpawningOptionfrom situations.situation_curve import SituationCurve, ShiftlessDesiredSituationsfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfoimport alarmsimport servicesimport sims4.loglogger = sims4.log.Logger('FanSituationManager', default_owner='jdimailig')
class FanSituationManager(HasTunableFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'fan_situation_interval': TunableSimMinute(description='\n            The amount of time, in Sim minutes, between attempts to create new\n            fan/stan situations.\n            ', default=15), 'fan_count_by_fame_level': TunableMapping(description='\n            The tunable amount of fans that are allowed by fame level of\n            a celebrity on the lot.  This number determines whether or not\n            more fan situations need to be triggered.\n            ', key_type=int, value_type=int), 'fans_cap': TunableTestedVariant(description='\n            Adjustable fans cap.\n            ', tunable_type=TunableRange(description='\n                Maximum number of fans we are allowed to run within this provider.\n    \n                After this cap is hit, no other fan situations will be spawned.\n                ', tunable_type=int, default=3, minimum=0), is_noncallable_type=True), 'fan_situations': TunableVariant(description='\n            Situations to choose from when generating a fan situation.\n            ', situation_curve=SituationCurve.TunableFactory(get_create_params={'user_facing': False}), shiftless=ShiftlessDesiredSituations.TunableFactory(get_create_params={'user_facing': False}), default='shiftless'), 'stan_situation': TunablePackSafeReference(description='\n            Stan situation.  A stan situation is tied to a particular Sim\n            via a relationship bit defined in FanTuning.\n            ', manager=services.get_instance_manager(Types.SITUATION), class_restrictions='StanSituation')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        situation_manager = services.get_zone_situation_manager()
        self._fan_situation_alarm_handle = None
        self._fan_situation_ids = set()
        self._stan_situation_ids = set()
        self._celebrity_container_situation = None
        self._celebrity_container_situation_id = situation_manager.create_situation(FanTuning.FANNABLE_CELEBRITY_SITUATION, user_facing=False)
        if self._celebrity_container_situation_id is not None:
            self._celebrity_container_situation = situation_manager[self._celebrity_container_situation_id]
        else:
            logger.error('Failed to create container situation')
        self.request_situations()
        self._create_fan_creation_alarm()

    def on_destroy(self):
        if self._celebrity_container_situation is not None:
            services.get_zone_situation_manager().destroy_situation_by_id(self._celebrity_container_situation_id)
        if self._fan_situation_alarm_handle is not None:
            alarms.cancel_alarm(self._fan_situation_alarm_handle)
            self._fan_situation_alarm_handle = None

    def save_fan_situations(self, writer):
        if self._fan_situation_ids:
            writer.write_uint64s('fan_situation_ids', self._fan_situation_ids)
        if self._stan_situation_ids:
            writer.write_uint64s('stan_situation_ids', self._stan_situation_ids)

    def load_fan_situations(self, reader):
        if reader is not None:
            self._fan_situation_ids = set(reader.read_uint64s('fan_situation_ids', ()))
        if reader is not None:
            self._stan_situation_ids = set(reader.read_uint64s('stan_situation_ids', ()))

    def _remove_stale_fan_situations(self):
        current_situation_ids = set(services.get_zone_situation_manager().keys())
        self._fan_situation_ids = self._fan_situation_ids & current_situation_ids
        self._stan_situation_ids = self._stan_situation_ids & current_situation_ids

    def _create_fan_creation_alarm(self):
        self._fan_situation_alarm_handle = alarms.add_alarm(self, create_time_span(minutes=self.fan_situation_interval), self._on_fan_creation_alarm, repeating=True)

    def _on_fan_creation_alarm(self, *_, **__):
        self.request_situations()

    def request_situations(self):
        self._remove_stale_fan_situations()
        stanned_sim_ids = self._stanned_sim_ids()
        for sim in self._stannable_sims():
            if sim.sim_id in stanned_sim_ids:
                pass
            else:
                self._try_spawn_stan_situation_for_sim(sim)
        expected_fan_count = self._get_expected_number_of_fans()
        if expected_fan_count == 0:
            return
        current_fan_count = self._fan_count()
        if current_fan_count < expected_fan_count:
            self._try_spawn_random_fan_situation()

    def _try_spawn_random_fan_situation(self):
        situation_manager = services.get_zone_situation_manager()
        (situation_type, _) = self.fan_situations.get_situation_and_params()
        if situation_type is not None:
            situation_id = situation_manager.create_situation(situation_type, user_facing=False, creation_source='FanSituationManager: Fan Situation')
            self._fan_situation_ids.add(situation_id)

    def _try_spawn_stan_situation_for_sim(self, stanned_sim):
        if self.stan_situation is None:
            return
        stan_results = services.sim_filter_service().submit_matching_filter(sim_filter=FanTuning.STAN_FILTER, number_of_sims_to_find=1, requesting_sim_info=stanned_sim.sim_info, allow_instanced_sims=True, allow_yielding=False, gsi_source_fn=lambda : 'FanSituationManager: Stan for {}'.format(str(stanned_sim)))
        if not stan_results:
            logger.warn('Could not create/find a stan for {}', str(stanned_sim))
            return
        stan_sim_info = stan_results[0].sim_info
        stan_id = stan_sim_info.sim_id
        in_stan_home_zone = stan_sim_info.household.home_zone_id == services.current_zone_id()
        if in_stan_home_zone or FanTuning.STAN_DISABLING_BITS & set(services.relationship_service().get_all_bits(stan_id, target_sim_id=stanned_sim.sim_id)):
            return
        duration_override = 0 if in_stan_home_zone else None
        situation_manager = services.get_zone_situation_manager()
        guest_list = SituationGuestList(invite_only=True, host_sim_id=stanned_sim.sim_id)
        guest_list.add_guest_info(SituationGuestInfo(stan_id, self.stan_situation.fan_job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.EVENT_VIP))
        situation_id = situation_manager.create_situation(self.stan_situation, guest_list=guest_list, user_facing=False, duration_override=duration_override, creation_source='FanSituationManager: Stan Situation targetting {}'.format(str(stanned_sim)))
        if situation_id is None:
            logger.error('Unable to create Stan situation')
            return
        self._stan_situation_ids.add(situation_id)

    def _get_expected_number_of_fans(self):
        if self._celebrity_container_situation is None:
            return 0
        fans_cap = self.fans_cap(resolver=GlobalResolver())
        if fans_cap <= 0:
            return 0
        expected_fans = 0
        for sim in self._celebrity_container_situation.all_sims_in_situation_gen():
            expected_fans += self._get_num_fans_for_fame_level(self._get_fame_level(sim))
            if expected_fans >= fans_cap:
                break
        return min(expected_fans, fans_cap)

    def _get_fame_level(self, sim):
        statistic = sim.get_statistic(FameTunables.FAME_RANKED_STATISTIC)
        if statistic is None:
            logger.error('{} does not have a the fame statistic', sim)
            return 0
        return statistic.rank_level

    def _get_num_fans_for_fame_level(self, fame_level):
        fans_for_fame = 0
        while fame_level > 0:
            if fame_level in self.fan_count_by_fame_level:
                fans_for_fame = self.fan_count_by_fame_level[fame_level]
                break
            fame_level -= 1
        return fans_for_fame

    def _fan_count(self):
        situation_manager = services.get_zone_situation_manager()
        fan_sim_ids = set()
        for situation in situation_manager.get_situations_by_tags(set((FanTuning.FAN_SITUATION_TAG,))):
            fan_sim_ids.update(sim.sim_id for sim in situation.all_sims_in_situation_gen())
        return len(fan_sim_ids)

    def _sim_is_stannable(self, sim):
        bucks_tracker = BucksUtils.get_tracker_for_bucks_type(FanTuning.STAN_PERK.associated_bucks_type, owner_id=sim.sim_id)
        if bucks_tracker is None:
            return False
        return bucks_tracker.is_perk_unlocked(FanTuning.STAN_PERK)

    def _stannable_sims(self):
        if FanTuning.STAN_PERK is None:
            return ()
        active_household = services.active_household()
        if active_household is None:
            return ()
        return tuple(sim for sim in active_household.instanced_sims_gen() if self._sim_is_stannable(sim))

    def _fannable_sims(self):
        if self._celebrity_container_situation is None:
            return ()
        return tuple(self._celebrity_container_situation.all_sims_in_situation_gen())

    def _stanned_sim_ids(self):
        situation_manager = services.get_zone_situation_manager()
        stanned_sim_ids = set()
        for situation_id in self._stan_situation_ids:
            situation = situation_manager.get(situation_id)
            if situation is None:
                logger.error('Could not find situation with id {}', situation_id)
            else:
                stanned_sim_info = situation.initiating_sim_info
                if stanned_sim_info is None:
                    logger.error('Stanned SimInfo missing in situation {}', situation)
                else:
                    stanned_sim_ids.add(stanned_sim_info.sim_id)
        return stanned_sim_ids
