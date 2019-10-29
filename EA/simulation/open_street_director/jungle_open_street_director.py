import itertoolsimport randomfrom date_and_time import DateAndTimefrom event_testing.test_events import TestEventfrom objects.components.portal_lock_data import LockAllWithSimIdExceptionDatafrom objects.components.portal_locking_enums import LockPriority, LockSidefrom objects.components.state import TunableStateValueReferencefrom open_street_director.open_street_director import OpenStreetDirectorBase, OpenStreetDirectorPriorityfrom sims4.tuning.tunable import TunableMapping, TunableReference, Tunable, TunableTuple, TunableRange, TunableList, TunablePackSafeReferencefrom sims4.utils import classpropertyfrom situations.situation_complex import TunableInteractionOfInterestfrom tag import TunableTagfrom temple.temple_tuning import TempleTuningimport servicesimport sims4.resourceslogger = sims4.log.Logger('JungleOpenStreetDirector', default_owner='rfleig')GROUP_TOKEN = 'group'TAG_TOKEN = 'tag'TAG_STATUS_TOKEN = 'tag_status'CLEAR_PROGRESS_TOKEN = 'clear_progress'CURRENT_TEMPLE_ID = 'temple_id'TEMPLE_STATE = 'temple_state'LAST_TIME_SAVED = 'last_time_saved'TREASURE_CHEST_GROUP = 'treasure_chest_group'TREASURE_CHEST_ID = 'treasure_chest_id'TREASURE_CHEST_STATUS = 'treasure_chest_status'
class JungleOpenStreetDirector(OpenStreetDirectorBase):
    DEFAULT_LOCK = LockAllWithSimIdExceptionData(lock_priority=LockPriority.PLAYER_LOCK, lock_sides=LockSide.LOCK_FRONT, should_persist=True, except_actor=False, except_household=False)
    PATH_LOCKED = 0
    PATH_UNAVAILABLE = 1
    PATH_UNLOCKED = 2
    MIN_CLEAR_COMMODITY = 0
    TEMPLE_STATE_NEEDS_RESET = 0
    TEMPLE_STATE_RESET = 1
    TEMPLE_STATE_IN_PROGRESS = 2
    TEMPLE_STATE_COMPLETE = 3
    TREASURE_CHEST_CLOSED = 0
    TREASURE_CHEST_OPEN = 1
    TEMPLE_PATH_OBSTACLE = TunableTag(description='\n        The tag for the path obstacle that leads to the Temple. This will be\n        used to gain a reference to it when the temple resets.\n        ', filter_prefixes=('Func',))
    TEMPLE_PATH_OBSTACLE_LOCK_STATE = TunableStateValueReference(description='\n        Indicates the temple is locked. This will be used to lock the\n        Path Obstacle.\n        ', pack_safe=True)
    TEMPLE_PATH_OBSTACLE_UNLOCK_STATE = TunableStateValueReference(description='\n        The unlock state for the path obstacles. Set when we load a brand new\n        vacation in the jungle.\n        ', pack_safe=True)
    TEMPLE_VENUE_TYPE = TunablePackSafeReference(description='\n        The venue type for the temple zone.\n        ', manager=services.get_instance_manager(sims4.resources.Types.VENUE))
    TEMPLE_LOCK_COMMODITY = TunablePackSafeReference(description='\n        The commodity that controls the temple lock.\n        ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='Commodity')
    INSTANCE_TUNABLES = {'path_obstacle_data': TunableMapping(description='\n            Tuned data for the path obstacles in the open street. \n            \n            This includes which conditional layer the path obstacle is attached\n            to and what state that layer is in when the obstacle is locked.\n            ', key_name='obstacle_tag_id', key_type=TunableTag(description='\n                A tag for a specific path obstacle object that we might want\n                to mark blocked or access_PermanentlyBlocked. \n                ', filter_prefixes=('Func',)), value_name='obstacle_data', value_type=TunableTuple(description='\n                All of the data associated with the path obstacle.\n                ', always_available=Tunable(description='\n                    If True then this particular path obstacle is always \n                    available to be cleared and traveled through.\n                    \n                    If False then this path obstacle is subject to randomly\n                    being available or unavailable depending on the travel\n                    group.\n                    ', tunable_type=bool, default=False), layers=TunableList(description='\n                    A list of conditional layers and the status the layer starts\n                    in (visible/hidden) that are associated with this path\n                    obstacle.\n                    ', tunable=TunableTuple(description='\n                        Data about which conditional layer the obstacle is associated\n                        with and what state it is in.\n                        ', conditional_layer=TunableReference(description='\n                            A reference to the Conditional Layer found in the open streets.\n                            ', manager=services.get_instance_manager(sims4.resources.Types.CONDITIONAL_LAYER)), visible=Tunable(description='\n                            Whether or not the conditional layer is show/hidden when\n                            the corresponding path obstacle is locked.\n                            \n                            Checked signifies that the layer is visible when the\n                            obstacle is locked.\n                            \n                            Unchecked signifies that the layer is hidden when the \n                            obstacle is locked.\n                            ', tunable_type=bool, default=True), immediate=Tunable(description='\n                            If checked then the layer will load immediately. If\n                            not checked then the layer will load over time.\n                            ', tunable_type=bool, default=False))))), 'num_of_paths_available': TunableRange(description='\n            The number of paths that are available when a vacation group \n            arrives in the jungle for the first time.\n            ', tunable_type=int, minimum=0, default=1), 'clear_path_interaction': TunableInteractionOfInterest(description='\n            A reference to the interaction that a Sim runs in order to clear\n            the path obstacle so they can use the portal.\n            '), 'permanently_blocked_state': TunableStateValueReference(description='\n            The state the blocked path obstacles should be set to if they \n            cannot be cleared.\n            '), 'path_unlocked_state': TunableStateValueReference(description='\n            The state the blocked path obstacles should be set to if they are \n            unlocked.\n            '), 'path_clearing_commodity': TunableReference(description='\n            The commodity that has to reach 100 in order for a path to be\n            considered clear.\n            ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC)), 'treasure_chest_tag': TunableTag(description='\n            The tag used to identify a treasure chest.\n            '), 'treasure_chest_open_state': TunableStateValueReference(description='\n            The state that a treasure chest is in when it has already been \n            opened.\n            '), 'treasure_chest_closed_state': TunableStateValueReference(description='\n            The state that a treasure chest is in when it is still closed.\n            ')}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._obstacle_status = {}
        self._path_obstacles = {}
        self._treasure_chest_status = {}
        travel_group_manager = services.travel_group_manager()
        household = services.active_household()
        travel_group = travel_group_manager.get_travel_group_by_household(household)
        if travel_group is None:
            logger.error("Trying to initialize the Jungle Open Street Director but there doesn't appear to be a travel group for the current household.")
            self._current_travel_group_id = None
        else:
            self._current_travel_group_id = travel_group.id
        services.get_event_manager().register_single_event(self, TestEvent.InteractionComplete)
        self._current_temple_id = None
        self._temple_state = self.TEMPLE_STATE_NEEDS_RESET
        self._last_time_saved = None

    def on_startup(self):
        super().on_startup()
        object_manager = services.object_manager()
        self._path_obstacles = self._get_path_obstacles()
        if self._current_travel_group_id in self._obstacle_status:
            path_obstacle_data = self._obstacle_status[self._current_travel_group_id]
            for (tag, status, progress) in path_obstacle_data:
                obstacles = object_manager.get_objects_matching_tags((tag,))
                for obstacle in obstacles:
                    if not obstacle.state_value_active(self.TEMPLE_PATH_OBSTACLE_UNLOCK_STATE):
                        self._update_temple_lock_commodity()
                        if obstacle.state_value_active(self.TEMPLE_PATH_OBSTACLE_UNLOCK_STATE):
                            status = JungleOpenStreetDirector.PATH_LOCKED
                        else:
                            status = JungleOpenStreetDirector.PATH_UNAVAILABLE
                        progress = 0
                    if tag == self.TEMPLE_PATH_OBSTACLE and status == JungleOpenStreetDirector.PATH_LOCKED:
                        self._lock_path_obstacle(obstacle, tag)
                    elif status == JungleOpenStreetDirector.PATH_UNAVAILABLE:
                        self._permanently_lock_path_obstacle(obstacle, tag)
                    elif status == JungleOpenStreetDirector.PATH_UNLOCKED:
                        self._unlock_path_obstacle(obstacle, tag)
                    else:
                        logger.error('Trying to setup an object that has a tag status that is not known. {}', status)
                    obstacle.set_stat_value(self.path_clearing_commodity, progress)
            if self._current_travel_group_id in self._treasure_chest_status:
                treasure_chest_data = self._treasure_chest_status[self._current_travel_group_id]
                for (obj_id, status) in treasure_chest_data:
                    chest = object_manager.get(obj_id)
                    if chest is None:
                        pass
                    elif status == JungleOpenStreetDirector.TREASURE_CHEST_OPEN:
                        chest.set_state(self.treasure_chest_open_state.state, self.treasure_chest_open_state)
                    else:
                        chest.set_state(self.treasure_chest_closed_state.state, self.treasure_chest_closed_state)
        else:
            always_available_paths = []
            possible_paths = []
            for (obj, tag) in self._path_obstacles.items():
                if self.path_obstacle_data[tag].always_available:
                    always_available_paths.append((obj, tag))
                else:
                    possible_paths.append((obj, tag))
            available_paths = random.sample(possible_paths, min(len(possible_paths), self.num_of_paths_available))
            unavailable_paths = [path for path in possible_paths if path not in available_paths]
            for (path_obstacle, tag) in itertools.chain(always_available_paths, available_paths):
                self._lock_path_obstacle(path_obstacle, tag, reset_commodity=True)
            for (path_obstacle, tag) in unavailable_paths:
                self._permanently_lock_path_obstacle(path_obstacle, tag)
            for chest in object_manager.get_objects_matching_tags((self.treasure_chest_tag,)):
                chest.set_state(self.treasure_chest_closed_state.state, self.treasure_chest_closed_state)
            travel_group_manager = services.travel_group_manager()
            travel_groups = travel_group_manager.get_travel_group_ids_in_region()
            for group_id in travel_groups:
                if group_id == self._current_travel_group_id:
                    pass
                else:
                    group = travel_group_manager.get(group_id)
                    if group.played:
                        break
            self._setup_for_first_travel_group()
        if self._temple_needs_reset():
            self.reset_temple()

    def _update_temple_lock_commodity(self):
        obstacle = self._get_temple_entrance_obstacle()
        lock_tracker = obstacle.get_tracker(JungleOpenStreetDirector.TEMPLE_LOCK_COMMODITY)
        lock_stat = lock_tracker.get_statistic(JungleOpenStreetDirector.TEMPLE_LOCK_COMMODITY)
        lock_stat.update_commodity_to_time(self._last_time_saved)
        lock_state = JungleOpenStreetDirector.TEMPLE_PATH_OBSTACLE_UNLOCK_STATE.state
        obstacle.state_component.set_state_from_stat(lock_state, lock_stat)

    def _temple_needs_reset(self):
        if self._temple_state == self.TEMPLE_STATE_NEEDS_RESET:
            return True
        elif self._temple_state == self.TEMPLE_STATE_COMPLETE:
            sim_info_manager = services.sim_info_manager()
            temple_zones = tuple(services.venue_service().get_zones_for_venue_type_gen(self.TEMPLE_VENUE_TYPE))
            if len(temple_zones) != 1:
                logger.error('Found either 0 or more than 1 zone that is set as a temple venue. There can be only one!')
            temple_zone_id = next(iter(temple_zones))
            if not any(sim.zone_id == temple_zone_id and sim.is_played_sim for sim in sim_info_manager.get_all()):
                return True
        return False

    def _setup_for_first_travel_group(self):
        self._current_temple_id = None
        self._temple_state = self.TEMPLE_STATE_NEEDS_RESET
        self._unlock_temple_obstacle()

    def on_shutdown(self):
        super().on_shutdown()
        services.get_event_manager().unregister_single_event(self, TestEvent.InteractionComplete)
        self._path_obstacles.clear()

    def _get_path_obstacles(self):
        object_manager = services.object_manager()
        path_obstacles = {}
        for obstacle_tag in self.path_obstacle_data:
            obstacles = object_manager.get_objects_matching_tags((obstacle_tag,))
            for obstacle in obstacles:
                path_obstacles[obstacle] = obstacle_tag
        return path_obstacles

    def _lock_path_obstacle(self, path_obstacle, obstacle_tag, reset_commodity=False):
        path_obstacle.add_lock_data(JungleOpenStreetDirector.DEFAULT_LOCK)
        self._setup_corresponding_layers(obstacle_tag)
        if reset_commodity:
            path_obstacle.set_stat_value(self.path_clearing_commodity, JungleOpenStreetDirector.MIN_CLEAR_COMMODITY)

    def _permanently_lock_path_obstacle(self, path_obstacle, obstacle_tag):
        path_obstacle.add_lock_data(JungleOpenStreetDirector.DEFAULT_LOCK)
        path_obstacle.set_state(self.permanently_blocked_state.state, self.permanently_blocked_state)
        self._setup_corresponding_layers(obstacle_tag)

    def _unlock_path_obstacle(self, path_obstacle, obstacle_tag):
        path_obstacle.set_state(self.path_unlocked_state.state, self.path_unlocked_state)
        self._setup_corresponding_layers(obstacle_tag, unlock=True)

    def _setup_corresponding_layers(self, path_obstacle_tag, unlock=False):
        obstacle_datas = self.path_obstacle_data[path_obstacle_tag]
        for obstacle_data in obstacle_datas.layers:
            if unlock == obstacle_data.visible:
                self.remove_layer_objects(obstacle_data.conditional_layer)
            elif obstacle_data.immediate:
                self.load_layer_immediately(obstacle_data.conditional_layer)
            else:
                self.load_layer_gradually(obstacle_data.conditional_layer)

    @classproperty
    def priority(cls):
        return OpenStreetDirectorPriority.DEFAULT

    def handle_event(self, sim_info, event, resolver, **kwargs):
        if resolver(self.clear_path_interaction):
            obstacle = resolver.interaction.target
            statistic = obstacle.get_stat_instance(self.path_clearing_commodity)
            if statistic is not None:
                statistic_value = statistic.get_value()
                if statistic_value >= statistic.max_value:
                    obstacle.set_state(self.path_unlocked_state.state, self.path_unlocked_state)
                    self._setup_corresponding_layers(self._path_obstacles[obstacle], unlock=True)

    def _save_custom_open_street_director(self, street_director_proto, writer):
        group_ids = []
        tags = []
        tag_status = []
        clear_progress = []
        for (group_id, path_obstacle_data) in self._obstacle_status.items():
            if group_id == self._current_travel_group_id:
                pass
            else:
                for (tag, status, progress) in path_obstacle_data:
                    group_ids.append(group_id)
                    tags.append(tag)
                    tag_status.append(status)
                    clear_progress.append(progress)
        if self._current_travel_group_id is None:
            return
        for (path_obstacle, tag) in self._path_obstacles.items():
            group_ids.append(self._current_travel_group_id)
            tags.append(tag)
            tag_status.append(self._get_tag_status(path_obstacle))
            clear_progress.append(path_obstacle.get_stat_value(self.path_clearing_commodity))
        writer.write_uint64s(GROUP_TOKEN, group_ids)
        writer.write_uint64s(TAG_TOKEN, tags)
        writer.write_uint64s(TAG_STATUS_TOKEN, tag_status)
        writer.write_floats(CLEAR_PROGRESS_TOKEN, clear_progress)
        writer.write_uint64(CURRENT_TEMPLE_ID, self._current_temple_id)
        writer.write_uint32(TEMPLE_STATE, self._temple_state)
        writer.write_uint64(LAST_TIME_SAVED, services.time_service().sim_now.absolute_ticks())
        self._save_treasure_chest_data(writer)

    def _get_tag_status(self, path_obstacle):
        if path_obstacle.state_value_active(self.permanently_blocked_state):
            return JungleOpenStreetDirector.PATH_UNAVAILABLE
        if path_obstacle.state_value_active(self.path_unlocked_state):
            return JungleOpenStreetDirector.PATH_UNLOCKED
        return JungleOpenStreetDirector.PATH_LOCKED

    def _load_custom_open_street_director(self, street_director_proto, reader):
        if reader is None:
            return
        travel_group_manager = services.travel_group_manager()
        group_ids = reader.read_uint64s(GROUP_TOKEN, [])
        tags = reader.read_uint64s(TAG_TOKEN, [])
        tag_status = reader.read_uint64s(TAG_STATUS_TOKEN, [])
        clear_progress = reader.read_floats(CLEAR_PROGRESS_TOKEN, 0)
        self._current_temple_id = reader.read_uint64(CURRENT_TEMPLE_ID, 0)
        self._temple_state = reader.read_uint32(TEMPLE_STATE, self.TEMPLE_STATE_NEEDS_RESET)
        last_time_saved = reader.read_uint64(LAST_TIME_SAVED, 0)
        for (index, group_id) in enumerate(group_ids):
            if not travel_group_manager.get(group_id):
                pass
            else:
                if group_id not in self._obstacle_status:
                    self._obstacle_status[group_id] = []
                path_obstacles = self._obstacle_status[group_id]
                path_obstacles.append((tags[index], tag_status[index], clear_progress[index]))
        self._last_time_saved = DateAndTime(last_time_saved)
        self._load_treasure_chest_data(reader)

    @property
    def current_temple_id(self):
        return self._current_temple_id

    def get_next_temple_id(self):
        if self._temple_state == self.TEMPLE_STATE_RESET:
            return self._current_temple_id

    def reset_temple(self, new_id=None, force=False):
        if self._temple_state == self.TEMPLE_STATE_COMPLETE and not force:
            self._lock_temple_obstacle()
            self._update_temple_lock_commodity()
        self._current_temple_id = self._get_new_temple_id(new_id=new_id)
        self._temple_state = self.TEMPLE_STATE_RESET
        self._update_temple_id_for_client()

    def set_temple_in_progress(self):
        self._temple_state = self.TEMPLE_STATE_IN_PROGRESS

    def set_temple_complete(self):
        self._temple_state = self.TEMPLE_STATE_COMPLETE

    def _set_temple_obstacle_state(self, state_value):
        obstacle = self._get_temple_entrance_obstacle()
        if obstacle is not None:
            obstacle.set_state(state_value.state, state_value)

    def _get_temple_entrance_obstacle(self):
        obstacle = services.object_manager().get_objects_matching_tags((self.TEMPLE_PATH_OBSTACLE,))
        if len(obstacle) != 1:
            logger.error('There should only be one Temple Entrance Path Obstacle. Found {} instead.', len(obstacle), owner='trevor')
            return
        return next(iter(obstacle))

    def _lock_temple_obstacle(self):
        self._set_temple_obstacle_state(self.TEMPLE_PATH_OBSTACLE_LOCK_STATE)

    def _unlock_temple_obstacle(self):
        self._set_temple_obstacle_state(self.TEMPLE_PATH_OBSTACLE_UNLOCK_STATE)

    def _get_new_temple_id(self, new_id=None):
        temples = list(TempleTuning.TEMPLES.keys())
        if new_id is not None and new_id in temples and new_id != self._current_temple_id:
            return new_id
        if self._current_temple_id is not None:
            temples.remove(self._current_temple_id)
        return random.choice(temples)

    def _update_temple_id_for_client(self):
        for proto in services.get_persistence_service().zone_proto_buffs_gen():
            if proto.lot_description_id == TempleTuning.TEMPLE_LOT_DESCRIPTION:
                proto.pending_house_desc_id = self._current_temple_id

    def _save_treasure_chest_data(self, writer):
        group_ids = []
        obj_ids = []
        status_ids = []
        for (group_id, treasure_chest_data) in self._treasure_chest_status.items():
            if group_id == self._current_travel_group_id:
                pass
            else:
                for (obj_id, curr_status) in treasure_chest_data:
                    group_ids.append(group_id)
                    obj_ids.append(obj_id)
                    status_ids.append(curr_status)
        if self._current_travel_group_id is None:
            return
        for chest in services.object_manager().get_objects_matching_tags((self.treasure_chest_tag,)):
            if chest.is_on_active_lot():
                pass
            else:
                group_ids.append(self._current_travel_group_id)
                obj_ids.append(chest.id)
                status_ids.append(self._get_treasure_chest_status(chest))
        writer.write_uint64s(TREASURE_CHEST_GROUP, group_ids)
        writer.write_uint64s(TREASURE_CHEST_ID, obj_ids)
        writer.write_uint64s(TREASURE_CHEST_STATUS, status_ids)

    def _get_treasure_chest_status(self, chest):
        if chest.state_value_active(self.treasure_chest_open_state):
            return JungleOpenStreetDirector.TREASURE_CHEST_OPEN
        return JungleOpenStreetDirector.TREASURE_CHEST_CLOSED

    def _load_treasure_chest_data(self, reader):
        if reader is None:
            return
        travel_group_manager = services.travel_group_manager()
        group_ids = reader.read_uint64s(TREASURE_CHEST_GROUP, [])
        obj_ids = reader.read_uint64s(TREASURE_CHEST_ID, [])
        status = reader.read_uint64s(TREASURE_CHEST_STATUS, [])
        for (index, group_id) in enumerate(group_ids):
            if not travel_group_manager.get(group_id):
                pass
            else:
                if group_id not in self._treasure_chest_status:
                    self._treasure_chest_status[group_id] = []
                treasure_chest = self._treasure_chest_status[group_id]
                treasure_chest.append((obj_ids[index], status[index]))
