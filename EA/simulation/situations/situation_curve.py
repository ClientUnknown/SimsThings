import operatorfrom event_testing.resolver import GlobalResolverfrom event_testing.tests import TunableTestSetfrom scheduler import TunableDayAvailabilityfrom sims4 import randomfrom sims4.tuning.tunable import AutoFactoryInit, HasTunableSingletonFactory, TunableList, TunableTuple, TunableMapping, Tunable, TunableLiteralOrRandomValue, TunedIntervalLiteral, TunableFactory, TunedIntervalfrom situations.situation import Situationfrom tunable_multiplier import TunableMultiplierfrom tunable_time import Daysimport date_and_timeimport servicesimport sims4.loglogger = sims4.log.Logger('Situations')
class _DesiredSituations(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {'desired_sim_count': TunableLiteralOrRandomValue(description='\n            The number of Sims desired to be participating in the situation.\n            ', tunable_type=int, default=0), 'disable_churn': Tunable(description="\n            If checked, we disable churn for this shift change. That means we\n            only fire the situation on shift change, not in between shifts. So\n            if you have a situation in this shift and it ends, we don't spin up\n            another one on the next churn (based on churn interval). Basically\n            means you want a one shot situation, fire and forget.\n            \n            If unchecked, we will try to maintain the desired number of\n            situations at every churn interval during this shift change.\n            ", tunable_type=bool, default=False)}

    @TunableFactory.factory_option
    def get_create_params(user_facing=False):
        create_params = {}
        create_params_locked = {}
        if user_facing:
            create_params['user_facing'] = Tunable(description="\n                                                   If enabled, we will start the situation as user facing.\n                                                   Note: We can only have one user facing situation at a time,\n                                                   so make sure you aren't tuning multiple user facing\n                                                   situations to occur at once.\n                                                   ", tunable_type=bool, default=False)
        else:
            create_params_locked['user_facing'] = False
        return {'weighted_situations': TunableList(description='\n            A weighted list of situations to be used while fulfilling the\n            desired Sim count.\n            ', tunable=TunableTuple(situation=Situation.TunableReference(pack_safe=True), params=TunableTuple(description='\n                    Situation creation parameters.\n                    ', locked_args=create_params_locked, **create_params), weight=Tunable(tunable_type=int, default=1), weight_multipliers=TunableMultiplier.TunableFactory(description="\n                    Tunable tested multiplier to apply to weight.\n                    \n                    *IMPORTANT* The only participants that work are ones\n                    available globally, such as Lot and ActiveHousehold. Only\n                    use these participant types or use tests that don't rely\n                    on any, such as testing all objects via Object Criteria\n                    test or testing active zone with the Zone test.\n                    ", locked_args={'base_value': 1}), tests=TunableTestSet(description="\n                    A set of tests that must pass for the situation and weight\n                    pair to be available for selection.\n                    \n                    *IMPORTANT* The only participants that work are ones\n                    available globally, such as Lot and ActiveHousehold. Only\n                    use these participant types or use tests that don't rely\n                    on any, such as testing all objects via Object Criteria\n                    test or testing active zone with the Zone test.\n                    ")))}

    def get_weighted_situations(self, predicate=lambda _: True):
        resolver = GlobalResolver()

        def get_weight(item):
            if not predicate(item.situation):
                return 0
            if not item.tests.run_tests(resolver):
                return 0
            return item.weight*item.weight_multipliers.get_multiplier(resolver)*item.situation.weight_multipliers.get_multiplier(resolver)

        weighted_situations = tuple((get_weight(item), (item.situation, dict(item.params.items()))) for item in self.weighted_situations)
        return weighted_situations

    def get_situation_and_params(self, predicate=lambda _: True, additional_situations=None):
        weighted_situations = self.get_weighted_situations(predicate=predicate)
        if additional_situations is not None:
            weighted_situations = tuple(weighted_situations) + tuple(additional_situations)
        situation_and_params = random.weighted_random_item(weighted_situations)
        if situation_and_params is not None:
            return situation_and_params
        return (None, {})

class SituationCurve(HasTunableSingletonFactory, AutoFactoryInit):

    @staticmethod
    def _verify_tunable_callback(instance_class, tunable_name, source, value, **kwargs):
        keys = set()
        for item in value.entries:
            days = item.days_of_the_week
            for (day, enabled) in days.items():
                if enabled:
                    if day in keys:
                        logger.error('WalkbyTuning {} has multiple population curves for the day {}.', source, day, owner='manus')
                    else:
                        keys.add(day)
            if item.walkby_desire_by_time_of_day:
                for hour in item.walkby_desire_by_time_of_day.keys():
                    if not hour < 0:
                        if hour > 24:
                            logger.error('Situation Curve in {} has in invalid hour of the day {}. Range: [0, 24].', source, hour, owner='manus')
                    logger.error('Situation Curve in {} has in invalid hour of the day {}. Range: [0, 24].', source, hour, owner='manus')
            else:
                logger.error("Situation Curve in {}'s days {} has no walkby desire population curve.", source, days, owner='manus')

    FACTORY_TUNABLES = {'verify_tunable_callback': _verify_tunable_callback}

    @TunableFactory.factory_option
    def get_create_params(**kwargs):
        return {'entries': TunableList(description='\n                A list of tuples declaring a relationship between days of the week\n                and desire curves.\n                ', tunable=TunableTuple(description='\n                    The first value is the day of the week that maps to a desired\n                    curve of population by time of the day.\n                    \n                    days_of_the_week    population_desire_by_time_of_day\n                        M,Th,F                time_curve_1\n                        W,Sa                  time_curve_2\n                        \n                    By production/design request we do not support multiple\n                    population curves for the same day. e.g. if you want something\n                    special to occur at noon on a Wednesday, make a unique curve for\n                    Wednesday and apply the changes to it.\n                    ', days_of_the_week=TunableDayAvailability(), walkby_desire_by_time_of_day=TunableMapping(description='\n                        Each entry in the map has two columns. The first column is\n                        the hour of the day (0-24) that maps to a desired list of\n                        population (second column).\n                        \n                        The entry with starting hour that is closest to, but before\n                        the current hour will be chosen.\n                        \n                        Given this tuning: \n                            hour_of_day           desired_situations\n                            6                     [(w1, s1), (w2, s2)]\n                            10                    [(w1, s2)]\n                            14                    [(w2, s5)]\n                            20                    [(w9, s0)]\n                            \n                        if the current hour is 11, hour_of_day will be 10 and desired is [(w1, s2)].\n                        if the current hour is 19, hour_of_day will be 14 and desired is [(w2, s5)].\n                        if the current hour is 23, hour_of_day will be 20 and desired is [(w9, s0)].\n                        if the current hour is 2, hour_of_day will be 20 and desired is [(w9, s0)]. (uses 20 tuning because it is not 6 yet)\n                        \n                        The entries will be automatically sorted by time.\n                        ', key_name='hour_of_day', key_type=Tunable(tunable_type=int, default=0), value_name='desired_walkby_situations', value_type=_DesiredSituations.TunableFactory(get_create_params=kwargs)))), 'desired_sim_count_multipliers': TunableMultiplier.TunableFactory(description='\n                Tunable tested multiplier to apply to the desired sim count.\n                ', locked_args={'base_value': 1})}

    def _get_sorted_situation_schedule(self, day):
        situation_schedule = []
        for item in self.entries:
            enabled = item.days_of_the_week.get(day, None)
            if enabled:
                for (beginning_hour, situations) in item.walkby_desire_by_time_of_day.items():
                    situation_schedule.append((beginning_hour, situations))
        situation_schedule.sort(key=operator.itemgetter(0))
        return situation_schedule

    def _get_desired_situations(self):
        if not self.entries:
            return
        time_of_day = services.time_service().sim_now
        hour_of_day = time_of_day.hour()
        day = time_of_day.day()
        situation_schedule = self._get_sorted_situation_schedule(day)
        if not situation_schedule:
            return
        entry = situation_schedule[-1]
        desire = entry[1]
        for entry in situation_schedule:
            if entry[0] <= hour_of_day:
                desire = entry[1]
            else:
                break
        return desire

    @property
    def is_shift_churn_disabled(self):
        desire = self._get_desired_situations()
        if desire is None:
            return False
        return desire.disable_churn

    def get_desired_sim_count(self):
        desire = self._get_desired_situations()
        if desire is None:
            return TunedIntervalLiteral(0)
        resolver = GlobalResolver()
        sim_count_multiplier = self.desired_sim_count_multipliers.get_multiplier(resolver)
        lower_bound = round(desire.desired_sim_count.lower_bound*sim_count_multiplier)
        upper_bound = round(desire.desired_sim_count.upper_bound*sim_count_multiplier)
        return TunedInterval(lower_bound, upper_bound)

    def get_timespan_to_next_shift_time(self, time_of_day):
        if not self.entries:
            return
        days_to_schedule_ahead = 1
        current_day = time_of_day.day()
        next_day = (current_day + days_to_schedule_ahead) % 7
        next_day_sorted_times = self._get_sorted_situation_schedule(next_day)
        if next_day_sorted_times:
            next_shift_hour = next_day_sorted_times[0][0]
        else:
            next_shift_hour = 0
        now = services.time_service().sim_now
        sorted_times = self._get_sorted_situation_schedule(current_day)
        scheduled_day = int(now.absolute_days())
        now_hour = now.hour()
        for (shift_hour, _) in sorted_times:
            if shift_hour > now_hour:
                next_shift_hour = shift_hour
                break
        scheduled_day += 1
        future = date_and_time.create_date_and_time(days=scheduled_day, hours=next_shift_hour)
        time_span_until = future - now
        return time_span_until

    def get_weighted_situations(self, predicate=lambda _: True):
        desire = self._get_desired_situations()
        if desire is None:
            return
        weighted_situations = desire.get_weighted_situations(predicate=predicate)
        return weighted_situations

    def get_situation_and_params(self, predicate=lambda _: True, additional_situations=None):
        desire = self._get_desired_situations()
        if desire is None:
            return
        situation_and_params = desire.get_situation_and_params(predicate=predicate, additional_situations=additional_situations)
        return situation_and_params

    def debug_output_schedule(self, output):
        for entry in self.entries:
            output('Days:' + ', '.join(day.name for day in Days if entry.days_of_the_week[day]))
            situation_schedule = list((hour, desire) for (hour, desire) in entry.walkby_desire_by_time_of_day.items())
            situation_schedule.sort(key=operator.itemgetter(0))
            for (hour, desire) in situation_schedule:
                output('  Hour: {}'.format(hour))
                for (weight, situation_and_params) in desire.get_weighted_situations():
                    output('    {}: {}'.format(situation_and_params[0].__name__, weight))

class ShiftlessDesiredSituations(HasTunableSingletonFactory, AutoFactoryInit):
    FACTORY_TUNABLES = {}

    @TunableFactory.factory_option
    def get_create_params(**kwargs):
        return {'_desired_siutations': _DesiredSituations.TunableFactory(get_create_params=kwargs), 'desired_sim_count_multipliers': TunableMultiplier.TunableFactory(description='\n                Tunable tested multiplier to apply to the desired sim count.\n                ', locked_args={'base_value': 1})}

    @property
    def is_shift_churn_disabled(self):
        desire = self._desired_siutations
        if desire is None:
            return False
        return desire.disable_churn

    def get_desired_sim_count(self):
        desire = self._desired_siutations
        if desire is None:
            return TunedIntervalLiteral(0)
        resolver = GlobalResolver()
        sim_count_multiplier = self.desired_sim_count_multipliers.get_multiplier(resolver)
        lower_bound = round(desire.desired_sim_count.lower_bound*sim_count_multiplier)
        upper_bound = round(desire.desired_sim_count.upper_bound*sim_count_multiplier)
        return TunedInterval(lower_bound, upper_bound)

    def get_timespan_to_next_shift_time(self, time_of_day):
        pass

    def get_situation_and_params(self, predicate=lambda _: True, additional_situations=None):
        situation_and_params = self._desired_siutations.get_situation_and_params(predicate=predicate, additional_situations=additional_situations)
        return situation_and_params

    def debug_output_schedule(self, output):
        output('Shiftless')
        for (weight, situation_and_params) in self._desired_siutations.get_weighted_situations():
            output('  {}: {}'.format(situation_and_params[0].__name__, weight))
