from _collections import defaultdictimport itertoolsimport randomfrom event_testing.resolver import SingleActorAndObjectResolver, SingleSimResolverfrom event_testing.test_events import TestEventfrom objects import ALL_HIDDEN_REASONSfrom sims4.geometry import test_point_in_polygonfrom temple.temple_tuning import TempleTuningfrom venues.scheduling_zone_director import SchedulingZoneDirectorimport build_buyimport cameraimport objects.systemimport servicesimport sims4.loglogger = sims4.log.Logger('Temple Zone Director', default_owner='trevor')
class TempleRoom:

    def __init__(self):
        self.gate = None
        self.trigger_object = None
        self.trigger_interaction = None
SAVE_DATA_TEMPLE_ID = 'temple_id'SAVE_DATA_CURRENT_ROOM = 'temple_current_room'SAVE_DATA_ROOMS = 'temple_rooms'SAVE_DATA_NEEDS_RESET = 'temple_needs_reset'TEMPLE_EVENTS = (TestEvent.SimActiveLotStatusChanged, TestEvent.InteractionComplete)
class TempleZoneDirector(SchedulingZoneDirector):

    def __init__(self):
        super().__init__()
        self._reset_temple_data()

    def _reset_temple_data(self):
        self._temple_id = None
        self._temple_data = None
        self._current_room = None
        self._rooms = None

    @property
    def current_temple_id(self):
        return self._temple_id

    @property
    def current_room(self):
        return self._current_room

    @property
    def room_count(self):
        return len(self._rooms)

    @property
    def room_data(self):
        return self._rooms

    def on_startup(self):
        super().on_startup()
        services.get_event_manager().register(self, TEMPLE_EVENTS)

    def on_shutdown(self):
        super().on_shutdown()
        services.get_event_manager().unregister(self, TEMPLE_EVENTS)

    def on_cleanup_zone_objects(self):
        super().on_cleanup_zone_objects()
        next_temple_id = self.open_street_director.get_next_temple_id()
        if next_temple_id is not None:
            self._reset_temple_data()
        if self._temple_id is None:
            if next_temple_id is None:
                logger.error("No temple_id was loaded for this temple and the Open Street Director doesn't have an ID for us. This temple will not function correctly.")
                return
            self._temple_id = next_temple_id
            self._prepare_temple_data()
            object_manager = services.object_manager()
            zone_id = services.current_zone_id()
            self._setup_gates(object_manager, zone_id)
            self._setup_traps(object_manager, zone_id)
            self._setup_rooms_visibility()
            self.open_street_director.set_temple_in_progress()
            self._require_setup = True
        self._apply_enter_lot_loot()

    def _apply_enter_lot_loot(self):
        if self._temple_data.enter_lot_loot:
            arrival_spawn_point = services.current_zone().active_lot_arrival_spawn_point
            for sim in services.sim_info_manager().instanced_sims_gen(allow_hidden_flags=ALL_HIDDEN_REASONS):
                if not sim.is_on_active_lot():
                    if arrival_spawn_point is not None and test_point_in_polygon(sim.intended_position, arrival_spawn_point.get_footprint_polygon()):
                        sim_resolver = SingleSimResolver(sim.sim_info)
                        for loot in self._temple_data.enter_lot_loot:
                            loot.apply_to_resolver(sim_resolver)
                sim_resolver = SingleSimResolver(sim.sim_info)
                for loot in self._temple_data.enter_lot_loot:
                    loot.apply_to_resolver(sim_resolver)

    def _has_enter_exit_lot_loot(self):
        if self._temple_data is None:
            return False
        return self._temple_data.enter_lot_loot or self._temple_data.exit_lot_loot

    def handle_event(self, sim_info, event, resolver):
        if event == TestEvent.SimActiveLotStatusChanged and self._has_enter_exit_lot_loot():
            sim_resolver = SingleSimResolver(sim_info)
            loots = self._temple_data.enter_lot_loot if resolver.get_resolved_arg('on_active_lot') else self._temple_data.exit_lot_loot
            for loot in loots:
                loot.apply_to_resolver(sim_resolver)
        elif event == TestEvent.InteractionComplete and resolver(TempleTuning.CHEST_OPEN_INTEARCTION):
            object_manager = services.object_manager()
            rare_chests = object_manager.get_objects_matching_tags((TempleTuning.CHEST_TAG,))
            chest_count = len(rare_chests)
            if chest_count == 0:
                logger.error('Starting up a temple that has no rare chests. This temple will not work correctly. Temples should have exactly 1 rare chest.')
            elif chest_count > 1:
                logger.error('Starting up a temple that has more than 1 rare chest. Temples should have exactly 1 rare chest. A random rare chest will be chosen as the final chest.')
            if rare_chests:
                final_chest = next(iter(rare_chests))
            if final_chest.state_value_active(TempleTuning.CHEST_OPEN_STATE):
                self.open_street_director.set_temple_complete()

    def _save_custom_zone_director(self, zone_director_proto, writer):
        temple_room_data = list(itertools.chain.from_iterable((room.gate.id if room.gate is not None else 0, room.trigger_object.id if room.trigger_object is not None else 0, room.trigger_interaction.guid64 if room.trigger_interaction is not None else 0) for room in self._rooms))
        writer.write_uint64(SAVE_DATA_TEMPLE_ID, self._temple_id)
        writer.write_uint64s(SAVE_DATA_ROOMS, temple_room_data)
        writer.write_uint32(SAVE_DATA_CURRENT_ROOM, self._current_room)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        if reader is not None:
            self._temple_id = reader.read_uint64(SAVE_DATA_TEMPLE_ID, None)
            self._prepare_temple_data()
            self._current_room = reader.read_uint32(SAVE_DATA_CURRENT_ROOM, 0)
            temple_room_data = reader.read_uint64s(SAVE_DATA_ROOMS, [])
            object_manager = services.object_manager()
            interaction_manager = services.get_instance_manager(sims4.resources.Types.INTERACTION)
            for (i, (gate_id, trigger_object_id, trigger_interaction_id)) in enumerate(zip(temple_room_data[::3], temple_room_data[1::3], temple_room_data[2::3])):
                self._rooms[i].gate = object_manager.get(gate_id) if gate_id != 0 else None
                self._rooms[i].trigger_object = object_manager.get(trigger_object_id) if trigger_object_id != 0 else None
                self._rooms[i].trigger_interaction = interaction_manager.get(trigger_interaction_id) if trigger_interaction_id != 0 else None
            self._setup_rooms_visibility()
        super()._load_custom_zone_director(zone_director_proto, reader)

    def _prepare_temple_data(self):
        self._temple_data = TempleTuning.TEMPLES[self._temple_id]
        self._rooms = [TempleRoom() for _ in range(len(self._temple_data.rooms))]
        self._current_room = 0

    def _setup_traps(self, object_manager, zone_id):
        traps_by_room = [defaultdict() for _ in range(len(self._rooms))]
        traps = object_manager.get_objects_matching_tags((TempleTuning.TRAP_TAG,))
        for placeholder_trap in traps:
            room = build_buy.get_location_plex_id(zone_id, placeholder_trap.position, placeholder_trap.level)
            (new_trap, trigger_interactions) = self._get_random_trap(room)
            new_trap_instance = objects.system.create_object(new_trap)
            new_trap_instance.location = placeholder_trap.location
            placeholder_trap.destroy(cause='Removing placeholder trap for temple.')
            traps_by_room[room][new_trap_instance] = trigger_interactions
        for (i, traps) in enumerate(traps_by_room[:-1]):
            if traps is None or not traps.keys():
                logger.error('It appears there are rooms missing traps, or the tuning has too many rooms! Room #{}.', i)
            else:
                trigger_object = random.choice(list(traps.keys()))
                self._rooms[i].trigger_object = trigger_object
                self._rooms[i].trigger_interaction = random.choice(list(traps[trigger_object]))

    def _setup_gates(self, object_manager, zone_id):
        active_sim_info = services.active_sim_info()
        gates = object_manager.get_objects_matching_tags((TempleTuning.GATE_TAG,))
        for gate in gates:
            if not gate.state_component:
                logger.error('Trying to randomize temple gates but the gate, {},  has no state component. Ignoring it.', gate)
            else:
                (front_position, back_position) = gate.get_door_positions()
                front_plex_id = build_buy.get_location_plex_id(zone_id, front_position, gate.level)
                back_plex_id = build_buy.get_location_plex_id(zone_id, back_position, gate.level)
                if front_plex_id == 0 and back_plex_id == 0:
                    logger.error("Found a gate, {}, but it doesn't seem to have a plex on either side. Ignoring it.", gate)
                else:
                    belonging_room = min(front_plex_id, back_plex_id)
                    self._rooms[belonging_room].gate = gate
                    gate_state_value = self._get_random_gate_state(belonging_room)
                    gate_state = TempleTuning.GATE_STATE
                    if not gate.has_state(gate_state):
                        logger.error('Trying to apply a random state to a temple gate but the gate, {}, has no state value, {} for state {}.', gate, gate_state_value, gate_state)
                    else:
                        gate.set_state(gate_state, gate_state_value)
                        resolver = SingleActorAndObjectResolver(active_sim_info, gate, source=self)
                        TempleTuning.GATE_LOCK_LOOT.apply_to_resolver(resolver)

    def _get_random_gate_state(self, room_number):
        return random.choice(list(self._temple_data.rooms[room_number].gate))

    def _get_random_trap(self, room_number):
        return random.choice(list(self._temple_data.rooms[room_number].traps.items()))

    def _setup_rooms_visibility(self):
        zone_id = services.current_zone_id()
        for i in range(1, len(self._temple_data.rooms)):
            build_buy.set_plex_visibility(zone_id, i, i <= self._current_room)

    def show_room(self, room_number, show):
        if room_number >= len(self._temple_data.rooms):
            return False
        zone_id = services.current_zone_id()
        build_buy.set_plex_visibility(zone_id, room_number, show)

    def unlock_next_room(self):
        if self._current_room >= len(self._temple_data.rooms):
            return
        gate = self._rooms[self._current_room].gate
        camera.focus_on_position(gate.position)
        gate.set_state(TempleTuning.GATE_UNLOCK_STATE.state, TempleTuning.GATE_UNLOCK_STATE)
        active_sim_info = services.active_sim_info()
        resolver = SingleActorAndObjectResolver(active_sim_info, gate, source=self)
        TempleTuning.GATE_UNLOCK_LOOT.apply_to_resolver(resolver)
        self._current_room += 1
        self.show_room(self._current_room, True)
