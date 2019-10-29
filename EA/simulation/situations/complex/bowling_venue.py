import itertoolsimport operatorfrom event_testing.test_events import TestEventfrom objects.components.object_relationship_component import ObjectRelationshipComponentfrom scheduler import TunableDayAvailabilityfrom sims4.random import weighted_random_itemfrom sims4.tuning.instances import lock_instance_tunablesfrom sims4.tuning.tunable import TunableTuple, TunableList, TunableThreshold, Tunable, TunableReference, TunableRange, TunableMappingfrom sims4.tuning.tunable_base import GroupNamesfrom situations.bouncer.bouncer_types import BouncerExclusivityCategory, RequestSpawningOption, BouncerRequestPriorityfrom situations.situation import Situationfrom situations.situation_complex import SituationComplexCommon, SituationState, SituationStateData, TunableSituationJobAndRoleStatefrom situations.situation_curve import SituationCurvefrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom situations.situation_types import SituationCreationUIOptionfrom tag import TunableTagsimport alarmsimport date_and_timeimport filtersimport servicesimport sims4logger = sims4.log.Logger('BowlingVenue', default_owner='mkartika')BOWLING_LANE_TOKEN = 'bowling_lane_id'
class _BowlingState(SituationState):
    pass

class BowlingVenueSituation(SituationComplexCommon):
    INSTANCE_TUNABLES = {'group_filter': TunableReference(description='\n            The aggregate filter that we use to find the sims for this\n            situation.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SIM_FILTER), class_restrictions=filters.tunable.TunableAggregateFilter, tuning_group=GroupNames.SITUATION), 'bowling_venue_job_and_role': TunableSituationJobAndRoleState(description='\n            The job and role state for the bowler on venue.\n            ', tuning_group=GroupNames.SITUATION), 'required_bowling_lanes': TunableThreshold(description='\n            The number of bowling lane objects that needed to trigger this situation.\n            ', value=Tunable(description='\n                The value of a threshold.\n                ', tunable_type=int, default=1), default=sims4.math.Threshold(value=1, comparison=sims4.math.Operator.GREATER_OR_EQUAL.function), tuning_group=GroupNames.SITUATION)}
    REMOVE_INSTANCE_TUNABLES = Situation.NON_USER_FACING_REMOVE_INSTANCE_TUNABLES

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bowling_lane = None
        self._bowling_lane_chosen = False
        self._registered_test_events = set()
        self._load_bowling_lane()

    @classmethod
    def _states(cls):
        return (SituationStateData(1, _BowlingState),)

    @classmethod
    def _get_tuned_job_and_default_role_state_tuples(cls):
        return [(cls.bowling_venue_job_and_role.job, cls.bowling_venue_job_and_role.role_state)]

    @classmethod
    def default_job(cls):
        pass

    @classmethod
    def get_predefined_guest_list(cls):
        guest_list = SituationGuestList(invite_only=True)
        situation_manager = services.get_zone_situation_manager()
        worker_filter = cls.group_filter if cls.group_filter is not None else cls.bowling_venue_job_and_role.job.filter
        instanced_sim_ids = [sim.sim_info.id for sim in services.sim_info_manager().instanced_sims_gen()]
        household_sim_ids = [sim_info.id for sim_info in services.active_household().sim_info_gen()]
        auto_fill_blacklist = situation_manager.get_auto_fill_blacklist(sim_job=cls.bowling_venue_job_and_role.job)
        situation_sims = set()
        for situation in situation_manager.get_situations_by_tags(cls.tags):
            situation_sims.update(situation.invited_sim_ids)
        blacklist_sim_ids = set(itertools.chain(situation_sims, instanced_sim_ids, household_sim_ids, auto_fill_blacklist))
        filter_results = services.sim_filter_service().submit_matching_filter(sim_filter=worker_filter, allow_yielding=False, blacklist_sim_ids=blacklist_sim_ids, gsi_source_fn=cls.get_sim_filter_gsi_name)
        if not filter_results:
            logger.debug('Could not find any Sims for situation {}', self)
            return
        for result in filter_results:
            guest_list.add_guest_info(SituationGuestInfo(result.sim_info.sim_id, cls.bowling_venue_job_and_role.job, RequestSpawningOption.DONT_CARE, BouncerRequestPriority.BACKGROUND_MEDIUM))
        return guest_list

    @classmethod
    def situation_meets_starting_requirements(cls, total_bowling_lanes=None, **kwargs):
        if total_bowling_lanes is None:
            total_bowling_lanes = services.venue_service().get_zone_director().get_total_bowling_lanes()
        if cls.required_bowling_lanes.compare(total_bowling_lanes):
            return True
        return False

    def _register_test_event(self, test_event):
        if test_event in self._registered_test_events:
            return
        self._registered_test_events.add(test_event)
        services.get_event_manager().register_single_event(self, test_event)

    def _test_event_unregister(self, test_event):
        if test_event in self._registered_test_events:
            self._registered_test_events.remove(test_event)
            services.get_event_manager().unregister_single_event(self, test_event)

    def handle_event(self, sim_info, event, resolver):
        super().handle_event(sim_info, event, resolver)
        if event == TestEvent.ObjectDestroyed:
            destroyed_obj = resolver.get_resolved_arg('obj')
            if self._bowling_lane_chosen and destroyed_obj.id == self._bowling_lane.id:
                self._bowling_lane = None
                self._self_destruct()

    def on_remove(self):
        self._test_event_unregister(TestEvent.ObjectDestroyed)
        zone_director = services.venue_service().get_zone_director()
        remove_situation_bowling_lane = getattr(zone_director, 'remove_situation_bowling_lane', None)
        if remove_situation_bowling_lane:
            remove_situation_bowling_lane(self.id)
        super().on_remove()

    def _on_remove_sim_from_situation(self, sim):
        super()._on_remove_sim_from_situation(sim)
        if self._bowling_lane is not None:
            if self._bowling_lane.objectrelationship_component is None:
                logger.warn('Trying to remove object relationship from {} that does not have object relationship component', self._bowling_lane)
                return
            self._bowling_lane.objectrelationship_component.remove_relationship(sim.id)

    def _save_custom_situation(self, writer):
        super()._save_custom_situation(writer)
        if self._bowling_lane is not None:
            writer.write_uint64(BOWLING_LANE_TOKEN, self._bowling_lane.id)

    def _load_bowling_lane(self):
        reader = self._seed.custom_init_params_reader
        if reader is None:
            return
        bowling_lane_id = reader.read_uint64(BOWLING_LANE_TOKEN, None)
        if bowling_lane_id is None:
            logger.error('Failed to find bowling lane id from {} reader.', self)
            return
        self._bowling_lane = services.object_manager().get(bowling_lane_id)
        if self._bowling_lane is None:
            logger.error('Failed to find bowling lane id {} from object manager.', bowling_lane_id)
            return
        self._bowling_lane_chosen = True
        services.venue_service().get_zone_director().set_situation_bowling_lane(self.id, self._bowling_lane)

    def start_situation(self):
        super().start_situation()
        self._register_test_event(TestEvent.ObjectDestroyed)
        self._change_state(_BowlingState())

    def _on_set_sim_job(self, sim, job):
        super()._on_set_sim_job(sim, job)
        if self._bowling_lane is None:
            self._bowling_lane = services.venue_service().get_zone_director().get_situation_bowling_lane(self.id)
            if self._bowling_lane is None:
                logger.error('Failed to add bowling lane object relationship to Sims because bowling lane is None.')
                return
            self._bowling_lane_chosen = True
        ObjectRelationshipComponent.setup_relationship(sim, self._bowling_lane)
lock_instance_tunables(BowlingVenueSituation, exclusivity=BouncerExclusivityCategory.NORMAL, creation_ui_option=SituationCreationUIOption.NOT_AVAILABLE)
class BowlingVenueMixin:
    BOWLING_LANE_OBJECT_TAGS = TunableTags(description='\n        Tags that considered bowling lane objects.\n        ', filter_prefixes=('func',))
    MAX_SIMS_ON_VENUE = TunableRange(description='\n        The maximum number of the Sims can be spawned in all bowling situations\n        combined in the venue.\n        ', tunable_type=int, default=4, minimum=1)
    MOONLIGHT_AFFORDANCES = TunableTuple(description='\n        Super affordances to set moonlight bowling lane when they are turned\n        on and turned off.\n        ', moonlight_on=TunableReference(description='\n            A super affordance when the moonlight is turned on.\n            ', manager=services.affordance_manager(), class_restrictions=('SwitchLightAndStateImmediateInteraction',), pack_safe=True), moonlight_off=TunableReference(description='\n            A super affordance when the moonlight is turned off.\n            ', manager=services.affordance_manager(), class_restrictions=('SwitchLightAndStateImmediateInteraction',), pack_safe=True))
    INSTANCE_TUNABLES = {'bowling_venue': TunableTuple(description='\n            Holds data associated with bowling venue situations.\n            ', situation_alarm_interval=TunableRange(description='\n                Interval in sim minutes to trigger bowling situation.\n                ', tunable_type=int, minimum=1, default=60), bowling_situations_schedule=SituationCurve.TunableFactory(description='\n                Bowling situations that are created depending on what time of \n                the day it is.\n                ', get_create_params={'user_facing': False}), moonlight_on_off_schedule=TunableList(description='\n                A list of tuples declaring a schedule to turn on/off moonlight bowling lane.\n                ', tunable=TunableTuple(description='\n                    The first value is the day of the week that maps to a desired\n                    on/off time for moonlight bowling by the time of the day.\n                    \n                    days_of_the_week    on_off_moonlight_by_time_of_day\n                        M,Th,F                    schedule_1\n                        W,Sa                      schedule_2\n                    ', days_of_the_week=TunableDayAvailability(), moonlight_on_off_desire_by_time_of_day=TunableMapping(description='\n                        Each entry in the map has two columns.\n                        The first column is the hour of the day (0-24)\n                        that maps to is_moonlight_on.\n                        \n                        The entry with starting hour that is closest to, but before\n                        the current hour will be chosen.\n                        \n                        Given this tuning\n                            beginning_hour        is_moonlight_on\n                                6                         true\n                                10                        false\n                                14                        true\n                                20                        false\n                                \n                            if the current hour is 11, hour_of_day will be 10 and moonlight_on is false, so moonlight is disabled.\n                            if the current hour is 19, hour_of_day will be 14 and moonlight_on is true, so moonlight is enabled.\n                            if the current hour is 23, hour_of_day will be 20 and moonlight_on is false, so moonlight is disabled.\n                            if the current hour is 2, hour_of_day will be 20 and moonlight_on is false. (uses 20 tuning because it is not 6 yet)\n                            \n                        The entries will be automatically sorted by time.\n                        ', key_type=Tunable(tunable_type=int, default=0), value_type=Tunable(tunable_type=bool, default=False), key_name='beginning_hour', value_name='is_moonlight_on'))))}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._bowling_lanes = self._get_bowling_lanes()
        self._bowling_lanes_dict = {}
        self._bowling_situation_alarm_handle = None
        self._moonlight_alarm_handle = None

    def create_situations_during_zone_spin_up(self):
        super().create_situations_during_zone_spin_up()
        self._initialize_alarms()

    def on_shutdown(self):
        super().on_shutdown()
        if self._bowling_situation_alarm_handle is not None:
            alarms.cancel_alarm(self._bowling_situation_alarm_handle)
            self._bowling_situation_alarm_handle = None
        if self._moonlight_alarm_handle is not None:
            alarms.cancel_alarm(self._moonlight_alarm_handle)
            self._moonlight_alarm_handle = None

    def on_exit_buildbuy(self):
        super().on_exit_buildbuy()
        self._bowling_lanes = self._get_bowling_lanes()

    def _initialize_alarms(self):
        repeating_time_span = date_and_time.create_time_span(minutes=self.bowling_venue.situation_alarm_interval)
        self._bowling_situation_alarm_handle = alarms.add_alarm(self, date_and_time.create_time_span(minutes=5), self._find_available_lane_and_start_situations, repeating=True, repeating_time_span=repeating_time_span)
        if self.bowling_venue.moonlight_on_off_schedule:
            self._moonlight_change()
            time_of_day = services.time_service().sim_now
            self._moonlight_alarm_handle = alarms.add_alarm(self, self._get_time_span_to_next_moonlight_schedule(time_of_day), self._moonlight_change)

    def get_total_bowling_lanes(self):
        if self._bowling_lanes is None:
            return 0
        return len(self._bowling_lanes)

    def set_situation_bowling_lane(self, situation_id, bowling_lane_obj):
        self._bowling_lanes_dict[situation_id] = bowling_lane_obj

    def get_situation_bowling_lane(self, situation_id):
        return self._bowling_lanes_dict.get(situation_id)

    def remove_situation_bowling_lane(self, situation_id):
        if situation_id in self._bowling_lanes_dict:
            del self._bowling_lanes_dict[situation_id]

    def _get_bowling_lanes(self):
        if self.BOWLING_LANE_OBJECT_TAGS is None:
            return
        else:
            bowling_lanes = list(services.object_manager().get_objects_with_tags_gen(*self.BOWLING_LANE_OBJECT_TAGS))
            if len(bowling_lanes) == 0:
                return
        return bowling_lanes

    def _get_number_of_sims_in_all_situations(self):
        situation_manager = services.get_zone_situation_manager()
        if situation_manager is None:
            return 0
        total_sims = 0
        for (situation_id, _) in self._bowling_lanes_dict.items():
            situation = situation_manager.get(situation_id)
            if situation is not None:
                total_sims += len(situation._situation_sims)
        return total_sims

    def _find_available_lane_and_start_situations(self, *_):
        if self._bowling_lanes is None:
            return
        if self.get_total_bowling_lanes() - len(self._bowling_lanes_dict) <= 1:
            return
        if self._get_number_of_sims_in_all_situations() >= self.MAX_SIMS_ON_VENUE:
            return
        for bowling_lane_obj in self._bowling_lanes:
            if bowling_lane_obj.in_use:
                pass
            elif bowling_lane_obj in self._bowling_lanes_dict.values():
                pass
            else:
                self._start_bowling_situation(bowling_lane_obj)
                break

    def _start_bowling_situation(self, bowling_lane_obj):
        situation_manager = services.get_zone_situation_manager()
        if not self.bowling_venue.bowling_situations_schedule.entries:
            return
        total_bowling_lanes = self.get_total_bowling_lanes()
        all_weighted_situations = self.bowling_venue.bowling_situations_schedule.get_weighted_situations()
        weighted_situations = [(weight, situation[0]) for (weight, situation) in all_weighted_situations if situation[0].situation_meets_starting_requirements(total_bowling_lanes)]
        if not weighted_situations:
            return
        situation_to_create = weighted_random_item(weighted_situations)
        guest_list = situation_to_create.get_predefined_guest_list()
        if guest_list is None:
            guest_list = SituationGuestList(invite_only=True)
        situation_id = situation_manager.create_situation(situation_to_create, guest_list=guest_list, spawn_sims_during_zone_spin_up=True, user_facing=False)
        self.set_situation_bowling_lane(situation_id, bowling_lane_obj)
        return situation_id

    def _get_sorted_moonlight_schedule(self, day):
        moonlight_schedule = []
        for item in self.bowling_venue.moonlight_on_off_schedule:
            enabled = item.days_of_the_week.get(day, None)
            if enabled:
                for (beginning_hour, is_on) in item.moonlight_on_off_desire_by_time_of_day.items():
                    moonlight_schedule.append((beginning_hour, is_on))
        moonlight_schedule.sort(key=operator.itemgetter(0))
        return moonlight_schedule

    def _moonlight_change(self, alarm_handle=None):
        if not self.bowling_venue.moonlight_on_off_schedule:
            return
        if self._get_desired_is_moonlight_on():
            self._activate_moonlight_affordance(self.MOONLIGHT_AFFORDANCES.moonlight_on)
        else:
            self._activate_moonlight_affordance(self.MOONLIGHT_AFFORDANCES.moonlight_off)
        if alarm_handle is not None:
            time_of_day = services.time_service().sim_now
            self._moonlight_alarm_handle = alarms.add_alarm(self, self._get_time_span_to_next_moonlight_schedule(time_of_day), self._moonlight_change)

    def _get_desired_is_moonlight_on(self):
        if not self.bowling_venue.moonlight_on_off_schedule:
            return
        time_of_day = services.time_service().sim_now
        hour_of_day = time_of_day.hour()
        day = time_of_day.day()
        moonlight_schedule = self._get_sorted_moonlight_schedule(day)
        if not moonlight_schedule:
            return
        entry = moonlight_schedule[-1]
        desire = entry[1]
        for entry in moonlight_schedule:
            if entry[0] <= hour_of_day:
                desire = entry[1]
            else:
                break
        return desire

    def _get_time_span_to_next_moonlight_schedule(self, time_of_day):
        if not self.bowling_venue.moonlight_on_off_schedule:
            return
        days_to_schedule_ahead = 1
        current_day = time_of_day.day()
        next_day = (current_day + days_to_schedule_ahead) % 7
        next_day_sorted_times = self._get_sorted_moonlight_schedule(next_day)
        if next_day_sorted_times:
            next_moonlight_hour = next_day_sorted_times[0][0]
        else:
            next_moonlight_hour = 0
        now = services.time_service().sim_now
        sorted_times = self._get_sorted_moonlight_schedule(current_day)
        scheduled_day = int(now.absolute_days())
        now_hour = now.hour()
        for (moonlight_hour, _) in sorted_times:
            if moonlight_hour > now_hour:
                next_moonlight_hour = moonlight_hour
                break
        scheduled_day += 1
        future = date_and_time.create_date_and_time(days=scheduled_day, hours=next_moonlight_hour)
        time_span_until = future - now
        return time_span_until

    def _activate_moonlight_affordance(self, affordance):
        if self._bowling_lanes is None:
            return
        moonlight_state = affordance.state_settings.desired_state
        for bowling_lane in self._bowling_lanes:
            if moonlight_state == bowling_lane.get_state(moonlight_state.state):
                pass
            else:
                affordance.target = bowling_lane
                affordance.state_settings.execute_helper(affordance)
                affordance.lighting_setting_operation.execute(affordance)
