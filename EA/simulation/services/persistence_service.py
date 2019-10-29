import collectionsimport datetimeimport functoolsfrom protocolbuffers import FileSerialization_pb2 as serialization, UI_pb2from protocolbuffers.Consts_pb2 import MSG_GAME_SAVE_COMPLETE, MSG_GAME_SAVE_LOCK_UNLOCKfrom distributor.system import Distributorfrom sims.household_telemetry import HouseholdRegionTelemetryDatafrom sims4.callback_utils import CallableListfrom sims4.localization import TunableLocalizedString, TunableLocalizedStringFactoryfrom sims4.service_manager import Servicefrom sims4.tuning.tunable import TunableRealSecond, TunableSimMinute, TunableInterval, TunableTuplefrom sims4.utils import exception_protectedimport cameraimport element_utilsimport elementsimport enumimport persistence_error_typesimport persistence_moduleimport schedulingimport servicesimport sims4.logimport telemetry_helperimport ui.ui_dialogTELEMETRY_GROUP_SAVE = 'SAVE'TELEMETRY_HOOK_SAVE_FAIL = 'FAIL'TELEMETRY_FIELD_ERROR_CODE = 'etyp'TELEMETRY_FIELD_STACK_HASH = 'ecod'save_telemetry_writer = sims4.telemetry.TelemetryWriter(TELEMETRY_GROUP_SAVE)logger = sims4.log.Logger('Persistence', default_owner='manus')callback_on_save = None
class PersistenceTuning:
    SAVE_GAME_COOLDOWN = TunableRealSecond(description='\n        Cooldown on the save game button to prevent users from saving too\n        often.\n        ', default=0, minimum=0)
    MINUTES_STAY_ON_LOT_BEFORE_GO_HOME = TunableInterval(description="\n        For all sims, when the sim is saved NOT on their home lot, we use this\n        interval to determine how many minutes they'll stay on that lot before\n        they go home.\n\n        Then, if we load up the non-home lot past this amount of time, that sim\n        will no longer be on that lot because that sim will have gone home.\n        \n        If the we load up on the sim's home lot -- if less than this amount of\n        time has passed, we set an alarm so that the sim will spawn into their\n        home lot at the saved time. If equal or more than this amount of time\n        has passed, that sim will be spawned in at zone load.\n        \n        The amount of time is a range. When loading, we'll randomly pick\n        between the upper and lower limit of the range.\n        ", tunable_type=TunableSimMinute, default_lower=180, default_upper=240, minimum=0)
    SAVE_FAILED_REASONS = TunableTuple(description='\n        Localized strings to display when the user cannot save.\n        ', generic=TunableLocalizedString(description='\n            Generic message for why game cannot be saved at the moment\n            '), on_cooldown=TunableLocalizedString(description='\n            The message to show when save game failed due to save being on\n            cooldown\n            '), exception_occurred=TunableLocalizedStringFactory(description='\n            The message to show when save game failed due to an exception\n            occuring during save\n            '))
    LOAD_ERROR_REQUEST_RESTART = ui.ui_dialog.UiDialogOk.TunableFactory(description='\n        The dialog that will be triggered when exception occurred during load\n        of zone and ask user to restart game.\n        ')
    LOAD_ERROR = ui.ui_dialog.UiDialogOk.TunableFactory(description='\n        The dialog that will be triggered when exception occurred during load\n        of zone.\n        ')

class SaveGameResult(enum.Int, export=False):
    SUCCESS = 0
    FAILED_ON_COOLDOWN = 1
    FAILED_EXCEPTION_OCCURRED = 2
    FAILED_SAVE_LOCKED = 3
    FAILED_STORAGE_FULL = 4
SaveGameData = collections.namedtuple('SaveGameData', ('slot_id', 'slot_name', 'force_override', 'auto_save_slot_id'))
class PersistenceService(Service):

    def __init__(self):
        super().__init__()
        self._save_locks = []
        self._read_write_locked = False
        self._save_game_data_proto = serialization.SaveGameData()
        self.save_timeline = None
        self._unlocked_callbacks = CallableList()
        self.once_per_session_telemetry_sent = False
        self.save_error_code = persistence_error_types.ErrorCodes.NO_ERROR
        self._zone_data_pb_cache = {}
        self._sim_data_pb_cache = None
        self._household_pb_cache = None
        self._world_ids = frozenset()

    def setup(self, **kwargs):
        self._time_of_last_save = None

    def build_caches(self):
        self._zone_data_pb_cache.clear()
        for zone in self._save_game_data_proto.zones:
            self._zone_data_pb_cache[zone.zone_id] = zone
        self._world_ids = frozenset(z.world_id for z in self._zone_data_pb_cache.values())
        self.dirty_sim_data_pb_cache()
        self._household_pb_cache = None

    def dirty_sim_data_pb_cache(self):
        self._sim_data_pb_cache = None

    def _get_sim_data_pb_cache(self):
        if self._sim_data_pb_cache is None:
            self._sim_data_pb_cache = {sim_pb.sim_id: index for (index, sim_pb) in enumerate(self._save_game_data_proto.sims)}
        return self._sim_data_pb_cache

    def _get_household_data_pb_cache(self):
        if self._household_pb_cache is not None:
            cache_len = len(self._household_pb_cache)
            actual_len = len(self._save_game_data_proto.households)
            if cache_len < actual_len:
                self._household_pb_cache = None
            elif cache_len > actual_len:
                logger.error('_household_pb_cache contains more than it should', owner='tingyul')
        if self._household_pb_cache is None:
            self._household_pb_cache = {household_pb.household_id: index for (index, household_pb) in enumerate(self._save_game_data_proto.households)}
        return self._household_pb_cache

    def is_save_locked(self):
        if self._read_write_locked:
            return True
        elif not self._save_locks:
            return False
        return True

    def get_save_lock_tooltip(self):
        if self._read_write_locked:
            return PersistenceTuning.SAVE_FAILED_REASONS.generic
        elif self._save_locks:
            return self._save_locks[-1].get_lock_save_reason()

    def set_read_write_lock(self, is_locked, reference_id):
        changed_lock = self._read_write_locked != is_locked
        self._read_write_locked = is_locked
        if changed_lock:
            if is_locked:
                self._send_lock_save_message(lambda : PersistenceTuning.SAVE_FAILED_REASONS.generic)
            elif self.is_save_locked():
                self._send_lock_save_message(self.get_save_lock_tooltip)
            else:
                self._send_unlock_save_message()
        self._try_invoke_unlocked_callbacks()

    def get_save_game_data_proto(self):
        return self._save_game_data_proto

    def lock_save(self, lock_holder):
        self._save_locks.append(lock_holder)
        self._send_lock_save_message(lock_holder.get_lock_save_reason)

    def unlock_save(self, lock_holder, send_event=True):
        if lock_holder in self._save_locks:
            self._save_locks.remove(lock_holder)
        self._try_invoke_unlocked_callbacks()
        if send_event:
            if not self.is_save_locked():
                self._send_unlock_save_message()
            else:
                self._send_lock_save_message(self.get_save_lock_tooltip)

    def _send_lock_save_message(self, reason_provider):
        distributor = Distributor.instance()
        if distributor is not None and distributor.client is not None:
            msg = UI_pb2.GameSaveLockUnlock()
            msg.is_locked = True
            msg.lock_reason = reason_provider()
            distributor.add_event(MSG_GAME_SAVE_LOCK_UNLOCK, msg)

    def _send_unlock_save_message(self):
        distributor = Distributor.instance()
        if distributor is not None and distributor.client is not None:
            msg = UI_pb2.GameSaveLockUnlock()
            msg.is_locked = False
            distributor.add_event(MSG_GAME_SAVE_LOCK_UNLOCK, msg)

    def remove_save_locks(self):
        if self._save_locks:
            self._save_locks.clear()
            self._send_unlock_save_message()
        self._unlocked_callbacks.clear()

    def add_save_unlock_callback(self, callback):
        if self.is_save_locked():
            self._unlocked_callbacks.register(callback)
        else:
            callback()

    def _try_invoke_unlocked_callbacks(self):
        if self._unlocked_callbacks and not self.is_save_locked():
            self._unlocked_callbacks()
            self._unlocked_callbacks.clear()

    def _create_save_timeline(self):
        self._destroy_save_timeline(self.save_timeline)
        self.save_timeline = scheduling.Timeline(services.time_service().sim_now)

    def _destroy_save_timeline(self, timeline):
        if self.save_timeline is not timeline:
            raise RuntimeError('Attempting to destroy the wrong timeline!')
        if self.save_timeline is not None:
            self.save_timeline = None
            timeline.teardown()

    def save_using(self, save_generator, *args, **kwargs):

        def call_save_game_gen(timeline):
            result = yield from save_generator(timeline, *args, **kwargs)
            return result

        self._create_save_timeline()
        element = elements.GeneratorElement(call_save_game_gen)
        element = elements.WithFinallyElement(element, self._destroy_save_timeline)
        element_handle = self.save_timeline.schedule(element)
        return element_handle

    def save_to_scratch_slot_gen(self, timeline):
        save_game_data = SaveGameData(0, 'scratch', True, None)
        save_result_code = yield from self.save_game_gen(timeline, save_game_data, send_save_message=False, check_cooldown=False)
        return save_result_code

    def save_game_gen(self, timeline, save_game_data, send_save_message=True, check_cooldown=False, ignore_callback=False):
        (result_code, failure_reason) = yield from self._save_game_gen(timeline, save_game_data, check_cooldown=check_cooldown)
        if send_save_message:
            msg = UI_pb2.GameSaveComplete()
            msg.return_status = result_code
            msg.save_cooldown = self._get_cooldown()
            if failure_reason is not None:
                msg.failure_reason = failure_reason
            msg.slot_id = save_game_data.slot_id
            distributor = Distributor.instance()
            distributor.add_event(MSG_GAME_SAVE_COMPLETE, msg)
        return result_code

    def _save_game_gen(self, timeline, save_game_data, check_cooldown=True):
        save_lock_reason = self.get_save_lock_tooltip()
        if save_lock_reason is not None:
            return (SaveGameResult.FAILED_SAVE_LOCKED, save_lock_reason)
        current_time = services.server_clock_service().now()
        result_code = SaveGameResult.FAILED_ON_COOLDOWN
        if self._time_of_last_save is not None:
            cooldown = (current_time - self._time_of_last_save).in_real_world_seconds()
        else:
            cooldown = PersistenceTuning.SAVE_GAME_COOLDOWN + 1
        if check_cooldown and cooldown > PersistenceTuning.SAVE_GAME_COOLDOWN:
            result_code = SaveGameResult.SUCCESS
            error_code_string = None
            try:
                yield from self._fill_and_send_save_game_protobufs_gen(timeline, save_game_data.slot_id, save_game_data.slot_name, auto_save_slot_id=save_game_data.auto_save_slot_id)
            except Exception as e:
                result_code = SaveGameResult.FAILED_EXCEPTION_OCCURRED
                error_code_string = persistence_error_types.generate_exception_code(self.save_error_code, e)
                logger.exception('Save failed due to Exception', exc=e)
                with telemetry_helper.begin_hook(save_telemetry_writer, TELEMETRY_HOOK_SAVE_FAIL) as hook:
                    hook.write_int(TELEMETRY_FIELD_ERROR_CODE, self.save_error_code)
                    hook.write_int(TELEMETRY_FIELD_STACK_HASH, sims4.hash_util.hash64(error_code_string))
            finally:
                self.save_error_code = persistence_error_types.ErrorCodes.NO_ERROR
        if result_code == SaveGameResult.SUCCESS:
            self._time_of_last_save = current_time
        failure_reason = self._get_failure_reason_for_result_code(result_code, error_code_string)
        return (result_code, failure_reason)

    def _get_failure_reason_for_result_code(self, result_code, exception_code_string):
        if result_code == SaveGameResult.SUCCESS:
            return
        if result_code == SaveGameResult.FAILED_ON_COOLDOWN:
            return PersistenceTuning.SAVE_FAILED_REASONS.on_cooldown
        if result_code == SaveGameResult.FAILED_EXCEPTION_OCCURRED:
            return PersistenceTuning.SAVE_FAILED_REASONS.exception_occurred(exception_code_string)
        return PersistenceTuning.SAVE_FAILED_REASONS.generic

    def _get_cooldown(self):
        if self._time_of_last_save is not None:
            current_time = services.server_clock_service().now()
            cooldown = PersistenceTuning.SAVE_GAME_COOLDOWN - (current_time - self._time_of_last_save).in_real_world_seconds()
            return cooldown
        return 0

    def _fill_and_send_save_game_protobufs_gen(self, timeline, slot_id, slot_name, auto_save_slot_id=None):
        self.save_error_code = persistence_error_types.ErrorCodes.SETTING_SAVE_SLOT_DATA_FAILED
        save_slot_data_msg = self.get_save_slot_proto_buff()
        save_slot_data_msg.slot_id = slot_id
        save_slot_data_msg.slot_name = slot_name
        if services.active_household_id() is not None:
            save_slot_data_msg.active_household_id = services.active_household_id()
        sims4.core_services.service_manager.save_all_services(self, save_slot_data=save_slot_data_msg)
        self.save_error_code = persistence_error_types.ErrorCodes.SAVE_CAMERA_DATA_FAILED
        camera.serialize(save_slot_data=save_slot_data_msg)

        def on_save_complete(slot_id, success):
            wakeable_element.trigger_soft_stop()

        self.save_error_code = persistence_error_types.ErrorCodes.SAVE_TO_SLOT_FAILED
        wakeable_element = element_utils.soft_sleep_forever()
        persistence_module.run_persistence_operation(persistence_module.PersistenceOpType.kPersistenceOpSave, self._save_game_data_proto, slot_id, on_save_complete)
        yield from element_utils.run_child(timeline, wakeable_element)
        if auto_save_slot_id is not None:
            self.save_error_code = persistence_error_types.ErrorCodes.AUTOSAVE_TO_SLOT_FAILED
            wakeable_element = element_utils.soft_sleep_forever()
            persistence_module.run_persistence_operation(persistence_module.PersistenceOpType.kPersistenceOpSave, self._save_game_data_proto, auto_save_slot_id, on_save_complete)
            yield from element_utils.run_child(timeline, wakeable_element)
        self.save_error_code = persistence_error_types.ErrorCodes.NO_ERROR

    def get_world_ids(self):
        return self._world_ids

    def get_lot_proto_buff(self, lot_id):
        zone_id = self.resolve_lot_id_into_zone_id(lot_id)
        if zone_id is not None:
            neighborhood_data = self.get_neighborhood_proto_buff(services.current_zone().neighborhood_id)
            if neighborhood_data is not None:
                for lot_owner_data in neighborhood_data.lots:
                    if zone_id == lot_owner_data.zone_instance_id:
                        return lot_owner_data

    def get_neighborhood_agnostic_lot_proto_buff(self, lot_id):
        (zone_id, neighborhood_id) = self.resolve_lot_id_into_zone_and_neighborhood_id(lot_id)
        if zone_id is None:
            return
        neighborhood_data = self.get_neighborhood_proto_buff(neighborhood_id)
        if neighborhood_data is None:
            return
        for lot_owner_data in neighborhood_data.lots:
            if zone_id == lot_owner_data.zone_instance_id:
                return lot_owner_data

    def get_zone_proto_buff(self, zone_id):
        if zone_id in self._zone_data_pb_cache:
            return self._zone_data_pb_cache[zone_id]

    def get_house_description_id(self, zone_id):
        zone_data = self.get_zone_proto_buff(zone_id)
        house_description_id = services.get_house_description_id(zone_data.lot_template_id, zone_data.lot_description_id, zone_data.active_plex)
        return house_description_id

    def get_lot_data_from_zone_data(self, zone_data):
        neighborhood_data = self.get_neighborhood_proto_buff(zone_data.neighborhood_id)
        if neighborhood_data is None:
            return
        for lot_data in neighborhood_data.lots:
            if zone_data.zone_id == lot_data.zone_instance_id:
                return lot_data

    def get_world_id_from_zone(self, zone_id):
        zone_proto = self.get_zone_proto_buff(zone_id)
        if zone_proto is None:
            return 0
        return zone_proto.world_id

    def zone_proto_buffs_gen(self):
        if self._save_game_data_proto is not None:
            for zone in self._save_game_data_proto.zones:
                yield zone

    def get_open_street_proto_buff(self, world_id):
        if self._save_game_data_proto is not None:
            for open_street in self._save_game_data_proto.streets:
                if open_street.world_id == world_id:
                    return open_street

    def add_open_street_proto_buff(self, open_street_proto):
        if self._save_game_data_proto is not None:
            self._save_game_data_proto.streets.append(open_street_proto)

    def get_household_id_from_lot_id(self, lot_id):
        lot_owner_info = self.get_lot_proto_buff(lot_id)
        if lot_owner_info is not None:
            for household in lot_owner_info.lot_owner:
                return household.household_id

    def get_household_id_from_zone_id(self, zone_id):
        zone_data = self.get_zone_proto_buff(zone_id)
        if zone_data is not None:
            return zone_data.household_id

    def resolve_lot_id_into_zone_id(self, lot_id, neighborhood_id=None, ignore_neighborhood_id=False):
        if neighborhood_id is None:
            neighborhood_id = services.current_zone().neighborhood_id
        if self._save_game_data_proto is not None:
            for zone in self._save_game_data_proto.zones:
                if not ignore_neighborhood_id:
                    if zone.neighborhood_id == neighborhood_id:
                        return zone.zone_id
                return zone.zone_id

    def resolve_lot_id_into_zone_and_neighborhood_id(self, lot_id):
        if self._save_game_data_proto is not None:
            for zone in self._save_game_data_proto.zones:
                if zone.lot_id == lot_id:
                    return (zone.zone_id, zone.neighborhood_id)
        return (None, None)

    def get_save_slot_proto_guid(self):
        if self._save_game_data_proto is not None:
            return self._save_game_data_proto.guid

    def get_save_slot_proto_buff(self):
        if self._save_game_data_proto is not None:
            return self._save_game_data_proto.save_slot

    def get_account_proto_buff(self):
        if self._save_game_data_proto is not None:
            return self._save_game_data_proto.account

    def add_sim_proto_buff(self, sim_id):
        sim_data_pb_cache = self._get_sim_data_pb_cache()
        sim_data_pb_cache[sim_id] = len(self._save_game_data_proto.sims)
        sim_pb = self._save_game_data_proto.sims.add()
        return sim_pb

    def del_sim_proto_buff(self, sim_id):
        if self._save_game_data_proto is None:
            return
        for (index, sim_msg) in enumerate(self._save_game_data_proto.sims):
            if sim_msg.sim_id == sim_id:
                del self._save_game_data_proto.sims[index]
                break
        logger.error('Attempting to delete Sim {} that is absent in the save file.', sim_id)
        self.dirty_sim_data_pb_cache()

    def get_sim_proto_buff(self, sim_id):
        sim_data_pb_cache = self._get_sim_data_pb_cache()
        index = sim_data_pb_cache.get(sim_id)
        if index is not None and index < len(self._save_game_data_proto.sims):
            return self._save_game_data_proto.sims[index]

    def add_household_proto_buff(self, household_id):
        household_pb_cache = self._get_household_data_pb_cache()
        household_pb_cache[household_id] = len(self._save_game_data_proto.households)
        household_pb = self._save_game_data_proto.households.add()
        return household_pb

    def del_household_proto_buff(self, household_id):
        if self._save_game_data_proto is None:
            return
        for (index, household_msg) in enumerate(self._save_game_data_proto.households):
            if household_msg.household_id == household_id:
                del self._save_game_data_proto.households[index]
                break
        logger.error('Attempting to delete Household {} that is absent in the save file.', household_id)
        self._household_pb_cache = None

    def get_household_proto_buff(self, household_id):
        household_pb_cache = self._get_household_data_pb_cache()
        index = household_pb_cache.get(household_id)
        if index is not None and index < len(self._save_game_data_proto.households):
            return self._save_game_data_proto.households[index]

    def all_household_protos(self):
        if self._save_game_data_proto is not None:
            return tuple(self._save_game_data_proto.households)
        return tuple()

    def get_neighborhood_proto_buff(self, neighborhood_id):
        if self._save_game_data_proto is not None:
            for neighborhood in self._save_game_data_proto.neighborhoods:
                if neighborhood.neighborhood_id == neighborhood_id:
                    return neighborhood

    def get_neighborhoods_proto_buf_gen(self):
        for neighborhood_proto_buf in self._save_game_data_proto.neighborhoods:
            yield neighborhood_proto_buf

    def get_neighborhood_proto_buf_from_zone_id(self, zone_id):
        zone_proto = self.get_zone_proto_buff(zone_id)
        if zone_proto is None:
            return
        neighborhood_proto = self.get_neighborhood_proto_buff(zone_proto.neighborhood_id)
        return neighborhood_proto

    def add_mannequin_proto_buff(self):
        return self._save_game_data_proto.mannequins.add()

    def get_mannequin_proto_buff(self, mannequin_id):
        if self._save_game_data_proto is not None:
            for mannequin_data in self._save_game_data_proto.mannequins:
                if mannequin_data.mannequin_id == mannequin_id:
                    return mannequin_data

    def del_mannequin_proto_buff(self, mannequin_id):
        if self._save_game_data_proto is not None:
            for (index, mannequin_data) in enumerate(self._save_game_data_proto.mannequins):
                if mannequin_data.mannequin_id == mannequin_id:
                    del self._save_game_data_proto.mannequins[index]
                    break

    def prepare_mannequin_for_cas(self, outfit_data):
        self.del_mannequin_proto_buff(outfit_data.sim_id)
        sim_info_data_proto = self.add_mannequin_proto_buff()
        sim_info_data_proto.mannequin_id = outfit_data.sim_id
        outfit_data.save_sim_info(sim_info_data_proto)
        current_zone_id = services.current_zone_id()
        sim_info_data_proto.zone_id = current_zone_id
        sim_info_data_proto.world_id = self.get_world_id_from_zone(current_zone_id)
        return sim_info_data_proto

    def all_travel_group_proto_gen(self):
        if self._save_game_data_proto is not None:
            for travel_group in self._save_game_data_proto.travel_groups:
                yield travel_group

    def get_travel_group_proto_buff(self, travel_group_id):
        if self._save_game_data_proto is not None:
            for travel_group in self._save_game_data_proto.travel_groups:
                if travel_group.travel_group_id == travel_group_id:
                    return travel_group

    def add_travel_group_proto_buff(self):
        return self._save_game_data_proto.travel_groups.add()

    def del_travel_group_proto_buff(self, travel_group_id):
        if self._save_game_data_proto is not None:
            for (index, travel_group) in enumerate(self._save_game_data_proto.travel_groups):
                if travel_group.travel_group_id == travel_group_id:
                    del self._save_game_data_proto.travel_groups[index]
                    break

    def try_send_once_per_session_telemetry(self):
        if not self.once_per_session_telemetry_sent:
            try:
                HouseholdRegionTelemetryData.send_household_region_telemetry()
            except Exception:
                logger.exception('Exception thrown inside try_send_once_per_session_telemetry()', owner='jwilkinson')
            finally:
                self.once_per_session_telemetry_sent = True

def save_unlock_callback(fn):

    @functools.wraps(fn)
    def wrapped(*args, **kwargs):
        persistence_service = services.get_persistence_service()
        persistence_service.add_save_unlock_callback(functools.partial(fn, *args, **kwargs))

    return wrapped

@exception_protected
def c_api_get_world_id_from_zone(zone_id):
    world_id = services.get_persistence_service().get_world_id_from_zone(zone_id)
    return world_id

@exception_protected
def c_api_get_data_readonly():
    save_game_data_proto = services.get_persistence_service().get_save_game_data_proto()
    return save_game_data_proto

@exception_protected
def c_api_get_data_readwrite(reference_id):
    save_game_data_proto = services.get_persistence_service().get_save_game_data_proto()
    services.get_persistence_service().set_read_write_lock(True, reference_id)
    return save_game_data_proto

@exception_protected
def c_api_save_data(reference_id):
    persistence_service = services.get_persistence_service()
    persistence_service.set_read_write_lock(False, reference_id)
    persistence_service.dirty_sim_data_pb_cache()
    return True

@exception_protected
def c_api_release_data(reference_id):
    services.get_persistence_service().set_read_write_lock(False, reference_id)
    return True
