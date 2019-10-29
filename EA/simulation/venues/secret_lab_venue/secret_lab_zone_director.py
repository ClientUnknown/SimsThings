from enum_lib import Enumfrom event_testing.register_test_event_mixin import RegisterTestEventMixinfrom event_testing.resolver import SingleActorAndObjectResolverfrom event_testing.test_events import TestEventfrom interactions import ParticipantTypefrom interactions.utils.loot_ops import LockDoor, UnlockDoorfrom objects.components.state import ObjectStateValuefrom sims.sim_spawner_service import SimSpawnReasonfrom sims4.resources import Typesfrom sims4.tuning.tunable import TunableList, TunableReference, TunableTuplefrom situations.service_npcs.modify_lot_items_tuning import TunableObjectMatchesDefinitionOrTagTestfrom situations.situation_complex import TunableInteractionOfInterestfrom venues.scheduling_zone_director import SchedulingZoneDirectorMixinfrom zone_director import ZoneDirectorBase, _ZoneSavedSimOpimport build_buyimport cameraimport servicesimport sims4.loglogger = sims4.log.Logger('Secret Lab', default_owner='jdimailig')SAVE_LAST_REVEALED_PLEX = 'last_revealed_plex'
class SecretLabCommand(Enum):
    RevealNextSection = 'RevealNextSection'
    RevealAllSections = 'RevealAllSections'
    ResetLab = 'ResetLab'

class SecretLabZoneDirector(RegisterTestEventMixin, SchedulingZoneDirectorMixin, ZoneDirectorBase):
    INSTANCE_TUNABLES = {'section_doors': TunableList(description='\n            An ordered set of doors, each of which unlocks a section of the lab\n            to explore.\n            ', tunable=TunableReference(manager=services.get_instance_manager(Types.OBJECT)), unique_entries=True), 'door_lock_operations': TunableTuple(description='\n            These operations are applied to doors that should be locked\n            based on the progress into the zone.\n            ', object_state=ObjectStateValue.TunableReference(description='\n                An object state that should be set on the door when locked.\n                '), lock_data=LockDoor.TunableFactory(description='\n                The LockDoor loot to run on the doors in the lab to lock them.\n                ')), 'door_unlock_operations': TunableTuple(description='\n            These operations are applied to doors that should be unlocked\n            based on the progress into the zone.\n            ', object_state=ObjectStateValue.TunableReference(description='\n                An object state that should be set on the door when unlocked.\n                '), lock_data=UnlockDoor.TunableFactory(description='\n                The UnlockDoor loot to run on the doors when they should be unlocked.\n                ')), 'reveal_interactions': TunableInteractionOfInterest(description='\n            Interactions that, when run on a door, reveal the plex associated \n            to the interacted door.\n            '), 'object_commodities_to_fixup_on_load': TunableList(description='\n            Normally object commodities retain their previously saved value on \n            load and do not simulate the decay up to the current time.\n            This list allows specific objects to update commodities based off\n            passage of time if time had elapsed between load and the last time\n            the zone was saved.\n            ', tunable=TunableTuple(commodity=TunableReference(description='\n                    The commodity to fix up if time elapsed since zone was last saved.\n                    ', manager=services.get_instance_manager(sims4.resources.Types.STATISTIC), class_restrictions='Commodity'), object_test=TunableObjectMatchesDefinitionOrTagTest(description='\n                    Test whether or not an object applies for this fixup.\n                    ')))}

    def __init__(self):
        super().__init__()
        self._revealed_plex = 0
        self._plex_door_map = self._generate_plex_door_map()
        self._reset_lab_data()
        self._command_handlers = {SecretLabCommand.ResetLab: self._reset_all_sections, SecretLabCommand.RevealAllSections: self._reveal_all_sections, SecretLabCommand.RevealNextSection: self._reveal_next_section}

    def on_startup(self):
        super().on_startup()
        self._register_test_event_for_keys(TestEvent.InteractionStart, self.reveal_interactions.custom_keys_gen())
        self._register_test_event_for_keys(TestEvent.InteractionComplete, self.reveal_interactions.custom_keys_gen())

    def on_shutdown(self):
        self._unregister_for_all_test_events()
        super().on_shutdown()

    def on_loading_screen_animation_finished(self):
        super().on_loading_screen_animation_finished()
        active_sim = services.get_active_sim()
        if active_sim is None:
            return
        if active_sim.is_on_active_lot():
            return
        camera.focus_on_sim(services.get_active_sim())

    def on_cleanup_zone_objects(self):
        super().on_cleanup_zone_objects()
        current_zone = services.current_zone()
        if self.object_commodities_to_fixup_on_load:
            time_of_last_zone_save = current_zone.time_of_last_save()
            for obj in list(services.object_manager().values()):
                if not obj.is_on_active_lot():
                    pass
                else:
                    for commodity_fixup in self.object_commodities_to_fixup_on_load:
                        if not commodity_fixup.object_test(objects=(obj,)):
                            pass
                        else:
                            fixup_commodity = obj.get_stat_instance(commodity_fixup.commodity)
                            if fixup_commodity is not None:
                                fixup_commodity.update_commodity_to_time(time_of_last_zone_save, update_callbacks=True)
        if current_zone.time_has_passed_in_world_since_zone_save() and self._should_reset_progress_on_load():
            self._revealed_plex = 0
        self._update_locks_and_visibility()

    def _determine_zone_saved_sim_op(self):
        if self._should_reset_progress_on_load():
            return _ZoneSavedSimOp.CLEAR
        return _ZoneSavedSimOp.MAINTAIN

    def _on_clear_zone_saved_sim(self, sim_info):
        if sim_info.is_selectable:
            self._request_spawning_of_sim_at_spawn_point(sim_info, SimSpawnReason.ACTIVE_HOUSEHOLD)
            return
        self._send_sim_home(sim_info)

    def _save_custom_zone_director(self, zone_director_proto, writer):
        writer.write_uint32(SAVE_LAST_REVEALED_PLEX, self._revealed_plex)
        super()._save_custom_zone_director(zone_director_proto, writer)

    def _load_custom_zone_director(self, zone_director_proto, reader):
        if reader is not None:
            self._revealed_plex = reader.read_uint32(SAVE_LAST_REVEALED_PLEX, None)
        super()._load_custom_zone_director(zone_director_proto, reader)

    def handle_event(self, sim_info, event, resolver):
        interaction_start = event == TestEvent.InteractionStart
        interaction_complete = event == TestEvent.InteractionComplete
        if resolver(self.reveal_interactions):
            door = resolver.get_participant(ParticipantType.Object)
            try:
                plex_to_unlock = self.section_doors.index(door.definition) + 1
            except ValueError:
                logger.error('Ran interaction {} on unexpected door {}', resolver.interaction, door)
                plex_to_unlock = 0
            zone_id = services.current_zone_id()
            if interaction_complete:
                self._handle_door_state(sim_info, door, True)
            else:
                build_buy.set_plex_visibility(zone_id, plex_to_unlock, True)
                self._revealed_plex = max(plex_to_unlock, self._revealed_plex)

    def handle_command(self, command:SecretLabCommand, **kwargs):
        if command in self._command_handlers:
            self._command_handlers[command](**kwargs)

    def _should_reset_progress_on_load(self):
        current_zone = services.current_zone()
        return current_zone.active_household_changed_between_save_and_load() or current_zone.time_has_passed_in_world_since_zone_save()

    def _generate_plex_door_map(self):
        plex_door_map = {}
        obj_mgr = services.object_manager()
        for (i, door_def) in enumerate(self.section_doors, 1):
            door = next(iter(obj_mgr.get_objects_of_type_gen(door_def)), None)
            if door is None:
                logger.error('Unable to find the door {} on lot to unlock plex {}', door_def, i)
            else:
                plex_door_map[i] = door
        return plex_door_map

    def _handle_door_state(self, sim_info, door, set_open):
        operations = self.door_unlock_operations if set_open else self.door_lock_operations
        resolver = SingleActorAndObjectResolver(sim_info, door, self)
        operations.lock_data.apply_to_resolver(resolver)
        state_value = operations.object_state
        door.set_state(state_value.state, state_value, force_update=True)

    def _update_locks_and_visibility(self):
        zone_id = services.current_zone_id()
        active_sim_info = services.active_sim_info()
        for i in range(1, len(self.section_doors) + 1):
            reveal = i <= self._revealed_plex
            build_buy.set_plex_visibility(zone_id, i, reveal)
            door = self._plex_door_map.get(i, None)
            if door is None:
                pass
            else:
                self._handle_door_state(active_sim_info, door, reveal)

    def _reset_lab_data(self):
        self._revealed_plex = 0

    def _reveal_next_section(self):
        self._revealed_plex = min(len(self.section_doors), self._revealed_plex + 1)
        self._update_locks_and_visibility()

    def _reveal_all_sections(self):
        self._revealed_plex = len(self.section_doors)
        self._update_locks_and_visibility()

    def _reset_all_sections(self):
        self._reset_lab_data()
        self._update_locks_and_visibility()
