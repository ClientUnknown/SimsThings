import itertoolsimport mathimport randomfrom protocolbuffers import GameplaySaveData_pb2 as gameplay_serializationfrom distributor.rollback import ProtocolBufferRollbackfrom event_testing.resolver import SingleSimResolverfrom interactions.social.social_super_interaction import SocialSuperInteractionfrom sims4.tuning.geometric import TunableCurvefrom sims4.tuning.tunable import TunableRange, TunableReferencefrom sims4.utils import classpropertyfrom situations.ambient.walkby_ambient_situation import WalkbyAmbientSituationfrom situations.bouncer.bouncer_types import RequestSpawningOption, BouncerRequestPriorityfrom situations.situation_guest_list import SituationGuestList, SituationGuestInfofrom tunable_time import TunableTimeOfDayfrom tunable_utils.tested_list import TunableTestedListimport alarmsimport clockimport enumimport gsi_handlersimport persistence_error_typesimport servicesimport sims.ghostimport sims4.logimport sims4.service_managerimport sims4.tuning.tunableimport situations.situation_guest_listimport terrainimport world.lot_tuninglogger = sims4.log.Logger('Ambient')with sims4.reload.protected(globals()):
    gsi_logging_enabled = False
class AmbientSourceType(enum.Int, export=False):
    SOURCE_STREET = 1
    SOURCE_GHOST = 2

class _AmbientSource:
    DEFAULT_PRIORITY_MULTIPLIER = 2.1

    def __init__(self, priority_multiplier):
        self._running_situation_ids = []
        self._priority_multipler = priority_multiplier

    @classproperty
    def source_type(cls):
        raise NotImplemented

    def is_valid(self):
        raise NotImplemented

    def save(self, source_data):
        source_data.source_type = self.source_type
        source_data.situation_ids.extend(self._running_situation_ids)

    def load(self, source_data):
        self._running_situation_ids = list(source_data.situation_ids)

    def begin_scheduled_walkbys(self):
        pass

    def _get_free_sim_slots(self):
        return self.get_desired_number_of_sims() - self.get_current_number_of_sims()

    def get_priority(self):
        imbalance = self._get_free_sim_slots()
        return imbalance*self._priority_multipler

    def get_desired_number_of_sims(self):
        raise NotImplemented

    def get_current_number_of_sims(self):
        self._cleanup_running_situations()
        situation_manager = services.get_zone_situation_manager()
        num_of_sims = 0
        for situation_id in self._running_situation_ids:
            situation = situation_manager.get(situation_id)
            if situation is None:
                pass
            else:
                sims_in_situation = situation.get_sims_expected_to_be_in_situation()
                if sims_in_situation is None:
                    pass
                else:
                    num_of_sims += sims_in_situation
        return num_of_sims

    def start_appropriate_situation(self, time_of_day=None):
        raise NotImplemented

    def start_specific_situation(self, situation_type):
        return self._start_specific_situation(situation_type)

    def _create_standard_ambient_guest_list(self, situation_type, **__):
        guest_list = situation_type.get_predefined_guest_list()
        if guest_list is None:
            client = services.client_manager().get_first_client()
            if client is None:
                logger.warn('No clients found when trying to get the active sim for ambient autonomy.', owner='sscholl')
                return
            active_sim_info = client.active_sim_info
            active_sim_id = active_sim_info.id if active_sim_info is not None else 0
            guest_list = situations.situation_guest_list.SituationGuestList(invite_only=True, host_sim_id=active_sim_id)
            if situation_type.default_job() is not None:
                guest_info = situations.situation_guest_list.SituationGuestInfo.construct_from_purpose(0, situation_type.default_job(), situations.situation_guest_list.SituationInvitationPurpose.WALKBY)
                guest_list.add_guest_info(guest_info)
        return guest_list

    def get_running_situations(self):
        situations = []
        situation_manager = services.current_zone().situation_manager
        for situation_id in self._running_situation_ids:
            situation = situation_manager.get(situation_id)
            if situation is not None:
                situations.append(situation)
        return situations

    def _start_specific_situation(self, situation_type, **kwargs):
        situation_manager = services.current_zone().situation_manager
        guest_list = self._create_standard_ambient_guest_list(situation_type, **kwargs)
        situation_id = situation_manager.create_situation(situation_type, guest_list=guest_list, user_facing=False)
        if situation_id is not None:
            self._running_situation_ids.append(situation_id)
        return situation_id

    def _cleanup_running_situations(self):
        situation_manager = services.current_zone().situation_manager
        to_delete_ids = []
        for situation_id in self._running_situation_ids:
            if situation_id not in situation_manager:
                to_delete_ids.append(situation_id)
        for delete_id in to_delete_ids:
            self._running_situation_ids.remove(delete_id)

    def get_gsi_description(self):
        return 'Unknown, {0}, {1}'.format(self.get_desired_number_of_sims(), self.get_current_number_of_sims())

class _AmbientSourceStreet(_AmbientSource):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        lot_tuning = world.lot_tuning.LotTuningMaps.get_lot_tuning()
        if lot_tuning is not None:
            self._walkby_tuning = lot_tuning.walkby
            self._walkby_schedule = None if lot_tuning.walkby_schedule is None else lot_tuning.walkby_schedule()
        else:
            self._walkby_tuning = None
            self._walkby_schedule = None

    @classproperty
    def source_type(cls):
        return AmbientSourceType.SOURCE_STREET

    def is_valid(self):
        return self._walkby_tuning is not None

    def get_desired_number_of_sims(self):
        if not self._walkby_tuning:
            return 0
        return self._walkby_tuning.get_desired_sim_count().lower_bound

    def start_appropriate_situation(self, time_of_day=None):
        if not self._walkby_tuning:
            return
        num_to_start = self._walkby_tuning.get_desired_sim_count().random_int() - self.get_current_number_of_sims()
        situation_type = self._walkby_tuning.get_ambient_walkby_situation(num_to_start)
        if situation_type is None:
            return
        return self._start_specific_situation(situation_type)

    def begin_scheduled_walkbys(self):
        super().begin_scheduled_walkbys()
        if self._walkby_schedule is not None:
            self._walkby_schedule.on_startup()

    def get_gsi_description(self):
        if self._walkby_tuning is None:
            street = 'Unknown Street'
        else:
            street = self._walkby_tuning.__name__
        return '({0}, {1}, {2})'.format(street, self.get_desired_number_of_sims(), self.get_current_number_of_sims())

    def save(self, source_data):
        super().save(source_data)
        if self._walkby_schedule is not None:
            self._walkby_schedule.save_situation_shifts(source_data)

    def load(self, source_data):
        super().load(source_data)
        if self._walkby_schedule is not None:
            self._walkby_schedule.load_situation_shifts(source_data)

class _AmbientSourceGhost(_AmbientSource):
    GHOST_SITUATIONS = TunableTestedList(description='\n        A list of possible ghost situations, tested aginst the Sim we want to\n        spawn.\n        ', tunable_type=TunableReference(description='\n            The ghost situation to spawn.\n            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION), pack_safe=True))
    DESIRED_GHOST_COUNT_PER_URNSTONE = TunableCurve(description='\n        This curve describes the maximum number of ghosts we want in the world\n        based on the number of valid urnstones in the world. If there are more\n        urnstones than the maximum number tuned on the X axis, we will just use\n        the final Y value.\n        ', x_axis_name='Valid Urnstones', y_axis_name='Desired Ghost Count')
    WALKBY_ALLOWED_START_TIME = TunableTimeOfDay(description='\n        The time of the day (24hr) when NPC ghosts can start doing walkbys.\n        ', default_hour=21)
    WALKBY_ALLOWED_DURATION = TunableRange(description="\n        The amount of time, in sim hours, past the 'Walkby Start Time' that the\n        ghost walkbys can start.\n        ", tunable_type=float, default=5, minimum=0, maximum=23)

    @classproperty
    def source_type(cls):
        return AmbientSourceType.SOURCE_GHOST

    def is_valid(self):
        return True

    @classmethod
    def _is_correct_time(cls):
        current_time = services.time_service().sim_now
        start_time = cls.WALKBY_ALLOWED_START_TIME
        end_time = start_time + clock.interval_in_sim_hours(cls.WALKBY_ALLOWED_DURATION)
        return current_time.time_between_day_times(start_time, end_time)

    def get_desired_number_of_sims(self):
        if not self._is_correct_time():
            return 0
        urnstones = sims.ghost.Ghost.get_valid_urnstones()
        if not urnstones:
            return 0
        return self.DESIRED_GHOST_COUNT_PER_URNSTONE.get(len(urnstones))

    def start_appropriate_situation(self, time_of_day=None):
        urnstones = sims.ghost.Ghost.get_valid_urnstones()
        sim_info = random.choice(urnstones).get_stored_sim_info()
        resolver = SingleSimResolver(sim_info)
        for situation_type in self.GHOST_SITUATIONS(resolver=resolver):
            if self._start_specific_situation(situation_type, sim_info=sim_info):
                return True
        return False

    def _create_standard_ambient_guest_list(self, situation_type, *, sim_info):
        guest_list = SituationGuestList(invite_only=True)
        guest_list.add_guest_info(SituationGuestInfo(sim_info.sim_id, situation_type.default_job(), RequestSpawningOption.MUST_SPAWN, BouncerRequestPriority.BACKGROUND_LOW))
        return guest_list

    def get_gsi_description(self):
        return '(Ghost, {0}, {1})'.format(self.get_desired_number_of_sims(), self.get_current_number_of_sims())

class AmbientService(sims4.service_manager.Service):
    TEST_WALKBY_SITUATION = sims4.tuning.tunable.TunableReference(description='\n                                            A walkby situation for testing.\n                                            ', manager=services.get_instance_manager(sims4.resources.Types.SITUATION))
    SOCIAL_AFFORDANCES = sims4.tuning.tunable.TunableList(description='\n        When selected for a walkby social the sim runs one of the social\n        affordances in this list.\n        ', tunable=SocialSuperInteraction.TunableReference())
    SOCIAL_COOLDOWN = sims4.tuning.tunable.TunableSimMinute(description='\n            The minimum amount of time from the end of one social\n            until the walkby sim can perform another social. If it is too small\n            sims may socialize, stop, then start socializing again.\n            ', default=60, minimum=30, maximum=480)
    SOCIAL_MAX_DURATION = sims4.tuning.tunable.TunableSimMinute(description='\n            The maximum amount of time the sims can socialize.\n            ', default=60, minimum=1, maximum=180)
    SOCIAL_MAX_START_DISTANCE = sims4.tuning.geometric.TunableDistanceSquared(description='\n            Walkby Sims must be less than this distance apart for a social\n            to be started.\n            ', default=10)
    SOCIAL_VIEW_CONE_ANGLE = sims4.tuning.tunable.TunableAngle(description='\n            For 2 sims to be able to socialize at least one sim must be in the\n            view cone of the other. This tunable defines the view cone as an angle\n            in degrees centered straight out in front of the sim. 0 degrees would \n            make the sim blind, 360 degrees means the sim can see in all directions.\n            ', default=sims4.math.PI)
    SOCIAL_CHANCE_TO_START = sims4.tuning.tunable.TunablePercent(description='\n            This is the percentage chance, per pair of properly positioned sims,\n            that a social will be started on an ambient service ping.\n\n            The number of pairs of sims is multiplied by this tunable to get the overall\n            chance of a social starting.\n            \n            For the purposes of these examples, we assume that the tuned value is 25%\n            \n            1 pair of sims -> 25%.\n            2 pairs of sims -> 50%\n            4 pairs of sims -> 100%.\n\n            ', default=100)

    def __init__(self):
        self._update_alarm_handle = None
        self._flavor_alarm_handle = None
        self._sources = []

    def stop(self):
        if self._update_alarm_handle is not None:
            alarms.cancel_alarm(self._update_alarm_handle)
            self._update_alarm_handle = None
        if self._flavor_alarm_handle is not None:
            alarms.cancel_alarm(self._flavor_alarm_handle)
            self._flavor_alarm_handle = None

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_AMBIENT_SERVICE

    def save(self, open_street_data=None, **kwargs):
        if open_street_data is None:
            return
        open_street_data.ambient_service = gameplay_serialization.AmbientServiceData()
        for source in self._sources:
            with ProtocolBufferRollback(open_street_data.ambient_service.sources) as source_data:
                source.save(source_data)

    def begin_walkbys(self):
        self._sources.append(_AmbientSourceStreet(_AmbientSource.DEFAULT_PRIORITY_MULTIPLIER))
        self._sources.append(_AmbientSourceGhost(_AmbientSource.DEFAULT_PRIORITY_MULTIPLIER))
        for source in self._sources:
            source.begin_scheduled_walkbys()
        open_street_id = services.current_zone().open_street_id
        open_street_data = services.get_persistence_service().get_open_street_proto_buff(open_street_id)
        if open_street_data is not None:
            for source_data in open_street_data.ambient_service.sources:
                for source in self._sources:
                    if source.source_type == source_data.source_type:
                        source.load(source_data)
                        break
        self._update_alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(5), self._update_alarm_callback, repeating=True, use_sleep_time=False)
        self._flavor_alarm_handle = alarms.add_alarm(self, clock.interval_in_sim_minutes(1), self._flavor_alarm_callback, repeating=True, use_sleep_time=False)

    def debug_update(self):
        return self._update(force_create=True)

    def start_specific_situation(self, situation_type):
        return self._sources[0].start_specific_situation(situation_type)

    def _update_alarm_callback(self, alarm_handle=None):
        client = services.client_manager().get_first_client()
        if client is None:
            return
        self._update()

    def _update(self, force_create=False):
        if not self._sources:
            return
        if gsi_handlers.ambient_handlers.archiver.enabled:
            gsi_description = self.get_gsi_description()
        else:
            gsi_description = None
        sources_and_priorities = [(source, source.get_priority()) for source in self._sources]
        sources_and_priorities.sort(key=lambda source: source[1], reverse=True)
        situation_id = None
        source = sources_and_priorities[0][0]
        priority = sources_and_priorities[0][1]
        if priority > 0:
            situation_id = source.start_appropriate_situation()
        elif force_create:
            for (source, _) in sources_and_priorities:
                situation_id = source.start_appropriate_situation()
                if situation_id is not None:
                    break
        if gsi_handlers.ambient_handlers.archiver.enabled:
            situation = None
            if situation_id is not None:
                situation = services.current_zone().situation_manager.get(situation_id)
            gsi_handlers.ambient_handlers.archive_ambient_data(gsi_description, created_situation=str(situation))
        return situation_id

    def _flavor_alarm_callback(self, _):
        if not self._sources:
            return
        social_available_sim_to_situation = {}
        flavor_available_sim_to_situation = {}
        for source in self._sources:
            for situation in source.get_running_situations():
                if isinstance(situation, WalkbyAmbientSituation):
                    sim = situation.get_sim_available_for_social()
                    if sim is not None:
                        social_available_sim_to_situation[sim] = situation
                    sim = situation.get_sim_available_for_walkby_flavor()
                    if sim is not None:
                        flavor_available_sim_to_situation[sim] = situation
        social_available_sims = list(social_available_sim_to_situation.keys())
        available_social_pairs = []
        for (actor_sim, target_sim) in itertools.combinations(social_available_sims, 2):
            if self._can_sims_start_social(actor_sim, target_sim):
                available_social_pairs.append((actor_sim, target_sim))
        if available_social_pairs and sims4.random.random_chance(len(available_social_pairs)*self.SOCIAL_CHANCE_TO_START*100):
            (actor_sim, target_sim) = available_social_pairs[random.randint(0, len(available_social_pairs) - 1)]
            social_available_sim_to_situation[actor_sim].start_social(social_available_sim_to_situation[target_sim])
            flavor_available_sim_to_situation.pop(actor_sim, None)
            flavor_available_sim_to_situation.pop(target_sim, None)
        for situation in flavor_available_sim_to_situation.values():
            if situation.random_chance_to_start_flavor_interaction():
                situation.start_flavor_interaction()
                break

    def _sim_forward_to_sim_dot(self, sim_one, sim_two):
        one_to_two = sim_two.position - sim_one.position
        one_to_two.y = 0
        if sims4.math.vector3_almost_equal(one_to_two, sims4.math.Vector3.ZERO()):
            return 1
        one_to_two = sims4.math.vector_normalize(one_to_two)
        one_to_two_dot = sims4.math.vector_dot_2d(sims4.math.vector_flatten(sim_one.forward), one_to_two)
        return one_to_two_dot

    def _can_sims_start_social(self, actor_sim, target_sim):
        distance_squared = (actor_sim.position - target_sim.position).magnitude_squared()
        if distance_squared > self.SOCIAL_MAX_START_DISTANCE:
            return False
        cone_dot = math.cos(self.SOCIAL_VIEW_CONE_ANGLE*0.5)
        actor_to_target_dot = self._sim_forward_to_sim_dot(actor_sim, target_sim)
        if actor_to_target_dot <= cone_dot:
            target_to_actor_dot = self._sim_forward_to_sim_dot(target_sim, actor_sim)
            if target_to_actor_dot <= cone_dot:
                return False
        if terrain.is_position_in_street(actor_sim.position):
            return False
        if terrain.is_position_in_street(target_sim.position):
            return False
        else:
            middle_position = (actor_sim.position + target_sim.position)*0.5
            if terrain.is_position_in_street(middle_position):
                return False
        return True

    def get_gsi_description(self):
        if not self._sources:
            return ''
        description = self._sources[0].get_gsi_description()
        for source in self._sources[1:]:
            description = description + '   ' + source.get_gsi_description()
        return description
