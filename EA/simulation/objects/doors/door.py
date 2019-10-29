from apartments.inactive_apartment_door_lock import InactiveApartmentDoorLockDatafrom interactions.base.immediate_interaction import ImmediateSuperInteractionfrom objects.components.portal_locking_enums import LockType, LockPriorityfrom objects.doors.door_dynamic_spawn_point import InactiveApartmentDoorDynamicSpawnPointfrom objects.doors.door_tuning import DoorTuningfrom objects.game_object import GameObjectfrom sims4.tuning.tunable import Tunableimport services
class Door(GameObject):
    INACTIVE_APARTMENT_DOOR_PORTAL_COST = 9999
    INSTANCE_TUNABLES = {'is_door_portal': Tunable(description='\n            Is this a valid door.\n            Should be false for arches, gates and other non lockable door portals.\n            ', tunable_type=bool, default=False)}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._back_spawn_point = None

    def on_remove(self):
        services.get_door_service().on_door_removed(self)
        self._destroy_back_spawn_point()
        super().on_remove()

    def get_door_positions(self):
        (front_location, back_location) = self.get_single_portal_locations()
        return (front_location.position if front_location is not None else None, back_location.position if back_location is not None else None)

    def swap_there_and_back(self):
        for portal_pair in self.get_portal_pairs():
            portal_there = self.get_portal_by_id(portal_pair.there)
            portal_back = self.get_portal_by_id(portal_pair.back)
            portal_there.swap_there_and_back()
            for sim in self.get_disallowed_sims():
                if self.portal_locking_component.has_bidirectional_lock(sim):
                    pass
                else:
                    routing_context = sim.get_routing_context()
                    routing_context.lock_portal(portal_there.there)
                    routing_context.unlock_portal(portal_there.back)

    def set_front_door_status(self, status):
        state = DoorTuning.FRONT_DOOR_STATE.enabled.state
        if status:
            self.set_state(state, DoorTuning.FRONT_DOOR_STATE.enabled)
        else:
            self.set_state(state, DoorTuning.FRONT_DOOR_STATE.disabled)

    def set_front_door_availability(self, status):
        state = DoorTuning.FRONT_DOOR_AVAILABILITY_STATE.enabled.state
        if status:
            self.set_state(state, DoorTuning.FRONT_DOOR_AVAILABILITY_STATE.enabled)
        else:
            self.set_state(state, DoorTuning.FRONT_DOOR_AVAILABILITY_STATE.disabled)

    def set_inactive_apartment_door_status(self, status):
        state = DoorTuning.INACTIVE_APARTMENT_DOOR_STATE.enabled.state
        if status:
            self.set_state(state, DoorTuning.INACTIVE_APARTMENT_DOOR_STATE.enabled)
            self._create_back_spawn_point()
            for portal_pair in self.get_portal_pairs():
                self.set_portal_cost_override(portal_pair.there, Door.INACTIVE_APARTMENT_DOOR_PORTAL_COST)
            self.add_lock_data(InactiveApartmentDoorLockData(self))
        else:
            self.set_state(state, DoorTuning.INACTIVE_APARTMENT_DOOR_STATE.disabled)
            self._destroy_back_spawn_point()
            for portal_pair in self.get_portal_pairs():
                self.clear_portal_cost_override(portal_pair.there)
            self.remove_locks(lock_type=LockType.INACTIVE_APARTMENT_DOOR, lock_priority=LockPriority.SYSTEM_LOCK)

    def _create_back_spawn_point(self):
        if self._back_spawn_point is None:
            self._back_spawn_point = InactiveApartmentDoorDynamicSpawnPoint(self, is_front=False)
            services.current_zone().add_dynamic_spawn_point(self._back_spawn_point)

    def _destroy_back_spawn_point(self):
        if self._back_spawn_point is not None:
            services.current_zone().remove_dynamic_spawn_point(self._back_spawn_point)
            self._back_spawn_point = None

    def get_back_spawn_point(self):
        return self._back_spawn_point

    def get_gsi_portal_items(self, key_name, value_name):
        door_items_list = super().get_gsi_portal_items(key_name, value_name)
        if self.has_state(DoorTuning.FRONT_DOOR_STATE.enabled.state):
            door_items_list.append({value_name: str(self.get_state(DoorTuning.FRONT_DOOR_STATE.enabled.state)), key_name: 'Front Door State'})
        if self.has_state(DoorTuning.FRONT_DOOR_AVAILABILITY_STATE.enabled.state):
            door_items_list.append({value_name: str(self.get_state(DoorTuning.FRONT_DOOR_AVAILABILITY_STATE.enabled.state)), key_name: 'Front Door Availability State'})
        if self.has_state(DoorTuning.INACTIVE_APARTMENT_DOOR_STATE.enabled.state):
            door_items_list.append({value_name: str(self.get_state(DoorTuning.INACTIVE_APARTMENT_DOOR_STATE.enabled.state)), key_name: 'Inactive Apartment Door State'})
        return door_items_list

class SetFrontDoorImmediateInteraction(ImmediateSuperInteraction):

    def _run_interaction_gen(self, timeline):
        services.get_door_service().set_as_front_door(self.target)
