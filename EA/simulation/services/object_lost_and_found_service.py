from _collections import defaultdictfrom protocolbuffers import FileSerialization_pb2from protocolbuffers import GameplaySaveData_pb2import sims4from build_buy import HouseholdInventoryFlagsfrom date_and_time import DateAndTimefrom distributor.rollback import ProtocolBufferRollbackfrom objects import ALL_HIDDEN_REASONSfrom objects.object_enums import ItemLocationfrom objects.object_manager import ObjectManagerfrom objects.system import create_objectfrom sims4.localization import TunableLocalizedStringFactory, LocalizationHelperTuningfrom sims4.service_manager import Servicefrom sims4.utils import classpropertyfrom ui.ui_dialog_notification import UiDialogNotificationimport build_buyimport persistence_error_typesimport serviceslogger = sims4.log.Logger('Object Lost and Found Service')
class ObjectLostAndFoundService(Service):
    STREET_UNKNOWN = 0
    OBJECTS_RETURN_MESSAGE_DIALOG = UiDialogNotification.TunableFactory(description='\n        The string that appears when an object is returned via the lost and\n        found service.\n        Params:\n            0 - String Bulleted list of objects returned.\n            \n        Example: The following items were returned to the inventory of their \n        owner via the lost and found.\n{0.String}\n        ')
    FAMILY_NAME_HEADER = TunableLocalizedStringFactory(description='\n        The string used to display the family that has received an object back\n        because of the lost and found service.\n        \n        0 - Family Name as a string.\n        ')

    class ObjectLocator:

        def __init__(self, zone_id, open_street_id, object_id, sim_id, household_id, time_before_lost, time_stamp=None):
            self.zone_id = zone_id
            self.open_street_id = open_street_id
            self.object_data = None
            self.object_id = object_id
            self.sim_id = sim_id
            self.household_id = household_id
            self.time_before_lost = time_before_lost
            self.time_stamp = services.time_service().sim_now if time_stamp is None else time_stamp

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._clear()

    def load(self, **_):
        self._clear()
        save_slot_data_msg = services.get_persistence_service().get_save_slot_proto_buff()
        if not save_slot_data_msg.gameplay_data.HasField('object_lost_and_found'):
            return
        object_lost_and_found = save_slot_data_msg.gameplay_data.object_lost_and_found
        for object_locators in object_lost_and_found.locators:
            object_data = FileSerialization_pb2.ObjectData()
            object_data.ParseFromString(object_locators.object)
            if object_data is None:
                logger.error('Trying to load a locator with no object data. \n                zone_id: {}, open_street_id: {}, sim_id: {}, household_id: {}, \n                time_before_lost: {}, time_stamp: {}', object_locators.zone_id, object_locators.open_street_id, object_locators.sim_id, object_locators.household_id, object_locators.time_before_lost, object_locators.time_stamp.absolute_ticks())
            else:
                locator = self._raw_add_object_data(object_locators.zone_id, object_locators.open_street_id, object_data.object_id, object_locators.sim_id, object_locators.household_id, object_locators.time_before_lost, DateAndTime(object_locators.time_stamp))
                locator.object_data = object_data
        for clone in object_lost_and_found.clones_to_delete:
            self.add_clone_id(clone.zone_id, clone.open_street_id, clone.object_id)

    def save(self, object_list=None, zone_data=None, open_street_data=None, store_travel_group_placed_objects=False, save_slot_data=None):
        self.update_zone_object_locators()
        proto_object_locators = GameplaySaveData_pb2.PersistableObjectLostAndFound()
        for entry in self._object_locators:
            if entry.object_data is None:
                logger.error('Trying to save a locator with no object data. \n                zone_id: {}, open_street_id: {}, sim_id: {}, household_id: {}, \n                time_before_lost: {}, time_stamp: {}', entry.zone_id, entry.open_street_id, entry.sim_id, entry.household_id, entry.time_before_lost, entry.time_stamp.absolute_ticks())
            else:
                with ProtocolBufferRollback(proto_object_locators.locators) as locator:
                    locator.object = entry.object_data.SerializeToString()
                    locator.zone_id = entry.zone_id
                    locator.open_street_id = entry.open_street_id
                    locator.sim_id = entry.sim_id
                    locator.household_id = entry.household_id
                    locator.time_before_lost = entry.time_before_lost
                    locator.time_stamp = entry.time_stamp.absolute_ticks()
        for (zone_id, objects) in self._clones_to_delete_by_zone.items():
            for object_id in objects:
                with ProtocolBufferRollback(proto_object_locators.clones_to_delete) as clone:
                    clone.zone_id = zone_id
                    clone.object_id = object_id
        save_slot_data.gameplay_data.object_lost_and_found = proto_object_locators

    @classproperty
    def save_error_code(cls):
        return persistence_error_types.ErrorCodes.SERVICE_SAVE_FAILED_OBJECT_LOST_AND_FOUND_SERVICE

    def on_cleanup_zone_objects(self, client):
        self.return_lost_objects()
        self.delete_clones()

    def on_zone_unload(self):
        self.update_zone_object_locators()

    @property
    def registered_object_locators(self):
        return self._object_locators

    @property
    def clones_to_delete_by_zone(self):
        return self._clones_to_delete_by_zone

    @property
    def clones_to_delete_by_street(self):
        return self._clones_to_delete_by_street

    def _clear(self):
        self._object_locators = []
        self._clones_to_delete_by_zone = {}
        self._clones_to_delete_by_street = {}

    def _any_household_member_on_lot(self, zone_id, household_id, ignore_sim_id):
        household = services.household_manager().get(household_id)
        if household is not None:
            if household.home_zone_id == zone_id:
                return True
            for sim_info in household.sim_info_gen():
                if sim_info.id != ignore_sim_id and sim_info.zone_id == zone_id:
                    return True
        return False

    def _return_lost_object(self, locator):
        sim_info = services.sim_info_manager().get(locator.sim_id)
        object_id = locator.object_data.object_id
        if sim_info is not None and sim_info.is_instanced():
            if sim_info.zone_id != locator.zone_id and not self._any_household_member_on_lot(locator.zone_id, sim_info.household.id, sim_info.id):
                sim = sim_info.get_sim_instance(allow_hidden_flags=ALL_HIDDEN_REASONS)
                if sim is None:
                    return (None, None)
                obj = create_object(locator.object_data.guid, loc_type=ItemLocation.SIM_INVENTORY)
                if obj is not None:
                    obj.attributes = locator.object_data.SerializeToString()
                    obj.scale = locator.object_data.scale
                    if sim.inventory_component.player_try_add_object(obj):
                        obj.update_ownership(sim_info)
                        self.remove_object(object_id)
                        self.add_clone_id(locator.zone_id, locator.open_street_id, object_id)
                        return (obj, sim)
                    obj.destroy(source=self, cause='Failed to add object to Sim Inv, try later')
                    return (None, None)
        elif sim_info is None and not self._any_household_member_on_lot(locator.zone_id, locator.household_id, locator.sim_id):
            obj = create_object(locator.object_data.guid, loc_type=ItemLocation.HOUSEHOLD_INVENTORY)
            if obj is not None:
                obj.attributes = locator.object_data.SerializeToString()
                obj.scale = locator.object_data.scale
                if build_buy.move_object_to_household_inventory(obj, HouseholdInventoryFlags.FORCE_OWNERSHIP):
                    self.remove_object(object_id)
                    self.add_clone_id(locator.zone_id, locator.open_street_id, object_id)
                    return (obj, locator.household_id)
        return (None, None)

    def return_lost_objects(self):
        returned_objects = defaultdict(list)
        current_zone = services.current_zone()
        current_zone_id = services.current_zone_id()
        current_open_street_id = current_zone.open_street_id
        active_household = services.active_household()
        for locator in list(self._object_locators):
            if locator.zone_id != current_zone_id and locator.open_street_id != current_open_street_id:
                elapsed_time = services.time_service().sim_now - locator.time_stamp
                if elapsed_time.in_minutes() < locator.time_before_lost:
                    pass
                elif locator.object_data is None:
                    self.remove_object(locator.object_id)
                else:
                    (obj_returned, owner) = self._return_lost_object(locator)
                    if obj_returned is not None and owner is not None:
                        if isinstance(owner, int):
                            if owner == active_household.id:
                                returned_objects[owner].append(obj_returned)
                                if owner.household is active_household:
                                    returned_objects[owner].append(obj_returned)
                        elif owner.household is active_household:
                            returned_objects[owner].append(obj_returned)
        if not returned_objects:
            return
        returned_objects_string = None
        household_manager = services.household_manager()
        for (owner, objects) in returned_objects.items():
            if isinstance(owner, int):
                household = household_manager.get(owner)
                header = ObjectLostAndFoundService.FAMILY_NAME_HEADER(household.name)
                next_string = LocalizationHelperTuning.get_bulleted_list(header, (LocalizationHelperTuning.get_object_name(obj) for obj in objects))
            else:
                next_string = LocalizationHelperTuning.get_bulleted_list(LocalizationHelperTuning.get_sim_name(owner), (LocalizationHelperTuning.get_object_name(obj) for obj in objects))
            if returned_objects_string is None:
                returned_objects_string = next_string
            else:
                returned_objects_string = LocalizationHelperTuning.NEW_LINE_LIST_STRUCTURE(returned_objects_string, next_string)
        dialog = ObjectLostAndFoundService.OBJECTS_RETURN_MESSAGE_DIALOG(services.active_sim_info())
        dialog.show_dialog(additional_tokens=(returned_objects_string,))

    def delete_clones(self):
        zone = services.current_zone()
        zone_id = zone.id
        open_street_id = zone.open_street_id
        object_manager = zone.object_manager

        def delete_clones_for_data(data, current_key):
            if current_key in list(data.keys()):
                for object_id in list(data[current_key]):
                    obj = object_manager.get(object_id)
                    if obj is not None:
                        obj.destroy(source=self, cause='Removing lost object clone on zone load')
                    self.remove_clone_id(object_id)

        delete_clones_for_data(self._clones_to_delete_by_zone, zone_id)
        delete_clones_for_data(self._clones_to_delete_by_street, open_street_id)

    def add_clone_id(self, zone_id, open_street_id, object_id):
        if zone_id not in self._clones_to_delete_by_zone:
            self._clones_to_delete_by_zone[zone_id] = set()
        self._clones_to_delete_by_zone[zone_id].add(object_id)
        if open_street_id != ObjectLostAndFoundService.STREET_UNKNOWN:
            if open_street_id not in self._clones_to_delete_by_street:
                self._clones_to_delete_by_street[open_street_id] = set()
            self._clones_to_delete_by_street[open_street_id].add(object_id)

    def remove_clone_id(self, object_id):

        def remove_from(data):
            for (key, objects) in data.items():
                if object_id in objects:
                    objects.remove(object_id)
                    del data[key]
                    break

        remove_from(self._clones_to_delete_by_zone)
        remove_from(self._clones_to_delete_by_street)

    def _raw_add_object_data(self, zone_id, open_street_id, object_id, sim_id, household_id, time_before_lost, time_stamp=None):
        locator = ObjectLostAndFoundService.ObjectLocator(zone_id, open_street_id, object_id, sim_id, household_id, time_before_lost, time_stamp)
        self._object_locators.append(locator)
        return locator

    def add_game_object(self, zone_id, object_id, sim_id, household_id, time_before_lost):
        self.remove_clone_id(object_id)
        self.remove_object(object_id)
        return self._raw_add_object_data(zone_id, ObjectLostAndFoundService.STREET_UNKNOWN, object_id, sim_id, household_id, time_before_lost) is not None

    def update_zone_object_locators(self):
        current_zone = services.current_zone()
        current_zone_id = services.current_zone_id()
        object_manager = current_zone.object_manager
        current_open_street_id = current_zone.open_street_id
        for locator in list(self._object_locators):
            if locator.zone_id != current_zone_id:
                pass
            else:
                obj = object_manager.get(locator.object_id)
                if obj is not None:
                    locator.open_street_id = ObjectLostAndFoundService.STREET_UNKNOWN if current_zone.lot.is_position_on_lot(obj.position) else current_open_street_id
                    object_list = FileSerialization_pb2.ObjectList()
                    open_street_object_locators = FileSerialization_pb2.ObjectList()
                    locator.object_data = ObjectManager.save_game_object(obj, object_list, open_street_object_locators)
                    if locator.object_data is None:
                        self.remove_object(locator.object_id)
                        self.remove_object(locator.object_id)
                else:
                    self.remove_object(locator.object_id)

    def remove_object(self, object_id):
        for locator in self._object_locators:
            if locator.object_id == object_id:
                self._object_locators.remove(locator)
                return True
        return False
